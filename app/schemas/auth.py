from pydantic import BaseModel

class AuthIn(BaseModel):
    usuario: str
    senha: str

class AuthData(BaseModel):
    message: str
    access_key: str
    expire_at: str

class AuthOut(BaseModel):
    message: str
    status: int
    data: AuthData | None = None
