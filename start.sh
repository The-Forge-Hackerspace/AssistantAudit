#!/bin/bash

# Script de démarrage rapide pour AssistantAudit

echo "════════════════════════════════════════════════════════════════════"
echo "   🚀 AssistantAudit - Démarrage de l'application"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Vérifier si l'environnement virtuel est activé
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  L'environnement virtuel n'est pas activé."
    echo "   Activation de l'environnement virtuel..."
    source venv/bin/activate
fi

echo "✅ Environnement virtuel activé"
echo ""

# Vérifier si la base de données existe
if [ ! -f "instance/assistantaudit.db" ]; then
    echo "📊 Initialisation de la base de données avec des données d'exemple..."
    python init_db.py
    echo ""
fi

echo "════════════════════════════════════════════════════════════════════"
echo "   Lancement du serveur Flask..."
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "📌 URL de l'application : http://127.0.0.1:5000"
echo ""
echo "📋 Pages disponibles :"
echo "   • http://127.0.0.1:5000/              → Accueil"
echo "   • http://127.0.0.1:5000/nouveau-projet → Nouveau projet d'audit"
echo "   • http://127.0.0.1:5000/entreprises    → Liste des entreprises"
echo ""
echo "💡 Appuyez sur Ctrl+C pour arrêter le serveur"
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Lancer l'application
python run.py
