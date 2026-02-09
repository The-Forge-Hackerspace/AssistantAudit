"""
Routes d'authentification : login, logout, gestion utilisateurs
"""
import re
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User
from app import limiter

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    """Page de connexion"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Veuillez remplir tous les champs.', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            logger.warning(f'Tentative de connexion échouée pour: {username}')
            flash('Identifiant ou mot de passe incorrect.', 'danger')
            return render_template('auth/login.html')

        if not user.actif:
            flash('Ce compte est désactivé. Contactez un administrateur.', 'warning')
            return render_template('auth/login.html')

        login_user(user)
        user.derniere_connexion = datetime.now(timezone.utc)
        db.session.commit()

        logger.info(f'Connexion réussie: {username}')
        flash(f'Bienvenue, {user.nom_complet or user.username} !', 'success')

        next_page = request.args.get('next')
        # Protection contre l'Open Redirect : rejeter les URLs absolues
        if next_page and urlparse(next_page).netloc != '':
            next_page = None
        return redirect(next_page or url_for('main.index'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Déconnexion"""
    logger.info(f'Déconnexion: {current_user.username}')
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Profil utilisateur - changer mot de passe"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not current_user.check_password(current_password):
            flash('Mot de passe actuel incorrect.', 'danger')
            return render_template('auth/profile.html')

        if len(new_password) < 8:
            flash('Le nouveau mot de passe doit contenir au moins 8 caractères.', 'danger')
            return render_template('auth/profile.html')

        # Vérification de la complexité du mot de passe
        if not re.search(r'[A-Z]', new_password):
            flash('Le mot de passe doit contenir au moins une majuscule.', 'danger')
            return render_template('auth/profile.html')
        if not re.search(r'[a-z]', new_password):
            flash('Le mot de passe doit contenir au moins une minuscule.', 'danger')
            return render_template('auth/profile.html')
        if not re.search(r'[0-9]', new_password):
            flash('Le mot de passe doit contenir au moins un chiffre.', 'danger')
            return render_template('auth/profile.html')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
            flash('Le mot de passe doit contenir au moins un caractère spécial.', 'danger')
            return render_template('auth/profile.html')

        if current_user.check_password(new_password):
            flash('Le nouveau mot de passe doit être différent de l\'ancien.', 'danger')
            return render_template('auth/profile.html')

        if new_password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return render_template('auth/profile.html')

        current_user.set_password(new_password)
        db.session.commit()
        logger.info(f'Mot de passe changé pour: {current_user.username}')
        flash('Mot de passe modifié avec succès.', 'success')

    return render_template('auth/profile.html')
