"""
Fonctions utilitaires partagées entre les routes
"""
import os
import re
import ipaddress
import logging
from functools import wraps
from datetime import datetime
from flask import current_app, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# Extensions de fichiers autorisées par type
ALLOWED_EXTENSIONS = {
    'pdf': {'pdf'},
    'image': {'png', 'jpg', 'jpeg', 'gif'},
    'document': {'pdf', 'doc', 'docx'},
    'spreadsheet': {'xlsx', 'xls', 'csv'},
    'all': {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xlsx', 'xls', 'csv'}
}


def allowed_file(filename, file_type='all'):
    """
    Vérifie si l'extension du fichier est autorisée selon le type

    Args:
        filename: Nom du fichier
        file_type: Type de fichier attendu ('pdf', 'image', 'document', 'spreadsheet', 'all')

    Returns:
        bool: True si l'extension est autorisée
    """
    if not filename or '.' not in filename:
        return False

    ext = filename.rsplit('.', 1)[1].lower()
    allowed = ALLOWED_EXTENSIONS.get(file_type, ALLOWED_EXTENSIONS['all'])
    return ext in allowed


def validate_file_type(file, expected_type, field_name):
    """
    Valide qu'un fichier uploadé correspond au type attendu

    Args:
        file: Fichier Flask (FileStorage)
        expected_type: Type attendu ('pdf', 'image', etc.)
        field_name: Nom du champ (pour messages d'erreur)

    Returns:
        tuple: (bool, str) - (succès, message d'erreur si échec)
    """
    if not file or not file.filename:
        return True, None  # Pas de fichier = OK (optionnel)

    if not allowed_file(file.filename, expected_type):
        allowed_ext = ', '.join(ALLOWED_EXTENSIONS[expected_type])
        return False, f"Le fichier '{field_name}' doit être au format {allowed_ext.upper()}"

    return True, None


def create_audit_folder_structure(entreprise_nom, date_creation):
    """
    Crée une structure de dossiers organisée pour un audit

    Format: uploads/{nom_entreprise}_{YYYYMMDD}/
    ├── bloc_00_general/
    ├── bloc_01_administratif/
    └── bloc_02_contexte/

    Args:
        entreprise_nom: Nom de l'entreprise
        date_creation: Date de création de l'audit

    Returns:
        str: Chemin de base du dossier créé
    """
    # Nettoyer le nom de l'entreprise pour le système de fichiers
    clean_name = re.sub(r'[^\w\s-]', '', entreprise_nom)
    clean_name = re.sub(r'[-\s]+', '_', clean_name).strip('_')

    # Format: NomEntreprise_20260208
    date_str = date_creation.strftime('%Y%m%d')
    base_folder = f"{clean_name}_{date_str}"

    # Créer la structure
    base_path = os.path.join(current_app.config['UPLOAD_FOLDER'], base_folder)
    subfolders = [
        'bloc_00_general',           # Organigramme, présentation
        'bloc_01_administratif',     # Lettre mission, contrat, planning
        'bloc_02_contexte'           # Documents de contexte
    ]

    for subfolder in subfolders:
        folder_path = os.path.join(base_path, subfolder)
        os.makedirs(folder_path, exist_ok=True)

    logger.info(f'Structure de dossiers créée: {base_folder}/')
    return base_folder


def save_uploaded_file(file, subfolder='', expected_type='all'):
    """
    Sauvegarde un fichier uploadé de manière sécurisée avec validation

    Args:
        file: Fichier Flask (FileStorage)
        subfolder: Sous-dossier dans uploads/
        expected_type: Type de fichier attendu ('pdf', 'image', etc.)

    Returns:
        tuple: (str|None, str|None) - (chemin relatif, message d'erreur)
    """
    if not file or not file.filename:
        return None, None

    # Validation du type
    if not allowed_file(file.filename, expected_type):
        allowed_ext = ', '.join(ALLOWED_EXTENSIONS[expected_type])
        return None, f"Type de fichier invalide. Formats acceptés: {allowed_ext.upper()}"

    try:
        filename = secure_filename(file.filename)
        # Ajout d'un timestamp pour éviter les collisions
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"

        # Création du dossier si nécessaire
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(upload_folder, exist_ok=True)

        # Sauvegarde du fichier
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)

        logger.info(f'Fichier uploadé: {os.path.join(subfolder, unique_filename)}')
        # Retourne le chemin relatif
        return os.path.join(subfolder, unique_filename), None

    except Exception as e:
        logger.error(f'Erreur lors de l\'upload: {str(e)}')
        return None, f"Erreur lors de l'upload: {str(e)}"


def validate_contacts(form_data):
    """
    Valide les contacts du formulaire
    - Vérifie qu'au moins un contact principal est désigné

    Args:
        form_data: Données du formulaire (request.form)

    Returns:
        tuple: (bool, str|None) - (succès, message d'erreur si échec)
    """
    contact_index = 0
    has_main_contact = False
    total_contacts = 0

    while True:
        nom_contact = form_data.get(f'contact_nom_{contact_index}', '').strip()

        if not nom_contact:
            break

        total_contacts += 1

        # Vérifier si c'est un contact principal
        if form_data.get(f'contact_principal_{contact_index}') == 'on':
            has_main_contact = True

        contact_index += 1

    if total_contacts > 0 and not has_main_contact:
        return False, "Au moins un contact doit être désigné comme 'Contact Principal'"

    return True, None


def validate_ip_or_cidr(target):
    """
    Valide strictement une adresse IP ou un réseau CIDR.

    Args:
        target: Chaîne à valider

    Returns:
        tuple: (bool, str|None) - (valide, message d'erreur)
    """
    if not target:
        return False, "La cible est requise"

    target = target.strip()

    # Essayer comme réseau CIDR
    try:
        ipaddress.ip_network(target, strict=False)
        return True, None
    except ValueError:
        pass

    # Essayer comme adresse IP simple
    try:
        ipaddress.ip_address(target)
        return True, None
    except ValueError:
        pass

    # Essayer comme plage d'IP (ex: 192.168.1.1-50)
    if '-' in target:
        parts = target.split('-')
        if len(parts) == 2:
            try:
                ipaddress.ip_address(parts[0].strip())
                # La deuxième partie peut être un octet seul
                second = parts[1].strip()
                if second.isdigit() and 0 <= int(second) <= 255:
                    return True, None
            except ValueError:
                pass

    return False, "Format de cible invalide. Utilisez une IP (ex: 192.168.1.1), CIDR (ex: 192.168.1.0/24) ou plage (ex: 192.168.1.1-50)"


def handle_file_upload(request, field_name, expected_type, subfolder):
    """
    Gère l'upload d'un fichier depuis un formulaire de manière centralisée.

    Args:
        request: Flask request object
        field_name: Nom du champ dans request.files
        expected_type: Type attendu ('pdf', 'image', 'spreadsheet')
        subfolder: Sous-dossier de destination

    Returns:
        tuple: (path|None, error_msg|None)
    """
    if field_name not in request.files:
        return None, None

    file = request.files[field_name]
    if not file or not file.filename:
        return None, None

    # Valider le type
    is_valid, error_msg = validate_file_type(file, expected_type, field_name)
    if not is_valid:
        return None, error_msg

    # Sauvegarder
    path, upload_error = save_uploaded_file(file, subfolder, expected_type)
    if upload_error:
        return None, upload_error

    return path, None


def validate_siret(siret):
    """
    Valide le format d'un numéro SIRET.

    Args:
        siret: Numéro SIRET à valider

    Returns:
        tuple: (bool, str|None) - (valide, message d'erreur)
    """
    if not siret:
        return True, None  # Optionnel

    siret = siret.strip()
    if not re.match(r'^\d{14}$', siret):
        return False, "Le SIRET doit contenir exactement 14 chiffres"

    return True, None


def admin_required(f):
    """
    Décorateur qui restreint l'accès aux administrateurs uniquement.
    Doit être utilisé après @login_required.
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def validate_mac_address(mac):
    """
    Valide le format d'une adresse MAC.

    Args:
        mac: Adresse MAC à valider

    Returns:
        tuple: (bool, str|None) - (valide, message d'erreur)
    """
    if not mac:
        return True, None  # Optionnel

    mac = mac.strip()
    # Accepter les formats AA:BB:CC:DD:EE:FF et AA-BB-CC-DD-EE-FF
    if not re.match(r'^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$', mac):
        return False, "Format d'adresse MAC invalide. Utilisez le format AA:BB:CC:DD:EE:FF"

    return True, None


def validate_ip_address(ip):
    """
    Valide le format d'une adresse IP (v4 ou v6).

    Args:
        ip: Adresse IP à valider

    Returns:
        tuple: (bool, str|None) - (valide, message d'erreur)
    """
    if not ip:
        return False, "L'adresse IP est requise"

    ip = ip.strip()
    try:
        ipaddress.ip_address(ip)
        return True, None
    except ValueError:
        return False, "Format d'adresse IP invalide"


def validate_email(email):
    """
    Valide le format d'une adresse email.

    Args:
        email: Adresse email à valider

    Returns:
        tuple: (bool, str|None) - (valide, message d'erreur)
    """
    if not email:
        return True, None  # Optionnel

    email = email.strip()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, f"Format d'email invalide : {email}"

    return True, None
