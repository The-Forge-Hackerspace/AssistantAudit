"""
Module d'initialisation de l'application Flask pour AssistantAudit
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timezone

from config import config

# Initialisation des extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'warning'
migrate = Migrate()
csrf = CSRFProtect()


def configure_logging(app):
    """Configure le logging de l'application"""
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)

    # Créer le dossier de logs si nécessaire
    log_file = app.config.get('LOG_FILE')
    if log_file:
        log_dir = os.path.dirname(log_file)
        os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s [%(name)s] %(message)s'
        ))
        app.logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    ))
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)


def create_app(config_name=None):
    """Factory pour créer l'application Flask"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))

    # Création du dossier uploads s'il n'existe pas
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialisation des extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Configuration du logging
    configure_logging(app)

    with app.app_context():
        # Import des modèles
        from . import models

        # User loader pour Flask-Login
        @login_manager.user_loader
        def load_user(user_id):
            return models.User.query.get(int(user_id))

        # Import et enregistrement des blueprints
        from .routes.main import main_bp
        from .routes.auth import auth_bp
        from .routes.audit import audit_bp
        from .routes.entreprise import entreprise_bp
        from .routes.equipement import equipement_bp
        from .routes.scan import scan_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(audit_bp)
        app.register_blueprint(entreprise_bp)
        app.register_blueprint(equipement_bp)
        app.register_blueprint(scan_bp)

        # Context processor pour l'année courante dans les templates
        @app.context_processor
        def inject_globals():
            return {'current_year': datetime.now(timezone.utc).year}

        # Création des tables (sera remplacé par Flask-Migrate en prod)
        db.create_all()

        app.logger.info('Application AssistantAudit initialisée avec succès')

    return app
