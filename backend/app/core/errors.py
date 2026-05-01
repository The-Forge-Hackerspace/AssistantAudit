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

class ServerError(AppError):
    """Erreur serveur (500) — défaillance interne, pas une validation utilisateur.

    À utiliser quand un traitement côté serveur plante pour une raison non
    contrôlable par le client (génération PDF, dépendance externe, etc.).
    Le détail technique de l'exception cause doit rester côté logs ;
    le message passé ici est sûr à exposer.
    """
    pass
