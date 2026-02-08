# AssistantAudit - Module Administratif & Client

Application Flask pour la gestion des audits IT avec module administratif et client.

**Version actuelle : 1.1** - [Voir les améliorations](AMELIORATIONS_v1.1.md)

## 🚀 Fonctionnalités

### ✅ Workflow "Nouveau Projet d'Audit"
- **Formulaire multi-étapes (Wizard)** avec 3 étapes :
  - **Étape 1** : Informations Entreprise (création ou sélection existante)
  - **Étape 2** : Ajout dynamique de contacts clés
  - **Étape 3** : Cadrage de l'audit avec upload de documents

### 📊 Tableaux de bord
- **Vue détail audit** avec blocs :
  - **Bloc 00** : Informations générales
  - **Bloc 01** : Documents administratifs (lettre mission, contrat, planning)
  - **Bloc 02** : Contexte de l'audit (objectifs, limites, hypothèses, risques)

### 🏢 Gestion des entités
- Entreprises clientes (création, affichage, **édition**)
- Contacts (avec contact principal)
- Sites/établissements
- Projets d'audit (NOUVEAU, EN_COURS, TERMINE)
- **Modification des audits à tout moment** (même après démarrage)

### 📝 Édition et modifications (v1.1)
- ✅ **Modifier une entreprise** : tous les champs + upload nouvel organigramme
- ✅ **Modifier un audit** : nom, documents, contexte (à tout moment, quel que soit le statut)
- ✅ **Remplacement de documents** : upload de nouveaux fichiers pour remplacer les anciens
- ✅ Navigation améliorée : carte "Entreprises" cliquable sur l'accueil

### 📁 Gestion des fichiers
- Upload sécurisé de documents (PDF, images, Excel)
- Stockage organisé par type de document
- Limitation de taille (16 MB max)

## 📁 Structure de la base de données

### Tables principales

1. **Entreprise** - Informations sur les entreprises clientes
2. **Contact** - Contacts au sein des entreprises
3. **Audit** - Projets d'audit (avec blocs Administratif et Contexte)
4. **Site** - Sites/établissements des entreprises

## 🛠️ Installation

```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Initialiser la base avec des données d'exemple (optionnel)
python init_db.py
```

## 🚀 Utilisation

### Lancer l'application

```bash
python run.py
```

L'application sermodifier`** : ✨ Modifier un audit (nom, documents, contexte)
- **`/audit/<id>/ajouter-site`** : Ajout d'un site
- **`/entreprises`** : Liste des entreprises
- **`/entreprise/<id>`** : Détails d'une entreprise
- **`/entreprise/<id>/modifier`** : ✨ Modifier 

- **`/`** : Page d'accueil avec statistiques et liste des audits
- **`/nouveau-projet`** : Formulaire wizard de création de projet
- **`/audit/<id>`** : Vue détail d'un audit
- **`/audit/<id>/ajouter-site`** : Ajout d'un site
- **`/entreprises`** : Liste des entreprises
- **`/entreprise/<id>`** : Détails d'une entreprise

### 📝 Créer un nouveau projet d'audit

1. Cliquez sur **"Nouveau Projet d'Audit"**
2. **Étape 1** : Saisissez les informations de l'entreprise (ou sélectionnez une existante)
   - Uploadez l'organigramme si disponible
3. **Étape 2** : Ajoutez les contacts clés
   - Cliquez sur "Ajouter un contact" pour ajouter plusieurs contacts
   - Marquez le contact principal
4. **Étape 3** : Définissez le cadrage de l'audit
   - Uploadez les documents administratifs (lettre de mission, contrat, planning)
   - Renseignez les objectifs, limites, hypothèses et risques
5. Validez pour créer le projet

### 📂 Structure des dossiers d'upload

```
uploads/
├── entreprises/           # Organigrammes
├── audits/
│   ├── lettres_mission/   # Lettres de mission
│   ├── contrats/          # Contrats
│   └── plannings/         # Plannings
```

## 🧪 Utiliser le shell interactif

```bash
flask shell
```

### Exemples de requêtes dans le shell

```python
# Récupérer tous les audits en cours
from app.models import Audit, AuditStatus
audits_en_cours = Audit.query.filter_by(status=AuditStatus.EN_COURS).all()

# Trouver une entreprise par nom
from app.models import Entreprise
entreprise = Entreprise.query.filter_by(nom='TechSecure Solutions').first()

# Voir tous les audits d'une entreprise
print(entreprise.audits.all())

# Voir tous les contacts d'une entreprise
print(entreprise.contacts.all())

# Ajouter un nouveau site
from app.models import Site
from app import db
site = Site(
    nom="Bureau régional Marseille",
    adresse="10 Rue de la République, 13001 Marseille",
    entreprise_id=entreprise.id
)
db.session.add(site)
db.session.commit()
```

## 🎨 Technologies utilisées

- **Backend** : Flask 3.1.2, SQLAlchemy 2.0.46
- **Frontend** : Bootstrap 5.3.2, Bootstrap Icons
- **Base de données** : SQLite
- **Upload** : Werkzeug (secure_filename)

## 📸 Aperçu des fonctionnalités

### Formulaire Wizard
- Interface intuitive en 3 étapes
- Ajout dynamique de contacts avec JavaScript
- Upload de fichiers sécurisé
- Validation à chaque étape

### Vue détail audit
- Tableau de bord complet
- Statut de l'audit (badges colorés)
- Liste des contacts et sites
- Indicateurs de documents disponibles
- Actions rapides (démarrer, terminer, ajouter site)

## 🔒 Sécurité

- Validation des extensions de fichiers
- Noms de fichiers sécurisés avec `secure_filename()`
- Horodatage des fichiers pour éviter les collisions
- Limitation de la taille des uploads (16 MB)

## 📝 Notes de développement

- Les fichiers uploadés sont stockés localement dans `uploads/`
- La base de données SQLite est dans `instance/assistantaudit.db`
- Les sessions Flask utilisent une clé secrète (à changer en production)
- Les timestamps des uploads évitent les conflits de noms

## 🔄 Workflow complet

1. **Création d'entreprise** (ou sélection existante)
2. **Ajout de contacts** clés
3. **Création du projet d'audit** avec documents
4. **Ajout de sites** si nécessaire
5. **Suivi de l'audit** via changements de statut
