# Hockney — Session History

## Plugin Installations

- 📦 Plugin `frontend-web-dev` installed from `github/awesome-copilot` (2026-03-21) — skills: `playwright-explore-website`, `playwright-generate-test`
- 📦 Plugin `security-best-practices` installed from `github/awesome-copilot` (2026-03-21) — skill: `ai-prompt-engineering-safety-review`

## Project Knowledge

- 12 frameworks = 12 different audit scenarios to test
- Framework sync is critical: SHA-256 hash validation must never fail silently
- Auth must be rock-solid: token refresh, expiry, scope validation
- Audit results are high-stakes — findings need accuracy testing
- Infrastructure scope: Firewalls, Switches, AD, M365, servers

## Patterns

(To be filled as work progresses)

## Key Files

- Backend tests: `backend/tests/`
- Frontend tests: `frontend/__tests__/` or `frontend/tests/`
- Test fixtures: `backend/tests/fixtures/` or `frontend/__fixtures__/`
- Framework samples: `data/frameworks/` (test data)

## Learnings

### Test Infrastructure Audit (2026-03-19)

**Backend Test Coverage:**
- 230 tests across 17 files (~3,100 lines)
- Strong infrastructure coverage: Health (21), Logging (25), Metrics (25), Sentry (23)
- Good Monkey365 config testing: 79 tests across 8 files
- Strong assessment scoring logic: 16 tests with excellent edge cases
- **Critical gaps:** API endpoints (10% coverage), services (5% coverage), security (minimal)
- **Quality issues:** test_api.py uses module-scope fixture (flaky risk), no query counting

**Coverage by Domain:**
- Infrastructure/Core: 85% ✅
- Business Logic: 25% ⚠️ (only assessment scoring)
- API Endpoints: 10% ❌ (8 tests for 45+ routes)
- Services: 5% ❌ (only performance optimization tests)
- Models/Data: 60% ✅ (via factories)
- Database: 70% ✅ (fixture setup good)

**Frontend Test Coverage:**
- **ZERO tests** — no unit, component, integration, or e2e tests
- No test infrastructure (no Vitest, Jest, Playwright, Cypress)
- No test scripts in package.json
- 61 TypeScript files, 18 pages, 25+ components — all untested
- Critical gaps: Auth flows, forms/validation, API integration, UI components

**Test Quality Strengths:**
- Excellent fixture setup (conftest.py) with function-scoped isolation
- Comprehensive factory pattern (factories.py) for complex scenarios
- Good test naming (mostly descriptive: `test_compliance_score_all_compliant`)
- Proper mocking strategy for health/sentry (using @patch)
- Strong edge case coverage for scoring logic (100+ control tests)

**Test Quality Issues:**
- test_api.py uses module-scope DB → state pollution risk
- No query counting (can't verify N+1 optimization claims)
- Datetime tests without frozen time (flaky potential)
- Mocked external dependencies (won't catch integration failures)
- No parallel test execution support (global state: LogContext, metrics)

**CI/CD Integration:**
- **NO test automation** — GitHub Actions only has squad management workflows
- Tests must be run manually (no pytest in CI)
- No coverage reporting configured
- No test gates for PRs

**Critical Test Gaps (Top 10):**
1. API endpoint tests (45+ routes, 37 untested)
2. Frontend tests (0 tests for 61 TS files)
3. Service layer tests (10 services, mostly untested)
4. Security tests (JWT, rate limiting, validation)
5. Database constraint tests (foreign keys, cascades)
6. Error handling tests (exception handlers untested)
7. External tool integration (PingCastle, AD Auditor, SSH/WinRM)
8. Configuration tests (config.py, environment validation)
9. File I/O tests (uploads, path traversal prevention)
10. E2E tests (no user flow testing)

**Recommendations (Prioritized):**
1. Add 100+ API endpoint tests (CRITICAL)
2. Setup frontend test infrastructure + critical tests (CRITICAL)
3. Add security tests (JWT, rate limiting, validation) (HIGH)
4. Test service layer business logic (MEDIUM)
5. Add CI/CD test automation (MEDIUM)
6. Implement query counting for performance tests (LOW)
7. Add mutation testing with mutmut (LOW)

**Test Baseline Quality Score:** 40% of production quality
- Infrastructure: 90% ✅
- API: 15% ❌
- Business Logic: 20% ❌
- Security: 15% ❌
- Frontend: 0% ❌

**Estimated Work to Reach 75% Coverage:**
- Backend API tests: 3-5 days
- Frontend infrastructure + tests: 5-7 days
- Security tests: 2-3 days
- Service layer tests: 3-4 days
- **Total:** 13-19 days (2.5-4 weeks)

**Files Needing Test Coverage (Backend):**
- app/api/v1/*.py (37 untested endpoints)
- app/services/*.py (10 service files)
- app/core/security.py (password hashing, JWT)
- app/core/config.py (environment validation)
- app/schemas/*.py (50+ validators)
- app/tools/*.py (10+ tools)

**Files Needing Test Coverage (Frontend):**
- src/contexts/auth-context.tsx (auth state management)
- src/services/api.ts (HTTP client)
- src/hooks/use-api.ts (SWR hooks)
- src/app/login/page.tsx (auth flow)
- src/app/*/page.tsx (18 pages)
- src/components/*.tsx (25+ components)

**Test Patterns Discovered:**
- Factory pattern for complex test data (excellent)
- Function-scoped fixtures for isolation (good)
- @patch for external dependencies (good for unit tests)
- In-memory SQLite for speed (good)
- Realistic test data (good — uses actual domain values)
- Module-scope anti-pattern in test_api.py (bad)
- No frozen time for datetime tests (risky)

**Next Actions:**
1. Propose test infrastructure roadmap to team (decisions.md)
2. Pair with Fenster on API test strategy
3. Pair with Dallas on frontend test setup
4. Create test coverage tracking dashboard
5. Add pytest-cov to CI/CD pipeline

## M365 Audit Path Verification (2026-03-21)

**Context:** Fenster fixed redundant tenant ID directories in Monkey365 audit paths.

**Verification Approach:**
- Created comprehensive test suite (15 new tests) covering:
  - Path construction (no duplicate tenant IDs)
  - Backward compatibility (old data readable)
  - Edge cases (special chars, concurrency, empty IDs)
  - Data integrity (findings saved correctly)
  - Integration smoke tests (full lifecycle)

**Test Results:**
- 32 total tests (17 original + 15 new): **ALL PASSING ✅**
- Path structure clean: `data/company-slug/Cloud/M365/scan_id/` (no duplicates)
- Backward compatible: Old audit data still accessible
- No regressions detected

**Key Findings:**
- Fix eliminates redundant tenant_id in paths
- Metadata integrity verified across new structure
- 10 concurrent audits tested with no path conflicts
- Special character sanitization working correctly
- Unicode preservation (French accents) intact

**Coverage:**
- Path Construction: 4/4 tests ✅
- Backward Compatibility: 2/2 tests ✅
- Edge Cases: 4/4 tests ✅
- Data Integrity: 3/3 tests ✅
- Integration: 2/2 tests ✅

**Confidence:** HIGH - Production-ready, safe to deploy.

**Test Patterns Discovered:**
- Comprehensive mocking strategy for storage layer (patch get_settings)
- Excellent use of tmp_path fixture for isolated filesystem tests
- Edge case coverage: empty inputs, special chars, concurrent operations
- Integration testing validates full lifecycle (create → write → read)
