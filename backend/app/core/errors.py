# core/errors.py
class AppError(Exception):
    """Base domain exception."""

class NotFoundError(AppError):
    pass

class ForbiddenError(AppError):
    pass

class ConflictError(AppError):
    pass

class ValidationError(AppError):
    pass

class BusinessRuleError(AppError):
    """Violation d'une règle métier (remplace ValueError dans les services)."""
    pass