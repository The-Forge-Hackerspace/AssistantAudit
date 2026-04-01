# Coverage Gaps Audit Report

**Category:** Coverage Gaps (High Priority)
**Codebase:** AssistantAudit (backend)
**Date:** 2026-04-01
**Score:** 5.5/10

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 4 |
| HIGH | 5 |
| MEDIUM | 3 |
| LOW | 0 |
| **Total** | **12** |

**Money Flows:** N/A (not a financial application -- all keyword matches are French language false positives like "telecharger", "chargement")

---

## Findings

### CRITICAL Severity (Priority 20+)

#### GAP-001: Campaign State Machine Transitions -- No Tests
- **Category:** Security / Data Integrity
- **File:** `backend/app/services/assessment_service.py` -- `start_campaign()` (line 145), `complete_campaign()` (line 169)
- **Description:** Campaign state transitions (DRAFT -> IN_PROGRESS -> COMPLETED) mutate both Campaign and linked Equipement statuses in batch. No test validates this multi-entity state machine. If `start_campaign()` flushes the campaign status but equipement updates fail, the system enters an inconsistent state.
- **Why critical:** State corruption -- campaign appears started but equipements aren't marked EN_COURS. Compliance scores become unreliable.
- **Covered by E2E?** Partially by `test_phase1.py` (happy path only), but no error/edge case coverage.
- **Suggested test type:** Integration
- **Effort:** M
- **Suggested tests:**
  - `test_start_campaign_transitions_all_equipements_to_en_cours`
  - `test_start_campaign_already_in_progress_rejected`
  - `test_complete_campaign_recomputes_scores`
  - `test_complete_campaign_with_unassessed_controls`

#### GAP-002: SecurityHeadersMiddleware -- No Tests
- **Category:** Security
- **File:** `backend/app/main.py` -- `SecurityHeadersMiddleware` (line 93-127)
- **Description:** The middleware adds 7 critical security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy) and removes the Server header. Zero tests verify these headers are present and correct on responses.
- **Why critical:** Misconfigured security headers expose the application to clickjacking, MIME sniffing, XSS, and information disclosure. A regression would be silent.
- **Covered by E2E?** No.
- **Suggested test type:** Integration
- **Effort:** S
- **Suggested tests:**
  - `test_response_contains_csp_header`
  - `test_response_contains_x_frame_options_deny`
  - `test_response_removes_server_header`
  - `test_hsts_header_on_https_requests`

#### GAP-003: Production Config Enforcement -- No Tests
- **Category:** Security
- **File:** `backend/app/core/config.py` -- `model_post_init()` (line 58-76)
- **Description:** `model_post_init()` enforces critical security constraints in production: SECRET_KEY must be >= 32 bytes, ENCRYPTION_KEY and FILE_ENCRYPTION_KEY must be set. No test validates that the application refuses to start with weak/missing keys in production mode.
- **Why critical:** If these checks regress, production deployments could run with insecure defaults (auto-generated SECRET_KEY, disabled encryption).
- **Covered by E2E?** No.
- **Suggested test type:** Unit
- **Effort:** S
- **Suggested tests:**
  - `test_production_rejects_missing_secret_key`
  - `test_production_rejects_short_secret_key`
  - `test_production_rejects_missing_encryption_key`
  - `test_development_allows_missing_keys`

#### GAP-004: Network Scan Background Execution -- No Tests
- **Category:** Security / Data Integrity
- **File:** `backend/app/services/scan_service.py` -- `execute_scan_background()` (line 100-207)
- **Description:** Background nmap scan execution runs in a separate `SessionLocal()` with explicit `db.commit()`. Creates ScanHost and ScanPort records in batch. Equipment creation via `update_host_decision()` (line 210-296) has race conditions on duplicate IP checks between the SELECT and INSERT. No tests cover the actual scan execution, host persistence, or equipment creation from scan results.
- **Why critical:** Background session management is error-prone. A commit failure loses scan results silently. Equipment creation race condition can produce duplicates.
- **Covered by E2E?** No. `test_monkey365_api.py` mocks `execute_scan_background` entirely. `test_rbac_scan_hosts.py` tests access control only.
- **Suggested test type:** Integration
- **Effort:** L
- **Suggested tests:**
  - `test_execute_scan_persists_hosts_and_ports`
  - `test_scan_failure_sets_status_failed`
  - `test_update_host_decision_creates_equipement`
  - `test_update_host_decision_skips_duplicate_ip`

---

### HIGH Severity (Priority 15-19)

#### GAP-005: Campaign Cascade Delete (3-Level Chain) -- No Tests
- **Category:** Data Integrity
- **File:** `backend/app/services/assessment_service.py` -- `delete_campaign()` (line 201-212)
- **Description:** Deleting a campaign triggers a 3-level cascade: Campaign -> Assessment -> ControlResult -> Attachment. This cascade relies on SQLAlchemy `cascade="all, delete-orphan"` across three relationships. No test verifies this chain completes correctly or that associated files on disk are cleaned up.
- **Why critical:** Broken cascade leaves orphaned records. File attachments on disk become unreachable.
- **Suggested test type:** Integration
- **Effort:** M
- **Suggested tests:**
  - `test_delete_campaign_cascades_to_assessments_and_results`
  - `test_delete_campaign_cleans_attachment_files`

#### GAP-006: Framework Import/Update with Existing Assessments -- No Tests
- **Category:** Data Integrity
- **File:** `backend/app/services/framework_service.py` -- `_import_from_data()` (line 76-165)
- **Description:** Framework import deletes ALL old categories (which cascades to delete controls) before creating new ones. If existing assessments have ControlResult records pointing to old controls via FK, this cascade delete will break referential integrity. No test covers framework update when assessments reference old controls.
- **Why critical:** Updating a framework that's already been used in assessments could corrupt the database or fail with FK violations, making frameworks un-updatable.
- **Suggested test type:** Integration
- **Effort:** M
- **Suggested tests:**
  - `test_framework_update_with_existing_assessments_handles_fk`
  - `test_framework_import_creates_categories_and_controls`
  - `test_framework_import_idempotent`

#### GAP-007: Framework Deletion with Filesystem Cleanup -- No Tests
- **Category:** Data Integrity
- **File:** `backend/app/services/framework_service.py` -- `delete_framework()` (line 529-549)
- **Description:** Deletes framework from DB (cascades to categories/controls) then attempts to delete the YAML file from disk. If DB commit succeeds but file deletion fails, the system is in an inconsistent state. No test exists for this operation.
- **Why critical:** DB/filesystem desync -- framework deleted from DB but YAML still on disk would cause re-import on next startup.
- **Suggested test type:** Integration
- **Effort:** S
- **Suggested tests:**
  - `test_delete_framework_removes_db_and_yaml`
  - `test_delete_framework_with_active_assessments_blocked`

#### GAP-008: Assessment Creation with Bulk ControlResult Generation -- Partial Coverage
- **Category:** Data Integrity
- **File:** `backend/app/services/assessment_service.py` -- `create_assessment()` (line 216-290)
- **Description:** Creating an assessment auto-generates a ControlResult for every control in the framework (potentially 100+ records in a single flush). The duplicate check (campaign_id, equipement_id, framework_id) is covered by `test_phase1.py` happy path, but no test validates: bulk insert with large frameworks, error handling on partial failures, or the equipement status update to EN_COURS triggered at line 279.
- **Why critical:** Bulk insert failure could leave partial ControlResults without rollback.
- **Suggested test type:** Integration
- **Effort:** M
- **Suggested tests:**
  - `test_create_assessment_generates_control_results_for_all_controls`
  - `test_create_assessment_duplicate_rejected_409`
  - `test_create_assessment_updates_equipement_status`

#### GAP-009: Task Dispatch Ownership Triple-Check -- No Unit Tests
- **Category:** Security
- **File:** `backend/app/services/task_service.py` -- `dispatch_task()` (line 34-51)
- **Description:** `dispatch_task()` performs three security checks: audit ownership, agent ownership, and tool allowlist. While `test_agents_api.py` covers the API-level dispatch (6 tests), and `test_access_control_audit.py` covers RBAC, no test directly validates the `dispatch_task()` service function's triple ownership verification logic in isolation. The API tests mock or wrap the service.
- **Why critical:** Bypassing any of the three checks would allow cross-tenant task execution.
- **Covered by E2E?** Partially by `test_agents_api.py` (test_dispatch_other_user_audit_404, test_dispatch_other_user_agent_404, test_dispatch_tool_not_allowed_403).
- **Suggested test type:** Unit (service layer)
- **Effort:** S
- **Downgraded from CRITICAL:** API-level integration tests do cover the key scenarios.

---

### MEDIUM Severity (Priority 10-14)

#### GAP-010: Bulk Control Result Update -- No Tests
- **Category:** Data Integrity
- **File:** `backend/app/services/assessment_service.py` -- `bulk_update_results()` (line 352-375)
- **Description:** Bulk update loops through result updates, silently skipping missing result_ids (no error/warning). No test validates this function's behavior, particularly the silent skip of invalid IDs.
- **Why critical:** Silent data loss -- callers think all updates succeeded when some were silently dropped.
- **Suggested test type:** Unit
- **Effort:** S
- **Suggested tests:**
  - `test_bulk_update_applies_all_valid_results`
  - `test_bulk_update_skips_missing_result_ids_gracefully`

#### GAP-011: CORS Configuration -- No Tests
- **Category:** Security
- **File:** `backend/app/main.py` -- CORSMiddleware (line 137-144)
- **Description:** CORS is configured with restricted origins, credentials support, and method filtering. No test verifies that unauthorized origins are rejected or that the configuration is correctly applied.
- **Why critical:** CORS misconfiguration could allow cross-site attacks against authenticated sessions.
- **Covered by E2E?** No.
- **Suggested test type:** Integration
- **Effort:** S
- **Downgraded from HIGH:** FastAPI's CORSMiddleware is a well-tested library component; risk is in configuration, not implementation.

#### GAP-012: Agent Revocation -- Incomplete Cleanup Tests
- **Category:** Data Integrity
- **File:** `backend/app/services/agent_service.py` -- `revoke_agent()` (line 96-111)
- **Description:** Agent revocation sets status="revoked" but does not clean up in-flight tasks. The TODO at line 97 mentions a scheduled purge for agents revoked > 30 days, which is not implemented. `test_agents_api.py` tests the revoke API call but not the downstream effects on running tasks or the missing cleanup.
- **Why critical:** Revoked agents and their tasks accumulate forever; running tasks continue executing after revocation.
- **Suggested test type:** Integration
- **Effort:** M
- **Suggested tests:**
  - `test_revoke_agent_cancels_running_tasks`
  - `test_heartbeat_revoked_agent_rejected` (exists in test_agents_api.py)

---

## Coverage Summary by Category

| Category | Critical Paths | Tested | Untested | Coverage |
|----------|---------------|--------|----------|----------|
| **Security Flows** | 43 | 36 | 7 | 84% |
| **Data Integrity** | 11 | 4 | 7 | 36% |
| **Core Journeys** | 3 | 1 (partial) | 2 | 33% |
| **Money Flows** | 0 | N/A | N/A | N/A |

### Well-Covered Areas (no gaps found)
- Password hashing & verification (bcrypt) -- `test_auth_security_critical.py`
- JWT token lifecycle (access/refresh/agent) -- `test_auth_security_critical.py`, `test_auth_refresh.py`
- Enrollment tokens (SHA-256, timing-safe compare, expiration) -- `test_auth_security_critical.py`
- Rate limiting (brute-force protection) -- `test_auth_security_critical.py`
- Certificate management (CA generation, agent cert signing) -- `test_cert_manager.py`
- RBAC enforcement (admin/auditeur/lecteur isolation) -- `test_access_control_audit.py`, `test_rbac_*.py` (4 files)
- Agent enrollment flow -- `test_agents_api.py`
- WebSocket authentication & task isolation -- `test_websocket.py`, `test_websocket_task_isolation.py`
- File encryption (AES-256-GCM, envelope encryption) -- `test_file_service.py`, `test_encrypted_json.py`, `test_file_encryption.py`
- KEK rotation -- `test_rotate_kek.py`
- Compliance scoring -- `test_assessment_scoring.py`
- Audit access control logging -- `test_access_denied_logging.py`
- Password complexity validation -- `test_password_validation.py`

---

## Scoring Breakdown

| Check | Score Impact | Details |
|-------|-------------|---------|
| money_flow_coverage | 0 (N/A) | No financial logic in codebase |
| security_flow_coverage | -1.5 | 3 CRITICAL security gaps (headers, config enforcement, scan execution) |
| data_integrity_coverage | -2.0 | 4 HIGH gaps (cascade delete, framework import, bulk ops) |
| core_journey_coverage | -1.0 | Campaign state machine untested, scan-to-equipment journey untested |

**Base: 10.0 - 4.5 penalties = 5.5/10**

---

## Priority Remediation Order

1. **GAP-002** (SecurityHeadersMiddleware) -- Effort: S, Impact: CRITICAL -- quick win
2. **GAP-003** (Production Config Enforcement) -- Effort: S, Impact: CRITICAL -- quick win
3. **GAP-001** (Campaign State Machine) -- Effort: M, Impact: CRITICAL -- core business logic
4. **GAP-005** (Cascade Delete) -- Effort: M, Impact: HIGH -- data integrity
5. **GAP-006** (Framework Import) -- Effort: M, Impact: HIGH -- data integrity
6. **GAP-004** (Scan Background Execution) -- Effort: L, Impact: CRITICAL -- complex but important
7. **GAP-007 to GAP-012** -- remaining HIGH/MEDIUM items
