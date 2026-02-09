"""
Configuration de l'application AssistantAudit
Supporte différents environnements via variables d'environnement
"""
import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    """Configuration de base commune à tous les environnements"""
    # Clé secrète — DOIT être définie via variable d'environnement en production
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-only-insecure-key-change-me-in-production'

    # Base de données
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'assistantaudit.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16 MB

    # Pagination
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', 20))

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE') or os.path.join(basedir, 'logs', 'assistantaudit.log')

    # Nmap
    NMAP_TIMEOUT = int(os.environ.get('NMAP_TIMEOUT', 600))  # 10 minutes par défaut


class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class TestingConfig(Config):
    """Configuration pour les tests"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost'


class ProductionConfig(Config):
    """Configuration pour la production"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'

    @classmethod
    def init_app(cls, app):
        """Vérifications spécifiques à la production"""
        # Vérifier que SECRET_KEY est définie explicitement via variable d'environnement
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY must be set via environment variable for production!")


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
