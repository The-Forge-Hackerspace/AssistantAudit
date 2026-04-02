# Scripts de tests manuels

> **SCOPE:** Scripts bash pour la validation manuelle des criteres d'acceptation. Complement aux tests automatises.

## Demarrage rapide

```bash
cd tests/manual
./test-all.sh                 # Executer TOUS les suites de tests
```

## Prerequis

- Conteneurs Docker en cours d'execution (`docker compose ps`)
- jq installe (`apt-get install jq` ou `brew install jq`)
- curl installe

## Structure

```
tests/manual/
├── config.sh          # Configuration partagee (BASE_URL, helpers, couleurs)
├── README.md          # Ce fichier
├── test-all.sh        # Lancer toutes les suites de tests
├── results/           # Resultats des tests (dans .gitignore)
└── {NN}-{sujet}/      # Suites de tests par Story
    ├── expected/      # Fichiers de reference attendus
    └── test-{slug}.sh # Script de test
```

## Suites de tests disponibles

| Suite | Story | AC Couverts | Commande |
|-------|-------|-------------|----------|
| 01-docker-hardening | TOS-6 | Image <500MB, Health checks, Resource limits, Trivy CI, Non-root | `cd tests/manual && ./01-docker-hardening/test-docker-hardening.sh` |

## Ajouter un nouveau test

1. Creer le script dans `{NN}-{sujet}/test-{slug}.sh`
2. **Mettre a jour ce README** (table Suites de tests disponibles)
3. **Mettre a jour `test-all.sh`** (ajouter au tableau SUITES)
