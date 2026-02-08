# 🔒 Améliorations v1.2 - Validations Robustes

**Date**: $(date +%Y-%m-%d)  
**Version**: 1.2  
**Statut**: ✅ Complète

---

## 📋 Résumé des Améliorations

Cette version renforce la sécurité et l'intégrité des données en ajoutant des **validations robustes** pour les fichiers uploadés et les formulaires.

### Améliorations Principales

1. ✅ **Validation de Type de Fichiers**
   - PDF uniquement pour les documents administratifs (contrat, lettre de mission)
   - Images (PNG, JPG, JPEG, GIF) pour les organigrammes
   - Tableurs (XLSX, XLS, CSV) pour les plannings
   - Messages d'erreur clairs et spécifiques

2. ✅ **Validation Contact Principal Obligatoire**
   - Au moins un contact doit être désigné "Contact Principal"
   - Validation côté serveur avec message d'erreur explicite

3. ✅ **Structure de Dossiers Organisée**
   - Format: `uploads/{NomEntreprise}_{YYYYMMDD}/bloc_XX_nom/`
   - Blocs automatiques:
     - `bloc_00_general/` - Fichiers généraux (organigramme, etc.)
     - `bloc_01_administratif/` - Documents administratifs
     - `bloc_02_contexte/` - Documents de contexte
   - Nettoyage automatique du nom d'entreprise (suppression caractères spéciaux)

---

## 🔧 Modifications Techniques

### 1. Nouvelles Fonctions de Validation

#### `allowed_file(filename, file_type='all')`
```python
ALLOWED_EXTENSIONS = {
    'pdf': {'pdf'},
    'image': {'png', 'jpg', 'jpeg', 'gif'},
    'document': {'pdf', 'doc', 'docx'},
    'spreadsheet': {'xlsx', 'xls', 'csv'},
    'all': {'pdf', 'doc', 'docx', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg', 'gif', 'txt'}
}
```

Vérifie qu'un fichier a une extension valide selon le type requis.

**Paramètres**:
- `filename`: Nom du fichier à valider
- `file_type`: Type attendu (`'pdf'`, `'image'`, `'document'`, `'spreadsheet'`, `'all'`)

**Retour**: `True` si valide, `False` sinon

---

#### `validate_file_type(file, expected_type, field_name)`
```python
def validate_file_type(file, expected_type, field_name):
    """
    Valide qu'un fichier correspond au type attendu
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
```

Validation complète d'un fichier uploadé.

**Paramètres**:
- `file`: Objet FileStorage de Flask
- `expected_type`: Type attendu (`'pdf'`, `'image'`, `'spreadsheet'`)
- `field_name`: Nom du champ pour les messages d'erreur

**Retour**: `(True, None)` si valide, `(False, "message d'erreur")` sinon

**Exemples d'erreurs**:
- `"Lettre de mission : Fichier non fourni ou invalide."`
- `"Organigramme : Seuls les fichiers PDF sont acceptés (reçu : .txt)."`
- `"Planning : Seuls les fichiers XLSX, XLS, CSV sont acceptés (reçu : .pdf)."`

---

#### `create_audit_folder_structure(entreprise_nom, date_creation)`
```python
def create_audit_folder_structure(entreprise_nom, date_creation):
    """
    Crée une structure de dossiers organisée pour un audit
    
    Format: uploads/{NomEntreprise}_{YYYYMMDD}/
    """
```

Génère automatiquement l'arborescence de dossiers.

**Paramètres**:
- `entreprise_nom`: Nom de l'entreprise (sera nettoyé)
- `date_creation`: Date de création (datetime)

**Retour**: Chemin relatif du dossier racine (ex: `"uploads/TechCorp_20240115"`)

**Structure créée**:
```
uploads/
└── NomEntreprise_20240115/
    ├── bloc_00_general/
    ├── bloc_01_administratif/
    └── bloc_02_contexte/
```

---

#### `save_uploaded_file(file, subfolder, expected_type='all')`
```python
def save_uploaded_file(file, subfolder, expected_type='all'):
    """
    Sauvegarde un fichier uploadé avec validation de type
    
    Returns:
        tuple: (file_path: str or None, error_message: str or None)
    """
```

Version améliorée qui valide le type avant sauvegarde.

**Paramètres**:
- `file`: Objet FileStorage
- `subfolder`: Sous-dossier de destination
- `expected_type`: Type attendu (par défaut `'all'`)

**Retour**: `(chemin, None)` si succès, `(None, "erreur")` si échec

**Exemple d'utilisation**:
```python
path, error = save_uploaded_file(contrat_file, f'{audit_folder}/bloc_01_administratif', 'pdf')
if error:
    flash(f'❌ {error}', 'danger')
    return redirect(...)
```

---

#### `validate_contacts(form_data)`
```python
def validate_contacts(form_data):
    """
    Vérifie qu'au moins un contact principal est désigné
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
```

Parcourt tous les contacts du formulaire pour vérifier la présence d'un contact principal.

**Paramètres**:
- `form_data`: Données du formulaire (`request.form`)

**Retour**: 
- `(True, None)` si au moins un contact principal existe
- `(False, "Au moins un 'Contact Principal' doit être désigné.")` sinon

---

### 2. Routes Modifiées

#### `nouveau_projet()` - Ligne 199
**Changements**:
1. **Validation des contacts** au début du POST:
   ```python
   contacts_valid, contact_error = validate_contacts(request.form)
   if not contacts_valid:
       flash(f'❌ {contact_error}', 'danger')
       return redirect(url_for('main.nouveau_projet'))
   ```

2. **Création de la structure de dossiers**:
   ```python
   audit_folder = create_audit_folder_structure(entreprise.nom, datetime.now())
   flash(f'📁 Dossier audit créé : {audit_folder}/', 'info')
   ```

3. **Validation de l'organigramme (image)**:
   ```python
   is_valid, error_msg = validate_file_type(organigramme_file, 'image', 'Organigramme')
   if not is_valid:
       flash(f'❌ {error_msg}', 'danger')
       return redirect(...)
   
   organigramme_path, upload_error = save_uploaded_file(
       organigramme_file, 
       'entreprises',
       'image'
   )
   ```

4. **Validation des documents administratifs (PDF)**:
   ```python
   # Lettre de mission
   is_valid, error_msg = validate_file_type(lettre_mission_file, 'pdf', 'Lettre de mission')
   lettre_mission_path, upload_error = save_uploaded_file(
       lettre_mission_file,
       f'{audit_folder}/bloc_01_administratif',
       'pdf'
   )
   
   # Contrat
   is_valid, error_msg = validate_file_type(contrat_file, 'pdf', 'Contrat')
   # ... similaire
   ```

5. **Validation du planning (tableur)**:
   ```python
   is_valid, error_msg = validate_file_type(planning_file, 'spreadsheet', 'Planning')
   planning_path, upload_error = save_uploaded_file(
       planning_file,
       f'{audit_folder}/bloc_01_administratif',
       'spreadsheet'
   )
   ```

---

#### `modifier_entreprise()` - Ligne 510
**Changements**:
- Validation stricte de l'organigramme (image uniquement)
- Messages d'erreur spécifiques
- Gestion des erreurs avec retour au formulaire

```python
is_valid, error_msg = validate_file_type(organigramme_file, 'image', 'Organigramme')
if not is_valid:
    flash(f'❌ {error_msg}', 'danger')
    return redirect(url_for('main.modifier_entreprise', entreprise_id=entreprise_id))

organigramme_path, upload_error = save_uploaded_file(
    organigramme_file,
    'entreprises',
    'image'
)
```

---

#### `modifier_audit()` - Ligne 565
**Changements**:
- Recréation de la structure de dossiers si nécessaire
- Validation PDF pour lettre de mission et contrat
- Validation tableur pour planning
- Stockage dans les bons sous-dossiers (`bloc_01_administratif/`)

```python
audit_folder = create_audit_folder_structure(entreprise.nom, audit.date_creation or datetime.now())

# Lettre de mission (PDF)
is_valid, error_msg = validate_file_type(lettre_mission_file, 'pdf', 'Lettre de mission')
lettre_mission_path, upload_error = save_uploaded_file(
    lettre_mission_file,
    f'{audit_folder}/bloc_01_administratif',
    'pdf'
)

# Contrat (PDF)
# Planning (Spreadsheet)
# ... similaire
```

---

## 🎯 Exemples d'Utilisation

### Scénario 1: Upload d'un fichier incorrect
**Action**: L'utilisateur tente d'uploader un `.txt` comme contrat  
**Résultat**: 
```
❌ Contrat : Seuls les fichiers PDF sont acceptés (reçu : .txt).
```
Le formulaire est réaffiché sans créer l'audit.

---

### Scénario 2: Aucun contact principal
**Action**: L'utilisateur crée 3 contacts mais aucun n'est marqué "principal"  
**Résultat**:
```
❌ Au moins un 'Contact Principal' doit être désigné.
```

---

### Scénario 3: Création réussie
**Action**: L'utilisateur soumet un formulaire valide  
**Résultat**:
```
✅ Projet d'audit "Audit IT TechCorp 2024" créé avec succès ! (2 contact(s) ajouté(s))
📁 Dossier audit créé : uploads/TechCorp_20240115/
```

Structure créée:
```
uploads/
└── TechCorp_20240115/
    ├── bloc_00_general/
    ├── bloc_01_administratif/
    │   ├── contrat_abc123.pdf
    │   ├── lettre_mission_xyz789.pdf
    │   └── planning_def456.xlsx
    └── bloc_02_contexte/
```

---

## 📊 Tableau des Validations

| Champ | Type Accepté | Extensions | Route Concernée |
|-------|-------------|------------|-----------------|
| Organigramme | `image` | `.png`, `.jpg`, `.jpeg`, `.gif` | `nouveau_projet`, `modifier_entreprise` |
| Lettre de mission | `pdf` | `.pdf` | `nouveau_projet`, `modifier_audit` |
| Contrat | `pdf` | `.pdf` | `nouveau_projet`, `modifier_audit` |
| Planning | `spreadsheet` | `.xlsx`, `.xls`, `.csv` | `nouveau_projet`, `modifier_audit` |
| Contacts | N/A | Au moins 1 principal requis | `nouveau_projet` |

---

## 🚀 Tests Recommandés

### Test 1: Validation Upload PDF
```bash
# Tenter d'uploader une image comme contrat
curl -F "contrat=@image.png" http://localhost:5000/nouveau-projet
# Attendu: Erreur "Seuls les fichiers PDF sont acceptés"
```

### Test 2: Validation Contact Principal
```bash
# Créer 2 contacts sans principal
# Attendu: Erreur "Au moins un 'Contact Principal' doit être désigné"
```

### Test 3: Structure Dossiers
```bash
# Créer un audit pour "Tech & Co."
# Vérifier: uploads/TechCo_20240115/ existe
ls -la uploads/
```

### Test 4: Validation Image
```bash
# Uploader un PDF comme organigramme
# Attendu: Erreur "Seules les images sont acceptées"
```

---

## 📝 Notes de Migration

### Depuis v1.1
- ✅ **Rétrocompatible**: Les audits existants continuent de fonctionner
- ⚠️ **Structure dossiers**: Les nouveaux audits utilisent la nouvelle structure
- ℹ️ **Fichiers existants**: Restent dans `uploads/audits/*` (pas de migration)

### Prochaines Évolutions
- [ ] Migration automatique des anciens fichiers vers nouvelle structure
- [ ] Validation côté client (JavaScript) pour feedback immédiat
- [ ] Compression automatique des images
- [ ] Prévisualisation des fichiers uploadés

---

## 🐛 À Signaler

Si vous rencontrez des problèmes:
1. Vérifier les permissions sur `uploads/`
2. Vérifier les extensions dans `ALLOWED_EXTENSIONS`
3. Consulter les logs Flask pour les erreurs détaillées

---

**✅ Version 1.2 - Validations Robustes Complète**
