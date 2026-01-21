from pydantic import BaseModel, Field, field_validator, model_validator

# EmailStr optionally requires the "email-validator" package. Provide a safe
# fallback (str) when the package is not installed so tests and environments
# without that optional dependency still import successfully.
try:
    from pydantic import EmailStr  # type: ignore
except Exception:
    EmailStr = str  # type: ignore
from typing import List, Optional
from datetime import datetime
import re

class Horarios(BaseModel):
    et_origem: Optional[datetime] = None
    chegada_coleta: Optional[datetime] = None
    saida_coleta: Optional[datetime] = None
    eta_destino: Optional[datetime] = None
    chegada_destino: Optional[datetime] = None
    finalizacao: Optional[datetime] = None

class Carga(BaseModel):
    pBru: str
    pCub: str
    qVol: str
    vTot: str

    @field_validator('pBru', 'qVol', 'vTot', 'pCub')
    def non_empty(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ''):
            raise ValueError("Campo obrigatório na carga")
        return v

class MinutaHeader(BaseModel):
    toma: str
    nDocEmit: str
    dEmi: str
    # Accept either numeric or string-coded service codes to be permissive with provider payloads
    cServ: int | str
    cTab: str
    tpEmi: int
    cStatus: int
    cAut: str
    carga: Carga
    horarios: Optional[Horarios] = None
    cOrigCalc: str
    cDestCalc: str

    @field_validator('dEmi')
    def validate_date(cls, v):
        # Expect YYYY-MM-DD
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except Exception:
            raise ValueError(f"dEmi inválido: {v}, deve ser 'YYYY-MM-DD'")
        return v

    @field_validator('cServ')
    def validate_cserv(cls, v):
        try:
            n = int(v)
        except Exception:
            raise ValueError("cServ deve ser numérico")
        if n <= 0 or n > 99:
            raise ValueError("cServ inválido")
        return v

    @field_validator('toma', 'nDocEmit', 'cTab', 'cAut')
    def non_empty_str(cls, v):
        if not v or (isinstance(v, str) and v.strip() == ''):
            raise ValueError('Campo obrigatório na minuta não pode ser vazio')
        return v

class Actor(BaseModel):
    nDoc: str
    IE: str
    cFiscal: int
    xNome: str
    xFant: str
    xLgr: str
    nro: str
    xCpl: Optional[str] = None
    xBairro: str
    cMun: str
    CEP: str
    cPais: int
    nFone: Optional[str] = None
    email: Optional[str] = None

    @field_validator('nDoc')
    def validate_nDoc(cls, v):
        if not (len(v) == 11 or len(v) == 14):
            raise ValueError('nDoc deve ser CNPJ ou CPF (11 ou 14 dígitos)')
        return v

    @field_validator('cMun')
    def validate_cMun(cls, v):
        if not v or not re.match(r'^\d{7}$', str(v)):
            raise ValueError('cMun inválido (7 dígitos)')
        return v

    @field_validator('IE', 'cFiscal', 'xNome', 'xFant', 'xLgr', 'nro', 'xBairro', 'CEP', 'cPais')
    def non_empty_actor_fields(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ''):
            raise ValueError('Campo de ator obrigatório não pode ser vazio')
        return v

    @field_validator('email')
    def validate_email_optional(cls, v):
        # Accept empty or missing email; basic sanity check when present
        if v is None or (isinstance(v, str) and v.strip() == ''):
            return None
        # Very permissive check: ensure there's an '@' when provided
        if isinstance(v, str) and '@' not in v:
            raise ValueError('email inválido')
        return v

class NotaFiscalItem(BaseModel):
    nPed: Optional[str] = None
    serie: str
    nDoc: Optional[str]
    dEmi: str
    vBC: str
    vICMS: str
    vBCST: str
    vST: str
    vProd: str
    vNF: float
    nCFOP: str
    pBru: str
    qVol: str
    chave: str
    tpDoc: str
    xEsp: str
    xNat: str
    xmlsB64: Optional[List[str]] = None
    # CT-e
    cte: Optional[dict] = None

    @field_validator('nPed', mode='before')
    def normalize_nped(cls, v):
        # Treat blank strings as missing (None)
        if isinstance(v, str) and v.strip() == '':
            return None
        return v

    @field_validator('chave')
    def chave_length(cls, v):
        if not v or len(v) != 44:
            print(f'Chave inválida: {v}')
            raise ValueError('chave deve ter 44 caracteres')
        return v

    @field_validator('vNF')
    def vnf_positive(cls, v):
        try:
            if float(v) <= 0:
                raise ValueError('vNF deve ser numérico e maior que zero')
        except Exception:
            raise ValueError('vNF inválido')
        return v

    @field_validator('qVol')
    def qvol_non_empty(cls, v):
        if not v or str(v).strip() == '':
            raise ValueError('qVol obrigatório')
        return v

class MinutaStructure(BaseModel):
    minuta: MinutaHeader
    rem: Actor
    dest: Actor
    toma: Optional[Actor] = None
    receb: Optional[Actor] = None
    documentos: List[NotaFiscalItem]

    @model_validator(mode='after')
    def check_documentos_not_empty(self):
        docs = getattr(self, 'documentos', None)
        if not docs or len(docs) == 0:
            raise ValueError('Lista de notas fiscais vazia na minuta')
        return self

class NotfisPayload(BaseModel):
    documentos: List[MinutaStructure]
