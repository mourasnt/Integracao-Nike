"""Serviço de processamento de emissão de minutas (Notfis).

Responsabilidades:
- Processar payload Notfis contendo múltiplas minutas
- Criar Shipments e ShipmentInvoices no banco de dados
- Gerenciar transações isoladas por minuta (uma falha não afeta as outras)
- Enriquecer shipments com dados de localidades (best-effort)
"""

import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.shipment import Shipment, ShipmentInvoice
from app.schemas.notfis import NotfisPayload, MinutaStructure, NotaFiscalItem
from app.schemas.emissao import MinutaResult, EmissaoResponse
from app.utils.mappers import minuta_to_shipment_payload, nota_to_invoice_payload
from app.services.localidades_service import LocalidadesService
from app.services.emissao_exceptions import ValidationError, PersistenceError


class EmissaoService:
    """Serviço para processamento de emissões de minutas."""

    def __init__(self, db: AsyncSession):
        """Inicializa o serviço com uma sessão de banco de dados.
        
        Args:
            db: Sessão assíncrona do SQLAlchemy
        """
        self.db = db

    async def process_payload(self, payload: NotfisPayload, user: str) -> EmissaoResponse:
        """Processa um payload Notfis completo com múltiplas minutas.
        
        Cada minuta é processada em uma transação isolada. Uma falha em uma
        minuta não afeta as outras.
        
        Args:
            payload: Payload Notfis validado pelo Pydantic
            user: Usuário autenticado que está fazendo a requisição
            
        Returns:
            EmissaoResponse com resultados de cada minuta
        """
        logger.debug("/emissao processing started by user=%s with %d minutas", user, len(payload.documentos))
        
        results: list[MinutaResult] = []
        
        for idx, minuta_struct in enumerate(payload.documentos):
            result = await self._process_minuta(idx, minuta_struct, user)
            results.append(result)
        
        # Determinar status global
        all_success = all(r.status == 1 for r in results)
        global_message = "Documento gerado no sistema" if all_success else "Houve erros no processamento"
        global_status = 1 if all_success else 0
        
        response = EmissaoResponse(
            message=global_message,
            status=global_status,
            data=results
        )
        
        logger.debug("/emissao completed: %d success, %d failed", 
                    sum(1 for r in results if r.status == 1),
                    sum(1 for r in results if r.status == 0))
        
        return response

    async def _process_minuta(self, idx: int, minuta_struct: MinutaStructure, user: str) -> MinutaResult:
        """Processa uma única minuta com transação isolada.
        
        Args:
            idx: Índice da minuta no payload (para logging)
            minuta_struct: Estrutura da minuta com header, atores e documentos
            user: Usuário autenticado
            
        Returns:
            MinutaResult com status do processamento
        """
        try:
            logger.debug("Processing minuta index=%d user=%s", idx, user)
            
            # Log raw payload para auditoria
            raw = minuta_struct.model_dump() if hasattr(minuta_struct, 'model_dump') else minuta_struct.dict()
            logger.info("Received minuta from %s: %s", user, json.dumps(raw, default=str))
            
            # Processar em transação isolada
            async with self.db.begin():
                shipment = await self._create_shipment(minuta_struct, raw)
                success_count, failure_count = await self._create_invoices(shipment, minuta_struct.documentos)
            
            # Transação commitada com sucesso
            logger.debug("Minuta index=%d committed successfully, shipment id=%s", idx, shipment.id)
            
            if failure_count > 0:
                message = f"Importação realizada com sucesso (algumas notas falharam: {failure_count})"
            else:
                message = "Importação realizada com sucesso"
            
            return MinutaResult(
                status=1,
                message=message,
                id=shipment.id,
                invoice_count=success_count,
                invoice_failures=failure_count if failure_count > 0 else None
            )
            
        except ValidationError as e:
            logger.warning("Validation error for minuta index=%d: %s", idx, e.message)
            await self._safe_rollback()
            return MinutaResult(
                status=0,
                message=f"Erro de validação: {e.message}",
                id=None
            )
            
        except PersistenceError as e:
            logger.exception("Persistence error for minuta index=%d: %s", idx, e.message)
            await self._safe_rollback()
            return MinutaResult(
                status=0,
                message=f"Erro ao salvar: {e.message}",
                id=None
            )
            
        except Exception as e:
            logger.exception("Unexpected error processing minuta index=%d: %s", idx, e)
            await self._safe_rollback()
            return MinutaResult(
                status=0,
                message=f"Erro: {e.__class__.__name__}: {str(e)}",
                id=None
            )

    async def _create_shipment(self, minuta_struct: MinutaStructure, raw: dict) -> Shipment:
        """Cria e persiste um Shipment a partir da estrutura da minuta.
        
        Args:
            minuta_struct: Estrutura da minuta validada
            raw: Payload raw para armazenamento
            
        Returns:
            Shipment criado e persistido (com ID atribuído)
            
        Raises:
            PersistenceError: Se falhar ao criar o shipment
        """
        try:
            # Mapear dados para payload do Shipment
            shipment_payload = minuta_to_shipment_payload(
                minuta=minuta_struct.minuta,
                rem=minuta_struct.rem,
                dest=minuta_struct.dest,
                toma=minuta_struct.toma,
                receb=getattr(minuta_struct, 'receb', None),
                raw_payload=json.dumps(raw, default=str)
            )
            
            # Criar e persistir
            shipment = Shipment(**shipment_payload)
            self.db.add(shipment)
            await self.db.flush()
            
            logger.debug("Shipment created with id=%s, service_code=%s", 
                        shipment.id, shipment.service_code)
            
            # Enriquecer com localidades (best-effort, não falha transação)
            await self._enrich_locations(shipment)
            
            return shipment
            
        except Exception as e:
            logger.exception("Failed to create shipment: %s", e)
            raise PersistenceError(f"Falha ao criar shipment: {str(e)}")

    async def _enrich_locations(self, shipment: Shipment) -> None:
        """Enriquece o shipment com dados normalizados de localidades.
        
        Esta operação é best-effort: falhas são logadas mas não interrompem
        o processamento.
        
        Args:
            shipment: Shipment a ser enriquecido
        """
        try:
            await LocalidadesService.set_shipment_locations(self.db, shipment)
            logger.debug("Locations enriched for shipment id=%s", shipment.id)
        except Exception as e:
            logger.warning("Failed to enrich locations for shipment id=%s (continuing anyway): %s", 
                          shipment.id, e)

    async def _create_invoices(self, shipment: Shipment, notas: list[NotaFiscalItem]) -> tuple[int, int]:
        """Cria as notas fiscais (invoices) para um shipment.
        
        Cada nota é processada individualmente com savepoint isolado.
        Falhas em notas individuais não afetam as outras.
        
        Args:
            shipment: Shipment pai das notas
            notas: Lista de notas fiscais a criar
            
        Returns:
            Tuple (success_count, failure_count)
        """
        success_count = 0
        failure_count = 0
        
        for nf_idx, nf in enumerate(notas):
            try:
                async with self.db.begin_nested():
                    await self._create_single_invoice(shipment, nf, nf_idx)
                success_count += 1
                
            except Exception as e:
                failure_count += 1
                logger.exception("Failed to create invoice index=%d for shipment id=%s: %s", 
                               nf_idx, shipment.id, e)
                # Continua processando outras notas
                continue
        
        logger.debug("Invoices for shipment id=%s: %d success, %d failed", 
                    shipment.id, success_count, failure_count)
        
        return success_count, failure_count

    async def _create_single_invoice(self, shipment: Shipment, nf: NotaFiscalItem, idx: int) -> ShipmentInvoice:
        """Cria uma única nota fiscal.
        
        Args:
            shipment: Shipment pai
            nf: Dados da nota fiscal
            idx: Índice da nota (para logging)
            
        Returns:
            ShipmentInvoice criada
            
        Raises:
            ValidationError: Se dados obrigatórios estiverem faltando
            PersistenceError: Se falhar ao persistir
        """
        logger.debug("Processing nota index=%d for shipment id=%s", idx, shipment.id)
        
        # Validações (já são feitas pelo Pydantic, mas double-check)
        if not nf.nDoc:
            raise ValidationError("Campo obrigatório 'nDoc' não informado")
        if not nf.chave or len(nf.chave) != 44:
            raise ValidationError("Campo 'chave' inválido (deve ter 44 caracteres)")
        
        # Mapear e criar
        invoice_payload = nota_to_invoice_payload(nf, shipment_id=shipment.id)
        invoice = ShipmentInvoice(**invoice_payload)
        
        # Garantir que remetente_ndoc está preenchido
        invoice.remetente_ndoc = invoice_payload.get('remetente_ndoc') or shipment.rem_nDoc
        
        self.db.add(invoice)
        
        return invoice

    async def _safe_rollback(self) -> None:
        """Executa rollback de forma segura, ignorando erros."""
        try:
            await self.db.rollback()
        except Exception as e:
            logger.warning("Rollback failed (may already be rolled back): %s", e)
