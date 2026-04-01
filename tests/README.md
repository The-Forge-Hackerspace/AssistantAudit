# Tests — AssistantAudit

## Vue d'ensemble

688+ tests backend (pytest), Playwright E2E frontend. Score cible : 0 échecs.

## Exécution

```bash
# Backend
cd backend && pytest -q
pytest -v                                   # verbeux
pytest tests/test_websocket.py -v          # fichier unique
pytest --cov=app --cov-report=html         # couverture HTML

# Frontend E2E
cd frontend && npx playwright test
```

## Structure des tests backend

Répertoire : `backend/tests/`

| Fichier | Couverture |
|---|---|
| `test_encrypted_json.py` | TypeDecorator EncryptedJSON |
| `test_encryption.py` | Chiffrement AES-256-GCM |
| `test_file_encryption.py` | Chiffrement enveloppe (KEK+DEK) |
| `test_health_check.py` | Endpoints health / ready / liveness |
| `test_websocket.py` | Communication WebSocket agent |
| `test_websocket_orphan_tasks.py` | Nettoyage des tâches orphelines |
| `test_websocket_task_isolation.py` | Isolation des tâches par agent |

## Couverture actuelle

**Bien couverts**
- Auth / sécurité, RBAC et isolation multi-tenant
- Chiffrement (AES-256-GCM, enveloppe KEK+DEK)
- WebSocket et cycle de vie des agents
- API globale (endpoints principaux)

**Non couverts**
- ~30 services sans test dédié (`scan_service`, `collect_service`, `ad_audit_service`…)
- Outils (`ssh_collector`, `nmap_scanner`, `ssl_checker`…)
- Frontend : 0 tests unitaires (Playwright E2E à étoffer)

## Conventions

- Fixtures pytest centralisées dans `conftest.py`
- Monkeypatch pour les dépendances externes
- Répertoires temporaires pour les tests de fichiers
- Aucun test async sur les services (backend synchrone)

## Objectifs

- Couverture cible : **> 80 %**
- Ajout de tests frontend (Playwright E2E + Vitest composants)
