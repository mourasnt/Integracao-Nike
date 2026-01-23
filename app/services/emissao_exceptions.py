"""Exceções customizadas para o serviço de emissão."""


class EmissaoError(Exception):
    """Exceção base para erros de emissão."""
    
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(message)


class ValidationError(EmissaoError):
    """Erro de validação de dados de entrada."""
    pass


class PersistenceError(EmissaoError):
    """Erro ao persistir dados no banco."""
    pass


class InvoicePartialError(EmissaoError):
    """Erro parcial: algumas notas falharam mas minuta foi salva."""
    
    def __init__(self, message: str, success_count: int, failure_count: int):
        super().__init__(message)
        self.success_count = success_count
        self.failure_count = failure_count
