
# ADR-002 — Authentification des agents (mTLS X.509 + JWT)

<!-- SCOPE: Décision d'architecture sur l'authentification des agents Windows distants (mTLS X.509 + JWT court) — couvre l'enrollment, l'authentification continue et la révocation -->
<!-- DOC_KIND: record -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Tu touches a l'enrollment agent ou a la securite du canal serveur <-> daemon. -->
<!-- SKIP_WHEN: Tu cherches une procedure runtime ou la documentation API. -->
<!-- PRIMARY_SOURCES: backend/app/core/cert_manager.py, backend/app/api/v1/agents.py, backend/app/api/v1/websocket.py -->

## Quick Navigation

- [Statut](#statut)
- [Contexte](#contexte)
- [Décision](#d-cision)
- [Conséquences](#cons-quences)
- [Maintenance](#maintenance)

## Agent Entry

Quand lire ce document : Tu touches a l'enrollment agent ou a la securite du canal serveur <-> daemon.

Quand l'ignorer : Tu cherches une procedure runtime ou la documentation API.

Sources primaires (auto-discovery) : `backend/app/core/cert_manager.py, backend/app/api/v1/agents.py, backend/app/api/v1/websocket.py`

## Statut

Acceptée (2026-05-01)

## Contexte

La plateforme AssistantAudit pilote des agents distants déployés sur des postes Windows (par exemple `win-agent`, 172.16.20.21) qui exécutent des collectes sensibles : inventaires Active Directory, scans Monkey365, exécutions PowerShell, exports de configurations. Les agents communiquent avec le backend FastAPI via HTTPS (REST + WebSocket persistant pour le streaming des sorties et le heartbeat).

Le canal d'authentification doit satisfaire plusieurs contraintes simultanées :

- **Authentification forte des deux extrémités** : un agent compromis ne doit pas pouvoir usurper l'identité d'un autre agent, et un faux backend ne doit pas pouvoir manipuler un agent.
- **Bootstrap sans mot de passe partagé** : les agents sont déployés en masse, on ne veut pas distribuer un secret long terme par image.
- **Révocation rapide** d'un agent compromis ou désaffecté, sans redémarrage du backend.
- **Sessions courtes pour les opérations applicatives** afin de limiter la fenêtre d'abus en cas de fuite mémoire d'un token.
- **Compatibilité avec les WebSocket FastAPI** (handshake initial puis canal long-vivant).

Trois schémas étaient envisageables :

1. **JWT seul** sur HTTPS standard — simple côté code, mais l'authentification côté serveur repose sur un seul facteur logiciel (le secret JWT) et la révocation par liste noire est coûteuse à grande échelle.
2. **mTLS seul** — authentification cryptographique forte, mais l'autorisation par requête (scopes, audit identity du caller, expiration courte) doit être ré-encodée par-dessus, et le rafraîchissement d'identité demande de reposer la connexion TLS.
3. **mTLS + JWT court (retenu)** — défense en profondeur : la couche transport authentifie le matériel/agent, la couche applicative porte l'identité métier et expire rapidement.

## Décision

L'authentification des agents repose sur **deux couches indépendantes** :

- **Couche transport — mTLS X.509** : une autorité de certification interne (CA) signe un certificat client par agent lors de l'enrollment. Le backend exige un certificat client valide (chemin `CA_CERT_PATH`), accepte une CRL (`CRL_PATH`) pour révoquer un agent compromis, et associe le `CN` du certificat à l'identité d'agent enregistrée en base.
- **Couche applicative — JWT signé** : après le handshake mTLS, l'agent obtient un token JWT court (signé avec `SECRET_KEY`, algorithme HMAC) qui porte l'`agent_id`, les scopes (collectes autorisées) et une expiration courte. Le token est rafraîchi périodiquement, permettant de propager rapidement les changements d'autorisation sans toucher aux certificats.

L'enrollment d'un nouvel agent suit un flux : génération d'un CSR côté agent → soumission par un opérateur authentifié → signature par la CA interne (`cert_manager`) → distribution du certificat + bootstrap JWT initial.

## Conséquences

**Positives :**

- Compromission isolée : un secret applicatif fuité ne suffit pas (il faut aussi le matériel cryptographique du certificat).
- Révocation immédiate possible via la CRL (transport) ET via la blacklist applicative côté backend (token).
- Audit traçable : le `CN` du certificat est journalisé sur chaque requête et corroboré avec l'`agent_id` du JWT — toute incohérence est un signal d'alerte.
- Le canal WebSocket bénéficie de l'authentification mTLS dès le handshake, sans devoir réécrire un protocole d'authentification au-dessus du flux.

**Négatives / contraintes :**

- Opérations PKI à maintenir : rotation de la CA, génération/distribution des certificats, supervision de la CRL — coût opérationnel non nul.
- Échec d'agent en cas de désynchronisation horloge (mTLS et JWT sont sensibles à `notBefore`/`exp`) : nécessite NTP côté agents.
- Le reverse proxy externe (NPMPlus en prod, Caddy en staging) doit être configuré pour passer le certificat client (`X-SSL-Client-*` ou TLS pass-through), sous peine de casser la chaîne de confiance.
- La perte de la clé privée de la CA forcerait une réémission complète des certificats agents — impose une procédure de sauvegarde sécurisée distincte de `ENCRYPTION_KEY`.

## Maintenance

**Update Triggers** : modification du contenu source, changement de structure, correction de reference, evolution de la stack ou de la spec.
**Verification** : revue manuelle annuelle ou a chaque changement majeur ; relance du verifier docs-quality apres edit.
**Last Updated** : 2026-05-01

- **Dernière mise à jour :** 2026-05-01
- **Déclencheurs de mise à jour :** changement de l'algorithme JWT, modification de la durée de vie des tokens, évolution du flux d'enrollment, ajout d'un mécanisme alternatif (par exemple OIDC pour les agents managés).
- **Vérification :** confirmer que `core/cert_manager.py`, `core/security.py` et la documentation des variables `CA_CERT_PATH`/`CA_KEY_PATH`/`CRL_PATH` restent cohérents avec cet ADR.
