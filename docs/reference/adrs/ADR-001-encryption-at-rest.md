# ADR-001 — Chiffrement des données au repos

<!-- SCOPE: Decision architecturale : chiffrement au repos AES-256-GCM enveloppe KEK+DEK pour fichiers et colonnes sensibles. -->
<!-- DOC_KIND: record -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu touches au chiffrement applicatif ou ajoutes une colonne sensible. -->
<!-- SKIP_WHEN: Tu cherches une procedure runtime (rotation KEK : voir runbook.md). -->
<!-- PRIMARY_SOURCES: backend/app/core/encryption.py, backend/app/core/file_encryption.py, backend/scripts/rotate_kek.py -->

## Quick Navigation

- [Statut](#statut)
- [Contexte](#contexte)
- [Décision](#d-cision)
- [Conséquences](#cons-quences)

## Agent Entry

Quand lire ce document : Tu touches au chiffrement applicatif ou ajoutes une colonne sensible.

Quand l'ignorer : Tu cherches une procedure runtime (rotation KEK : voir runbook.md).

Sources primaires (auto-discovery) : `backend/app/core/encryption.py, backend/app/core/file_encryption.py, backend/scripts/rotate_kek.py`

## Statut

Acceptée (2026-03-29)

## Contexte

L'application stocke des données sensibles : credentials Active Directory, résultats de scans réseau, configurations d'équipements. Ces données transitent et persistent en base SQLite/PostgreSQL ainsi que dans des fichiers exportés (rapports PDF, exports JSON).

Une fuite de la base de données ou du système de fichiers ne doit pas exposer ces informations en clair. Il faut donc chiffrer au niveau de la couche persistance, de façon transparente pour le reste du code applicatif.

## Décision

Chiffrement des colonnes sensibles via des **SQLAlchemy TypeDecorators** personnalisés :

- `EncryptedText` — pour les champs texte (mots de passe, tokens, adresses IP sensibles)
- `EncryptedJSON` — pour les structures de données complexes (résultats de scans, configurations)

Algorithme retenu : **AES-256-GCM** (authentifié, résistant aux attaques par manipulation de ciphertext).

Pour les fichiers (rapports, exports), adoption d'un schéma **envelope encryption** :

- Une **KEK** (Key Encryption Key) dérivée de la configuration serveur chiffre une **DEK** (Data Encryption Key) générée aléatoirement par fichier.
- Seule la DEK chiffrée est stockée aux côtés du fichier.

La KEK est injectée via variable d'environnement (`ENCRYPTION_KEY`) et ne réside jamais en base.

## Conséquences

**Positives :**

- Transparence pour le code applicatif : les services lisent et écrivent des valeurs Python ordinaires, le chiffrement/déchiffrement est géré par les TypeDecorators.
- Overhead minimal : AES-GCM est accéléré matériellement sur les CPU modernes.
- Rotation de la KEK possible sans re-chiffrer les DEK des fichiers existants (seule l'enveloppe est à remplacer).
- Isolation des compromissions : la compromission d'un fichier n'expose pas les clés des autres fichiers.

**Négatives / contraintes :**

- Les colonnes chiffrées ne sont pas interrogeables par SQL (pas de `WHERE col = ?` sur un champ `EncryptedText`).
- La perte de la KEK rend les données irrécupérables — nécessite une procédure de sauvegarde sécurisée de la clé.
- Légère augmentation de la taille des données stockées (IV + tag GCM + base64).

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.

**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.

**Last Updated** : 2026-05-01
