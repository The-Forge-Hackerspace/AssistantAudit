# AssistantAudit — Test Coverage & Quality Baseline Audit
**QA Lead:** Hockney  
**Audit Date:** 2026-03-19  
**Project:** AssistantAudit v2 (IT Security Audit Platform)

---

## Test Infrastructure

**Backend (Python/FastAPI):**
- **Test Framework:** pytest 8.0.0 + pytest-asyncio + pytest-cov + pytest-mock
- **Location:** ackend/tests/ (17 test files, ~3,100 lines of test code)
- **Configuration:** conftest.py with fixtures, factories.py for test data
- **Database:** SQLite in-memory (per-test isolation via function-scoped fixtures)
- **Test Runner:** Manual execution only (.venv\Scripts\python -m pytest tests/)
- **Mocking:** Uses @patch from unittest.mock, MagicMock for external dependencies

**Frontend (Next.js/React):**
- **Test Framework:** ⚠️ **NONE** — no Vitest, Jest, Playwright, or Cypress configured
- **Location:** ⚠️ **ZERO test files** found in rontend/src/
- **Test Scripts:** ⚠️ **NONE** in package.json
- **Dependencies:** ⚠️ **NO testing libraries** installed

**CI/CD:**
- **GitHub Actions:** 4 workflows (squad management only)
- **Test Automation:** ⚠️ **NONE** — no pytest or npm test runs in CI
- **Coverage Reports:** ⚠️ **NONE** — no coverage tracking configured

---

## Backend Test Coverage

**Total Tests:** 230 test functions across 17 files

**Coverage by Module:**

| Module | Tests | Lines | Quality | Status |
|--------|-------|-------|---------|--------|
| core/health_check | 21 | 205 | ✅ Excellent | Database connectivity, readiness, liveness endpoints |
| core/logging | 25 | 311 | ✅ Excellent | JSON structured logging, audit trail, middleware |
| core/metrics | 25 | 318 | ✅ Very Good | Prometheus metrics, HTTP/DB/error tracking |
| core/sentry_integration | 23 | 294 | ✅ Very Good | Exception capture, breadcrumbs, transactions |
| api/auth | 3 | 104 | ⚠️ Partial | Login success/failure, token generation |
| api/entreprises | 2 | 104 | ⚠️ Minimal | Create and list only |
| assessment/scoring | 16 | 262 | ✅ Excellent | Compliance scoring with edge cases (100+ controls) |
| performance | 9 | 249 | ✅ Good | N+1 query optimization (but no query counting) |
| monkey365/api | 21 | 525 | ✅ Very Good | API validation, auth modes, role-based access |
| monkey365/auth_modes | 23 | 375 | ✅ Excellent | 4 auth modes, credential validation |
| monkey365/executor | 17 | 342 | ✅ Good | Config generation, validation |
| monkey365/interactive | 7 | 165 | ✅ Good | PowerShell script generation fix |
| monkey365/module_loading | 7 | 163 | ✅ Good | Module availability, git clone, verification |
| monkey365/powershell | 5 | 161 | ✅ Good | Output capture, JSON formatting |
| monkey365/storage | 17 | 158 | ✅ Very Good | Slugify, path generation, metadata |
| monkey365/timezone | 7 | 96 | ✅ Good | Timezone-aware datetime calculations |
| phase1 & phase2 | 2 | 300 | ⚠️ Manual | End-to-end integration tests (require running server) |

**Estimated Coverage:**
- Infrastructure/Core: **85%** ✅
- Business Logic: **25%** ⚠️ (only assessment scoring)
- API Endpoints: **10%** ❌ (8 tests for 45+ routes)
- Services: **5%** ❌ (mostly untested)
- Models: **60%** ✅ (via factory usage)
- Database: **70%** ✅ (fixture setup good)

---

## Frontend Test Coverage

**Total Tests:** ⚠️ **ZERO**

**Frontend Inventory:**
- 61 TypeScript/TSX files in src/
- 18 page routes (Next.js App Router)
- 25+ UI components (shadcn/ui + custom)
- 21.4 KB API client (services/api.ts)
- 8 tool integration pages (AD Auditor, Monkey365, Scanner, SSL Checker, etc.)

**Critical Untested Features:**
1. **Auth Flows:** Login, logout, token refresh, JWT expiry handling
2. **Forms:** Validation (zod + react-hook-form), submission, error states
3. **API Integration:** Axios client, SWR caching, error handling, 401 redirects
4. **Components:** AuthGuard, AppLayout, ThemeToggle, PingCastleTerminal
5. **Tools:** 8 audit tool pages with form inputs and result displays
6. **Navigation:** Protected routes, role-based access

**Test Infrastructure Needed:**
- Vitest + @testing-library/react (unit/component tests)
- Playwright or Cypress (E2E tests)
- MSW (API mocking for integration tests)
- c8 or nyc (coverage reporting)

---

## Test Quality Assessment

**Test Naming:** ✅ **Mostly Excellent**
- Good: 	est_compliance_score_all_compliant, 	est_ready_endpoint_returns_503_when_db_disconnected
- Generic: 	est_metrics_collector_record_http_request (what's verified?)
- Excellent use of snake_case with clear input/output descriptions

**Test Clarity:** ✅ **Good**
- Tests are well-organized into classes
- Clear arrange-act-assert structure
- Good use of factories for test data

**Determinism:** ⚠️ **Mostly Good with Issues**
- ✅ Function-scoped database fixtures (clean state per test)
- ⚠️ test_api.py uses module-scope fixture (flaky risk: state pollution)
- ⚠️ Datetime tests without frozen time (flaky potential at second boundaries)
- ✅ No filesystem dependencies (uses in-memory DB)

**Flakiness Patterns Detected:**
1. **Module-scoped database** (test_api.py) → tests share state
2. **No frozen time** (test_monkey365_timezone.py) → timing-dependent assertions
3. **Global state** (LogContext, metrics collector) → would fail with parallel execution

---

## Coverage by Domain

### **Authentication & Security: 20%** ⚠️

**What's Tested:**
- ✅ Login success/failure (3 tests)
- ✅ JWT token generation (via fixtures)

**Critical Gaps:**
- ❌ Password hashing/verification (hash_password() used but not tested)
- ❌ JWT token expiration & refresh
- ❌ Rate limiting (ate_limit.py exists but untested)
- ❌ CORS validation
- ❌ Input sanitization (XSS, SQL injection prevention)
- ❌ Role-based access control (admin/auditeur/lecteur across all endpoints)

### **Audit & Assessment Logic: 60%** ✅

**What's Tested:**
- ✅ Compliance score calculation (16 tests with edge cases)
- ✅ Campaign aggregation scoring
- ✅ N+1 query optimization (9 tests)

**Gaps:**
- ❌ Assessment service methods (list_campaigns(), get_campaign_score())
- ❌ Control result creation and updates
- ❌ Framework loading and control filtering
- ❌ Audit lifecycle (status transitions)

### **Framework Sync: 15%** ⚠️

**What's Tested:**
- ⚠️ Implicit testing via integration tests

**Critical Gaps:**
- ❌ SHA-256 hash validation
- ❌ Missing framework file detection
- ❌ YAML parsing errors
- ❌ Network failures during sync
- ❌ Hash mismatch handling

### **API Endpoints: 10%** ❌

**What's Tested:**
- ✅ Health check (1 test)
- ✅ Auth login (2 tests)
- ✅ Entreprise CRUD (2 tests)
- ✅ Monkey365 API (21 tests)

**Critical Gaps (37 untested endpoints):**
- ❌ /api/v1/assessments/* (CRUD, scoring, results)
- ❌ /api/v1/audits/* (CRUD, status updates)
- ❌ /api/v1/sites/* (CRUD, equipment association)
- ❌ /api/v1/equipements/* (CRUD, type-specific fields)
- ❌ /api/v1/frameworks/* (listing, category/control retrieval)
- ❌ /api/v1/attachments/* (file upload/download)
- ❌ /api/v1/network_map/* (network visualization)
- ❌ /api/v1/tools/* (AD Auditor, PingCastle, Scanner, SSL Checker, etc.)
- ❌ Pagination, filtering, sorting across all endpoints
- ❌ Error responses (400/422/500) for all endpoints

### **UI Components: 0%** ❌

**All untested:**
- ❌ Auth flows (login, logout, token refresh)
- ❌ Forms (validation, submission, error handling)
- ❌ API integration (data fetching, SWR caching)
- ❌ Navigation (protected routes, redirects)
- ❌ Tool pages (8 audit tool integrations)

---

## Mock & Fixture Strategy

**Fixtures (conftest.py):** ✅ **Excellent**
- Function-scoped database (SQLite in-memory)
- FastAPI TestClient with dependency overrides
- Pre-created users (admin, auditeur, lecteur)
- JWT token headers for each role
- Automatic cleanup after each test

**Factories (factories.py):** ✅ **Comprehensive**
- 10+ entity factories (User, Entreprise, Site, Equipement, Framework, etc.)
- Batch creation helpers (create_batch())
- Realistic defaults (UUIDs for uniqueness, French locale data)
- Complex scenario builder (create_full_assessment_scenario())

**Mocking Strategy:** ✅ **Good for Unit Tests**
- Health/Sentry: Uses @patch to mock sentry_sdk, SessionLocal
- Monkey365: Mocks subprocess execution
- Database connectivity: Mocks DB exceptions

**Gaps in Mocking:**
- ❌ No mocking of external APIs (Microsoft 365, PingCastle, AD)
- ❌ Database queries never counted (no SQLAlchemy query introspection)
- ❌ Real database used for most tests (in-memory, but not fully isolated)
- ❌ No HTTP mocking library (e.g., httpx.Mock, responses) for external API calls

---

## CI/CD Integration

**Current State:** ❌ **No Test Automation**

**GitHub Actions Workflows:**
1. squad-heartbeat.yml — Team work monitoring (Ralph)
2. squad-issue-assign.yml — Issue auto-assignment
3. squad-triage.yml — Issue triage automation
4. sync-squad-labels.yml — Label synchronization

**What's Missing:**
- ❌ No pytest runs on push/PR
- ❌ No frontend test runs
- ❌ No coverage reporting
- ❌ No test gates (PRs can merge without tests)
- ❌ No test failure notifications

**Recommended CI/CD Pipeline:**
`yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/ --cov --cov-report=xml
      - uses: codecov/codecov-action@v4
  
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - run: npm ci
      - run: npm test
      - run: npm run test:e2e
`

---

## Critical Test Gaps

**Top 10 Missing Tests (Prioritized by Risk):**

1. **API Endpoint Tests** (37 untested routes)
   - Risk: Breaking changes ship to production undetected
   - Impact: HIGH — critical business operations (audits, assessments)
   - Estimated Tests: 100+ (5 per endpoint: success, 401, 403, 422, 404)

2. **Frontend Auth Flow** (0 tests)
   - Risk: Users can't log in, sessions expire without refresh
   - Impact: HIGH — blocks all user access
   - Estimated Tests: 15 (login, logout, token refresh, protected routes)

3. **Security Validation** (minimal tests)
   - Risk: SQL injection, XSS, unauthorized access
   - Impact: CRITICAL — data breach, compliance violations
   - Estimated Tests: 30 (input sanitization, rate limiting, JWT expiry)

4. **Framework Sync** (0 dedicated tests)
   - Risk: Hash mismatches, missing files, YAML parsing failures
   - Impact: HIGH — audits use wrong framework versions
   - Estimated Tests: 10 (hash validation, network errors, file missing)

5. **Service Layer Business Logic** (5% coverage)
   - Risk: Bugs in core business operations
   - Impact: HIGH — incorrect audit results, scoring errors
   - Estimated Tests: 50 (AssessmentService, AuthService, FrameworkService)

6. **Database Constraints** (0 explicit tests)
   - Risk: Foreign key violations, orphaned records, cascades fail
   - Impact: MEDIUM — data integrity issues
   - Estimated Tests: 20 (FK enforcement, cascades, unique constraints)

7. **External Tool Integration** (mocked, not verified)
   - Risk: Tools fail silently, data parsing breaks
   - Impact: MEDIUM — audit results incorrect or missing
   - Estimated Tests: 30 (PingCastle, AD Auditor, SSH/WinRM, Nmap)

8. **Frontend Forms** (0 tests)
   - Risk: Validation bypassed, submissions fail silently
   - Impact: MEDIUM — user frustration, data loss
   - Estimated Tests: 25 (validation, submission, error states)

9. **Error Handling** (0 tests)
   - Risk: Unhelpful error messages, stack traces in production
   - Impact: MEDIUM — poor UX, information leakage
   - Estimated Tests: 15 (exception handlers, 4xx/5xx responses)

10. **File I/O & Uploads** (0 tests)
    - Risk: Path traversal, file type validation bypassed
    - Impact: MEDIUM-HIGH — security vulnerability
    - Estimated Tests: 10 (upload validation, path traversal, cleanup)

---

## Edge Cases Coverage

**Well-Covered Edge Cases:** ✅
- Compliance scoring with 100+ controls (very large assessments)
- Mixed compliance statuses (compliant + partial + non-compliant)
- Empty result sets (0 controls assessed → None score)
- Timezone-aware vs naive datetime calculations
- Negative duration clamping (completed_at < created_at)
- French accents in slugify (é → e, à → a)
- Unicode and special characters in storage paths

**Missing Edge Cases:** ❌
- **Boundary Values:** Max int (2^31), empty strings, NULL/None handling
- **Concurrency:** Multiple users editing same entity, race conditions
- **Network Failures:** Timeouts, partial responses, retry logic
- **Large Datasets:** 10,000+ entities, pagination performance
- **Invalid File Types:** .exe uploaded as evidence, 0-byte files
- **Token Edge Cases:** Token refresh during concurrent requests
- **Database Limits:** SQLite 2GB limit, connection pool exhaustion

**Error Path Coverage:** ⚠️ **Partial**
- ✅ Database connection failures (health check tests)
- ✅ Monkey365 config validation errors (23 tests)
- ⚠️ API validation errors (only for Monkey365 endpoint)
- ❌ Service layer exceptions (untested)
- ❌ External tool failures (mocked away)
- ❌ File upload errors (untested)

**Concurrency Testing:** ❌ **None**
- No tests for concurrent API requests
- No race condition testing
- No database deadlock testing
- Tests would fail with parallel execution (pytest -n auto)

---

## Testability Issues

**Good Testability:** ✅
- Dependency injection (FastAPI's dependency override system)
- Clean separation: models, schemas, services, API routes
- Database fixtures with per-test isolation
- Factory pattern for complex test data

**Design Improvements Needed:** ⚠️

1. **Global State in Core Modules**
   - core/logging.py uses global LogContext → breaks parallel tests
   - core/metrics.py uses global collectors → same issue
   - **Fix:** Use dependency injection for context/collectors

2. **Hard-Coded Time Dependencies**
   - datetime.now() without frozen time → flaky tests
   - **Fix:** Use pytest-freezegun or inject time provider

3. **No Query Counting**
   - Performance tests verify data correctness but not query count
   - **Fix:** Add SQLAlchemy event listener for query counting

4. **Tightly Coupled Tool Execution**
   - Tools execute via subprocess with no abstraction
   - **Fix:** Create tool adapter interfaces for easier mocking

5. **No Interface Segregation**
   - Services are concrete classes, not interfaces
   - **Fix:** Use protocols (PEP 544) or abstract base classes

---

## Test Maintenance & Debt

**Flaky Tests:** ⚠️ **2 Patterns Detected**
1. **test_api.py module scope** — tests share database state
   - Fix: Change @pytest.fixture(scope="module") to scope="function"
2. **Datetime tests without frozen time** — timing-dependent
   - Fix: Use pytest-freezegun

**Outdated Tests:** ✅ **None Found**
- All tests appear current with codebase

**Cleanup Needs:** ⚠️ **Minor**
- Remove commented-out code in test_api.py
- Consolidate duplicate test setup in Monkey365 tests
- Extract common mock patterns to conftest.py

**Tech Debt:** ⚠️ **Moderate**
- No coverage tracking (add pytest-cov to CI)
- No mutation testing (add mutmut)
- No property-based testing (add hypothesis for validators)
- Manual test runs (add to CI/CD)

**Documentation:** ⚠️ **Minimal**
- No 	ests/README.md explaining test structure
- No docs on running tests
- No guidance on writing new tests
- No test coverage reports

---

## Quality Baseline

**Current State:** AssistantAudit has **~40% test maturity** for a production-ready security audit platform. Backend infrastructure is well-tested (health, logging, metrics), but critical business logic (API endpoints, services), security validation, and all frontend code remain untested.

**Risk Assessment:** **HIGH** — The lack of API and frontend tests creates significant regression risk as features evolve. Security vulnerabilities (auth, validation) may go undetected until production.

---

## QA Recommendations

**Top 5 Immediate Quality Improvements:**

1. **Add API Endpoint Tests** (3-5 days)
   - Target: 100+ tests for 45+ REST endpoints
   - Focus: CRUD operations, role-based access, validation errors
   - Use existing fixtures/factories for test data

2. **Setup Frontend Test Infrastructure** (5-7 days)
   - Install: Vitest, @testing-library/react, Playwright
   - Add test scripts to package.json
   - Write 50+ tests for auth, forms, API integration

3. **Implement Security Tests** (2-3 days)
   - Test JWT token expiration & refresh
   - Test rate limiting
   - Test input validation/sanitization
   - Test password hashing

4. **Add CI/CD Test Automation** (1 day)
   - GitHub Actions workflow for pytest + npm test
   - Coverage reporting (pytest-cov, c8)
   - Block PRs with failing tests

5. **Fix Flaky Test Patterns** (1 day)
   - Change test_api.py to function-scoped fixtures
   - Add pytest-freezegun for datetime tests
   - Add query counting for performance tests

**Long-Term Goals:**
- Coverage target: 75%+ for critical paths (auth, sync, audits)
- Mutation testing with mutmut
- Property-based testing with hypothesis
- E2E tests for full user workflows
- Performance benchmarks with pytest-benchmark

---

**Report End**
