# Security Review Checklist - Monkey365 Executor

**Date**: 2024-12-19  
**Status**: ✅ **APPROVED** (with recommended improvements)

---

## Quick Summary

| Category | Status | Details |
|----------|--------|---------|
| **Subprocess Safety** | ✅ SECURE | All arguments passed as lists, no shell injection possible |
| **Input Validation** | ✅ SECURE | Comprehensive whitelist validation on all user inputs |
| **PowerShell Escaping** | ✅ SECURE | Proper single-quote escaping implemented |
| **Credential Handling** | ✅ SECURE | Conditional parameters based on auth mode |
| **Password Logging** | ✅ SECURE | Passwords never logged in plaintext |
| **Environment Variables** | ✅ SECURE | Safe copy-modify pattern, no credential leakage |
| **Temporary Files** | ⚠️ IMPROVE | Hardcoded path - should use tempfile module |
| **JSON Parsing** | ⚠️ IMPROVE | No file size limits - potential memory exhaustion |
| **Git Clone** | ℹ️ INFO | URL is hardcoded (secure, but validate if configurable) |

---

## Critical Security Controls ✅

### 1. Subprocess Injection Prevention
- [x] All `subprocess.run()` calls use argument lists (not strings)
- [x] `shell=True` is NEVER used
- [x] User input never concatenated into command strings
- [x] PowerShell `-Command` parameters properly escaped

### 2. Input Validation
- [x] UUIDs validated with regex: `^[0-9a-fA-F]{8}-...$`
- [x] Emails validated with regex: `^[a-zA-Z0-9._%+-]+@...$`
- [x] Secrets validated with whitelist: `^[a-zA-Z0-9_.~\-]{1,256}$`
- [x] Safe names validated: `^[a-zA-Z0-9_\-]+$`
- [x] Export formats whitelisted: `JSON, HTML, CSV, CLIXML`
- [x] Collect modules whitelisted: `ExchangeOnline, SharePointOnline, etc.`

### 3. PowerShell Injection Prevention
- [x] All user strings escaped with `_escape_ps_string()`
- [x] Single-quote escaping: `'` → `''`
- [x] Boolean values converted to `$true`/`$false` (not user strings)
- [x] Enum values validated before use

### 4. Credential Security
- [x] Passwords converted to `SecureString` in PowerShell
- [x] Passwords masked in logs: `_mask_password()`
- [x] Conditional credential passing (only for relevant auth modes)
- [x] No credentials logged in plaintext

### 5. Path Security
- [x] `output_path.rglob("*.json")` only traverses subdirectories (no path traversal)
- [x] `cwd` parameter isolates subprocess working directory
- [x] File writes are to controlled directories
- [ ] **TODO**: Use `tempfile` module for temporary script files

### 6. Error Handling
- [x] Subprocess timeout enforced (3600 seconds)
- [x] JSON parsing errors caught and handled
- [x] Unicode decode errors handled gracefully
- [x] File not found errors handled

---

## Required Fixes

### ⚠️ MEDIUM Priority - Fix Temporary File Handling

**Current Issue**:
```python
ps1_path = Path("D:/AssistantAudit/temp/monkey365_scan.ps1")  # Hardcoded, predictable
```

**Required Fix**:
```python
import tempfile
import stat

temp_dir = Path(tempfile.gettempdir()) / "assistantaudit_monkey365"
temp_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
ps1_path = temp_dir / f"scan_{scan_id}_{os.getpid()}.ps1"
ps1_path.write_text(script, encoding="utf-8")
os.chmod(ps1_path, stat.S_IRUSR | stat.S_IWUSR)  # Owner read/write only
```

**Why This Matters**:
- Prevents predictable file locations (security through obscurity)
- Prevents race conditions between concurrent scans
- Allows proper OS-level temporary directory management
- Enables file permission restrictions (owner-only access)

---

## Recommended Improvements

### 1. Add JSON File Size Limit (LOW Priority)

**Add to top of file**:
```python
MAX_JSON_SIZE = 100 * 1024 * 1024  # 100 MB
```

**In `_parse_output()` method**:
```python
for json_file in output_path.rglob("*.json"):
    if json_file.stat().st_size > MAX_JSON_SIZE:
        logger.warning(f"Skipping oversized file: {json_file.name}")
        continue
    # ... rest of parsing
```

### 2. Add Rate Limiting (OPTIONAL)

Prevent abuse by limiting scan frequency:
```python
class RateLimiter:
    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
    # ... implementation in SECURITY_FIXES_MONKEY365.py
```

### 3. Add Security Audit Logging (OPTIONAL)

Log security-relevant events:
```python
logger.info(
    f"[SECURITY AUDIT] Scan initiated: scan_id={scan_id}, "
    f"auth_mode={self.config.auth_mode}, user={os.getenv('USER')}"
)
```

---

## Testing Requirements

### Security Tests to Implement

1. **Injection Prevention**:
   ```python
   def test_powershell_injection_blocked():
       config = Monkey365Config(
           tenant_id="'; Invoke-Expression 'calc.exe'; #"
       )
       with pytest.raises(ValueError):
           config.validate()
   ```

2. **Path Traversal Prevention**:
   ```python
   def test_path_traversal_blocked():
       executor.run_scan("../../etc/passwd")
       # Should be contained within output_dir
   ```

3. **Credential Leakage Prevention**:
   ```python
   def test_no_password_in_logs(caplog):
       config = Monkey365Config(
           auth_mode="ropc",
           password="SuperSecret123"
       )
       executor.build_script(config)
       assert "SuperSecret123" not in caplog.text
   ```

4. **Race Condition Testing**:
   ```python
   def test_concurrent_scans():
       with ThreadPoolExecutor(max_workers=5) as executor:
           futures = [executor.submit(run_scan, f"scan_{i}") for i in range(10)]
       # Verify no file collisions
   ```

---

## Validation Commands

Run these commands to verify security controls:

```bash
# 1. Check for subprocess shell=True usage (should return NOTHING)
grep -r "shell=True" backend/app/tools/monkey365_runner/

# 2. Check for hardcoded credentials (should return NOTHING)
grep -rE "(password|secret|token)\s*=\s*['\"][^'\"]+['\"]" backend/app/tools/monkey365_runner/ --include="*.py"

# 3. Check for SQL injection patterns (should return NOTHING for this module)
grep -r "execute.*%s" backend/app/tools/monkey365_runner/

# 4. Run security-focused tests
pytest backend/tests/test_monkey365_auth_modes.py -v
pytest backend/tests/test_monkey365_executor.py -v --tb=short

# 5. Check for TODO security items
grep -r "TODO.*SECURITY" backend/app/tools/monkey365_runner/
```

---

## Acceptance Criteria

Before marking this as COMPLETE, ensure:

- [x] All subprocess calls use list arguments
- [x] All user inputs are validated
- [x] All PowerShell strings are escaped
- [x] Passwords are never logged
- [ ] **PENDING**: Temporary files use `tempfile` module
- [ ] **PENDING**: JSON file size limits implemented
- [ ] Security tests pass
- [ ] No hardcoded credentials in code
- [ ] Code review completed

---

## Sign-Off

**Security Reviewer**: ✅ APPROVED (with recommendations)  
**Recommendation**: Implement temporary file fix (MEDIUM priority) before production deployment.

**Risk Level**: LOW (after temporary file fix applied)  
**Estimated Fix Time**: 30 minutes  
**Deployment Impact**: None (backwards compatible)

---

## References

- Full Security Report: `SECURITY_REVIEW_MONKEY365.md`
- Code Fixes: `SECURITY_FIXES_MONKEY365.py`
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- PowerShell Security: https://docs.microsoft.com/en-us/powershell/scripting/learn/security-overview
