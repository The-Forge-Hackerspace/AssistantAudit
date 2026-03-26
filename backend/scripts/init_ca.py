"""
Script d'initialisation de la CA privee interne.
A executer UNE SEULE FOIS a l'installation du serveur.

Usage :
    python scripts/init_ca.py
"""
import sys
from pathlib import Path

# Ajouter le backend au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.core.cert_manager import CertManager


def main() -> None:
    settings = get_settings()
    ca_cert_path = Path(settings.CA_CERT_PATH)
    ca_key_path = Path(settings.CA_KEY_PATH)

    if ca_cert_path.exists():
        print(f"ERREUR: {ca_cert_path} existe deja.")
        print("Refus d'ecraser une CA existante. Supprimez-la manuellement si necessaire.")
        sys.exit(1)

    if ca_key_path.exists():
        print(f"ERREUR: {ca_key_path} existe deja.")
        print("Refus d'ecraser une cle privee existante.")
        sys.exit(1)

    ca_cert_path.parent.mkdir(parents=True, exist_ok=True)

    print("Generation de la CA privee interne AssistantAudit...")
    CertManager.generate_ca(ca_cert_path, ca_key_path)

    print()
    print(f"  Certificat CA : {ca_cert_path}")
    print(f"  Cle privee CA : {ca_key_path}")
    print()
    print("IMPORTANT: Sauvegardez ca.key dans un endroit securise.")
    print("           Si cette cle est perdue, tous les agents devront etre re-enrolles.")
    print("           Ne commitez JAMAIS ca.key dans le depot git.")


if __name__ == "__main__":
    main()
