
# Manuel — Format des référentiels YAML (`frameworks/*.yaml`)

<!-- SCOPE: Manuel d'édition d'un référentiel d'audit YAML (frameworks/*.yaml) — structure attendue, champs obligatoires/optionnels, valeurs autorisées et règles de synchronisation au démarrage backend -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu ajoutes ou edites un referentiel YAML dans frameworks/. -->
<!-- SKIP_WHEN: Tu cherches l'API REST des frameworks ou le modele DB. -->
<!-- PRIMARY_SOURCES: frameworks/*.yaml, backend/app/services/framework_service.py -->

## Quick Navigation

- [Emplacement](#emplacement)
- [Structure de haut niveau](#structure-de-haut-niveau)
- [Exemple minimal de structure](#exemple-minimal-de-structure)
- [Règles de validation et synchronisation](#r-gles-de-validation-et-synchronisation)
- [Workflow d'édition](#workflow-d-dition)
- [Anti-patrons fréquents](#anti-patrons-fr-quents)
- [Maintenance](#maintenance)

Ce manuel décrit la structure attendue des fichiers YAML déposés dans le répertoire `frameworks/` à la racine du dépôt. Ces fichiers représentent les référentiels de conformité (CIS, ANSSI, audits internes) et sont **auto-synchronisés en base** au démarrage du backend (table `framework`).

## Agent Entry

Quand lire ce document : Tu ajoutes ou edites un referentiel YAML dans frameworks/.

Quand l'ignorer : Tu cherches l'API REST des frameworks ou le modele DB.

Sources primaires (auto-discovery) : `frameworks/*.yaml, backend/app/services/framework_service.py`

## Emplacement

Tous les référentiels résident dans `frameworks/` à la racine du dépôt et sont montés en lecture dans le conteneur backend (volume `./frameworks`). Le nom du fichier doit correspondre à `<ref_id>.yaml` (kebab ou snake_case).

## Structure de haut niveau

Un fichier valide contient une racine `framework:` avec les champs métadonnées, suivie d'une liste `categories:` regroupant les contrôles.

| Champ | Niveau | Type | Obligatoire | Description |
|-------|--------|------|-------------|-------------|
| `ref_id` | framework | string | oui | Identifiant unique stable (sert de clé en base). |
| `name` | framework | string | oui | Libellé d'affichage en français. |
| `description` | framework | string | recommandé | Présentation courte du référentiel. |
| `version` | framework | string | oui | Numéro de version sémantique du référentiel (`1.0`, `2.1.3`). |
| `engine` | framework | enum | oui | `manual`, `semi-automatic`, ou `automatic` selon le mode d'évaluation. |
| `source` | framework | string | optionnel | URL ou référence du document source (ex. CIS Benchmark URL). |
| `author` | framework | string | optionnel | Auteur ou organisme à l'origine du référentiel. |
| `categories` | framework | list | oui | Liste des chapitres regroupant les contrôles. |
| `name` | category | string | oui | Titre de la catégorie (FR). |
| `description` | category | string | recommandé | Phrase décrivant le périmètre de la catégorie. |
| `controls` | category | list | oui | Liste des contrôles de la catégorie. |
| `id` | control | string | oui | Identifiant court unique au sein du référentiel (ex. `FW-001`). |
| `title` | control | string | oui | Intitulé court du contrôle (FR). |
| `description` | control | string | oui | Description vérifiable du critère attendu. |
| `severity` | control | enum | oui | `critical`, `high`, `medium`, `low`, `info`. |
| `check_type` | control | enum | oui | `manual`, `semi-automatic`, `automatic`. |
| `evidence_required` | control | bool | optionnel | `true` si une preuve doit être attachée (capture, export). |
| `remediation` | control | string | recommandé | Instructions de correction proposées à l'auditeur. |
| `effort_days` | control | number | optionnel | Estimation indicative pour le plan de remédiation. |

## Exemple minimal de structure

```yaml
framework:
  ref_id: example_audit
  name: "Audit Exemple"
  version: "1.0"
  engine: manual
  categories:
    - name: "Configuration de base"
      controls:
        - id: EX-001
          title: "Mot de passe admin modifié"
          severity: critical
          check_type: manual
```

## Règles de validation et synchronisation

- Le démarrage du backend lit chaque fichier `frameworks/*.yaml`, le valide, puis met à jour la table `framework` (insertion ou mise à jour idempotente sur `ref_id`).
- Une `version` modifiée déclenche une nouvelle entrée — les évaluations existantes restent rattachées à l'ancienne version.
- Les `id` de contrôle doivent rester stables entre versions : un changement d'`id` casse les évaluations historiques.
- YAML strict : pas de tabulations, indentation par espaces, guillemets recommandés pour les chaînes contenant `:` ou `#`.
- Aucune entité externe XML/YAML — la lecture utilise PyYAML et `defusedxml` au niveau du parser ; ne jamais référencer `!!python/object` ou tags personnalisés.

## Workflow d'édition

1. Copier un référentiel proche (`firewall_audit.yaml`, `wifi_audit.yaml`) comme point de départ.
2. Choisir un `ref_id` unique et un nom de fichier cohérent.
3. Renseigner les catégories puis les contrôles avec un `id` préfixé (ex. `LIN-001` pour Linux, `WIN-001` pour Windows).
4. Lancer le backend en local — les erreurs de format apparaissent dans les logs au moment de la synchronisation.
5. Vérifier en base ou via l'API `GET /api/v1/frameworks` que le référentiel est bien chargé.
6. Couvrir le nouveau référentiel par un test si la criticité le justifie (`backend/tests/test_framework_loading.py` ou équivalent).

## Anti-patrons fréquents

- Réutiliser un `ref_id` déjà pris par un autre fichier — provoque un écrasement silencieux.
- Oublier `severity` ou `check_type` — l'évaluation et le rapport PDF affichent alors des valeurs par défaut peu informatives.
- Mettre des secrets (mots de passe d'exemple, tokens) dans `description` ou `remediation` — ces fichiers sont versionnés.
- Modifier l'`id` d'un contrôle après publication — historique d'audit cassé.

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

- **Dernière mise à jour :** 2026-05-01
- **Déclencheurs de mise à jour :** ajout d'un nouveau champ supporté côté loader, changement d'enum (`severity`, `check_type`), évolution du moteur d'évaluation.
- **Vérification :** confirmer que `backend/app/services/framework*.py` accepte tous les champs documentés et que les tests de chargement (`backend/tests/`) couvrent au moins un référentiel `manual`, `semi-automatic` et `automatic`.
