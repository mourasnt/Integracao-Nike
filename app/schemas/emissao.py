"""Schemas de resposta para o endpoint /emissao."""

from pydantic import BaseModel, Field
from typing import List, Optional


class MinutaResult(BaseModel):
    """Resultado do processamento de uma minuta individual."""
    
    status: int = Field(..., description="1 para sucesso, 0 para falha")
    message: str = Field(..., description="Mensagem descritiva do resultado")
    id: Optional[int] = Field(None, description="ID do shipment criado, se sucesso")
    invoice_count: Optional[int] = Field(None, description="Quantidade de notas processadas com sucesso")
    invoice_failures: Optional[int] = Field(None, description="Quantidade de notas que falharam")

    class Config:
        from_attributes = True


class EmissaoResponse(BaseModel):
    """Resposta completa do endpoint /emissao."""
    
    message: str = Field(..., description="Mensagem geral do processamento")
    status: int = Field(..., description="1 se todas minutas OK, 0 se alguma falhou")
    data: List[MinutaResult] = Field(default_factory=list, description="Resultados por minuta")

    class Config:
        from_attributes = True

    def has_failures(self) -> bool:
        """Retorna True se alguma minuta falhou."""
        return any(r.status == 0 for r in self.data)

    def all_failed(self) -> bool:
        """Retorna True se todas minutas falharam."""
        return all(r.status == 0 for r in self.data)

    def get_http_status(self) -> int:
        """Retorna código HTTP apropriado baseado nos resultados."""
        if not self.data:
            return 400  # Nenhuma minuta processada
        if self.all_failed():
            return 400  # Todas falharam
        if self.has_failures():
            return 207  # Sucesso parcial (Multi-Status)
        return 200  # Todas OK
