#!/bin/bash

# ============================================================================
# SCRIPT DE DÉMARRAGE - IT Audit Management System v1.2
# ============================================================================

echo "🚀 Démarrage du système de gestion d'audits IT"
echo "================================================"

# Vérifier si venv existe
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer venv
source venv/bin/activate

# Installer les dépendances
echo "📚 Installation des dépendances..."
pip install -q Flask==3.1.2 Flask-SQLAlchemy==3.1.1 SQLAlchemy==2.0.46 Werkzeug==3.0.1

# Initialiser la base de données si nécessaire
if [ ! -f "instance/assistantaudit.db" ]; then
    echo "🗄️  Initialisation de la base de données..."
    python init_db.py
fi

# Démarrer le serveur
echo ""
echo "✅ Démarrage du serveur sur http://localhost:5000"
echo ""
echo "📌 Applications disponibles:"
echo "   • Accueil: http://localhost:5000/"
echo "   • Nouveau projet: http://localhost:5000/nouveau-projet"
echo "   • Entreprises: http://localhost:5000/entreprises"
echo ""

python run.py
