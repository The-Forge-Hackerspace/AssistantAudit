#!/usr/bin/env python3
"""
Script de test pour vérifier les validations v1.2
"""
import os
import sys

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.utils import (
    allowed_file, 
    validate_file_type, 
    create_audit_folder_structure,
    validate_contacts
)
from werkzeug.datastructures import FileStorage, ImmutableMultiDict
from io import BytesIO
from datetime import datetime

# Créer l'application Flask pour le contexte
app = create_app()

print("="*80)
print("🧪 TESTS DES VALIDATIONS v1.2")
print("="*80)

# Test 1: allowed_file
print("\n📝 Test 1: allowed_file()")
print("-" * 40)
tests_allowed = [
    ("document.pdf", "pdf", True),
    ("document.txt", "pdf", False),
    ("image.png", "image", True),
    ("image.pdf", "image", False),
    ("planning.xlsx", "spreadsheet", True),
    ("planning.pdf", "spreadsheet", False),
    ("anything.pdf", "all", True),
]

for filename, file_type, expected in tests_allowed:
    result = allowed_file(filename, file_type)
    status = "✅" if result == expected else "❌"
    print(f"{status} allowed_file('{filename}', '{file_type}') = {result} (attendu: {expected})")

# Test 2: validate_file_type
print("\n📝 Test 2: validate_file_type()")
print("-" * 40)

# Créer des fichiers de test
test_files = [
    ("test.pdf", b"PDF content", "pdf", "Contrat"),
    ("test.png", b"PNG content", "image", "Organigramme"),
    ("test.txt", b"Text content", "pdf", "Document"),
]

for filename, content, expected_type, field_name in test_files:
    file_obj = FileStorage(
        stream=BytesIO(content),
        filename=filename,
        content_type='application/octet-stream'
    )
    is_valid, error_msg = validate_file_type(file_obj, expected_type, field_name)
    
    if filename.endswith('.txt') and expected_type == 'pdf':
        status = "✅" if not is_valid else "❌"
        print(f"{status} validate_file_type('{filename}', '{expected_type}') = {is_valid}")
        if error_msg:
            print(f"   💬 Message: {error_msg}")
    else:
        status = "✅" if is_valid else "❌"
        print(f"{status} validate_file_type('{filename}', '{expected_type}') = {is_valid}")

# Test 3: create_audit_folder_structure (avec contexte Flask)
print("\n📝 Test 3: create_audit_folder_structure()")
print("-" * 40)

test_entreprises = [
    ("TechCorp", datetime(2024, 1, 15)),
    ("Innovate & Co.", datetime(2024, 2, 20)),
    ("Société@Test!", datetime(2024, 3, 10)),
]

with app.app_context():
    for nom, date in test_entreprises:
        folder = create_audit_folder_structure(nom, date)
        print(f"✅ '{nom}' → {folder}/")
        
        # Vérifier que les dossiers existent (chemin complet via UPLOAD_FOLDER)
        upload_folder = app.config['UPLOAD_FOLDER']
        expected_subfolders = [
            f"{upload_folder}/{folder}/bloc_00_general",
            f"{upload_folder}/{folder}/bloc_01_administratif",
            f"{upload_folder}/{folder}/bloc_02_contexte",
        ]
        
        all_exist = all(os.path.exists(sf) for sf in expected_subfolders)
        if all_exist:
            print(f"   ✅ Tous les sous-dossiers créés")
        else:
            print(f"   ❌ Certains sous-dossiers manquants")
            for sf in expected_subfolders:
                exists = "✅" if os.path.exists(sf) else "❌"
                print(f"      {exists} {sf}")

# Test 4: validate_contacts
print("\n📝 Test 4: validate_contacts()")
print("-" * 40)

# Test avec contact principal
form_with_main = ImmutableMultiDict([
    ('contact_nom_0', 'Jean Dupont'),
    ('contact_principal_0', 'on'),
    ('contact_nom_1', 'Marie Martin'),
])

is_valid, error = validate_contacts(form_with_main)
status = "✅" if is_valid else "❌"
print(f"{status} Formulaire avec 1 contact principal : {is_valid}")

# Test sans contact principal
form_without_main = ImmutableMultiDict([
    ('contact_nom_0', 'Jean Dupont'),
    ('contact_nom_1', 'Marie Martin'),
])

is_valid, error = validate_contacts(form_without_main)
status = "✅" if not is_valid else "❌"
print(f"{status} Formulaire sans contact principal : {is_valid}")
if error:
    print(f"   💬 Message: {error}")

# Test sans contacts (devrait être valide car pas de contacts = pas besoin de principal)
form_empty = ImmutableMultiDict([])
is_valid, error = validate_contacts(form_empty)
status = "✅" if is_valid else "❌"
print(f"{status} Formulaire vide (0 contacts) : {is_valid} (attendu: True)")
if error:
    print(f"   💬 Message: {error}")

print("\n" + "="*80)
print("✅ TOUS LES TESTS TERMINÉS")
print("="*80)
print()
print("💡 Structure des dossiers créés:")
print("   uploads/")
for nom, date in test_entreprises:
    import re
    clean_name = re.sub(r'[^\w\s-]', '', nom)
    clean_name = clean_name.replace(' ', '')
    date_str = date.strftime('%Y%m%d')
    print(f"   └── {clean_name}_{date_str}/")
    print(f"       ├── bloc_00_general/")
    print(f"       ├── bloc_01_administratif/")
    print(f"       └── bloc_02_contexte/")

print()
