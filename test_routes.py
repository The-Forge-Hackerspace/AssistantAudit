"""
Script de test de l'application web AssistantAudit
Affiche les routes disponibles et démarre le serveur
"""
from app import create_app

def list_routes():
    """Liste toutes les routes disponibles dans l'application"""
    app = create_app()
    
    print("=" * 80)
    print("🚀 ROUTES DISPONIBLES DANS L'APPLICATION")
    print("=" * 80)
    print()
    
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
            routes.append((rule.rule, methods, rule.endpoint))
    
    # Trier par URL
    routes.sort()
    
    print(f"{'URL':<50} {'MÉTHODES':<15} {'ENDPOINT'}")
    print("-" * 80)
    
    for url, methods, endpoint in routes:
        print(f"{url:<50} {methods:<15} {endpoint}")
    
    print()
    print("=" * 80)
    print(f"✅ Total : {len(routes)} routes disponibles")
    print("=" * 80)
    print()
    print("📌 PAGES PRINCIPALES :")
    print("   • http://127.0.0.1:5000/              → Page d'accueil")
    print("   • http://127.0.0.1:5000/nouveau-projet → Créer un projet d'audit")
    print("   • http://127.0.0.1:5000/entreprises    → Liste des entreprises")
    print()
    print("💡 Pour démarrer le serveur : python run.py")
    print("💡 Pour initialiser avec des données : python init_db.py")
    print()


if __name__ == '__main__':
    list_routes()
