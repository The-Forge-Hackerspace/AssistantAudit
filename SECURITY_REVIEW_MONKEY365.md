# Security Review: Monkey365 Subprocess Executor
**Date**: 2024-12-19  
**Reviewer**: Security Specialist  
**Scope**: `backend/app/tools/monkey365_runner/executor.py`  
**Focus**: Subprocess injection, environment handling, path traversal, credential exposure

---

## Executive Summary

**Overall Status**: ✅ **SECURE** (with minor recommendations)

The Monkey365 executor demonstrates **strong security practices** with comprehensive input validation, proper PowerShell escaping, and secure subprocess handling. The code has been designed with security as a priority, implementing multiple defense layers against injection attacks.

### Key Strengths
- ✅ Comprehensive input validation with whitelisting
- ✅ Proper PowerShell string escaping
- ✅ Subprocess arguments passed as list (not shell=True)
- ✅ Conditional credential handling based on auth mode
- ✅ Password masking in logs
- ✅ Secure environment variable handling

### Issues Found
- ⚠️ **MEDIUM**: Hardcoded temporary file path (line 490)
- ⚠️ **LOW**: Git clone URL not validated
- ⚠️ **LOW**: Lack of file size limits in JSON parsing
- 💡 **INFO**: Consider additional rate limiting for scans

---

## Detailed Analysis

### 1. ✅ SECURE: Subprocess Argument Handling

#### `ensure_monkey365_ready()` - Lines 266-277
```python
clone_result = subprocess.run(
    [
        "git",
        "clone",
        "--depth=1",
        "https://github.com/silverhack/monkey365.git",
        str(monkey365_dir),
    ],
    capture_output=True,
    text=True,
    cwd=monkey365_dir.parent,
)
```

**Status**: ✅ **SECURE**
- Arguments passed as list, not string (prevents shell injection)
- No user-controlled input in git clone command
- Hard-coded GitHub URL (not injectable)
- Path is controlled by application (Path object converted to string)
- `cwd` parameter safely isolates working directory

**Minor Risk**: If `monkey365_dir` could be manipulated by an attacker to point to a sensitive location, files could be overwritten. However, `monkey365_dir` is derived from `DEFAULT_MONKEY365_DIR` or `self.monkey365_path.parent`, both controlled by the application configuration.

**Recommendation**: None required. This is secure.

---

#### `ensure_monkey365_ready()` - Lines 300-305
```python
result = subprocess.run(
    ["powershell.exe", "-Command", test_ps],
    capture_output=True,
    text=True,
    cwd=monkey365_dir,
)
```

**Status**: ✅ **SECURE**
- PowerShell path is not user-controlled (`powershell.exe`)
- `-Command` parameter is fixed
- `test_ps` uses escaped string: `safe_dir = _escape_ps_string(str(monkey365_dir))`
- Escaping function properly handles PowerShell single-quote escaping (line 64: `return value.replace("'", "''")`

**Validation of Escaping**:
```python
def _escape_ps_string(value: str) -> str:
    """
    Échappe une valeur pour insertion sûre dans une string PowerShell
    entourée de guillemets simples.
    En PowerShell, le seul échappement dans une single-quoted string est
    de doubler les apostrophes : ' → ''
    """
    return value.replace("'", "''")
```

This is **correct PowerShell escaping**. Single-quoted strings in PowerShell do not interpret special characters except for `'`, which must be doubled.

**Recommendation**: None required. This is secure.

---

#### `run_scan()` - Lines 500-514
```python
result = subprocess.run(
    [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ps1_path),
    ],
    capture_output=True,
    text=True,
    timeout=3600,
    cwd=self.monkey365_path.parent,
    env=env,
)
```

**Status**: ✅ **SECURE**
- Arguments passed as list (no shell injection)
- `-NoProfile` prevents loading of user profiles (security hardening)
- `-ExecutionPolicy Bypass` is necessary for script execution (acceptable in this context)
- `-File` parameter ensures the script is executed as a file, not as arbitrary code
- `ps1_path` is controlled by application (line 490)
- `timeout=3600` prevents indefinite hangs
- `capture_output=True` safely captures stdout/stderr
- `env` is a copy of `os.environ` with minimal modification

**Issue**: ⚠️ **MEDIUM** - Hardcoded temporary path (see Section 3)

**Recommendation**: See Section 3 for path security recommendations.

---

### 2. ✅ SECURE: PowerShell Script Generation (`build_script()`)

#### Input Validation - Lines 368-384
```python
# Validate configuration (includes auth-mode-specific credential checks)
active_config.validate()

# Valider les noms d'analyses et rulesets
for analysis in self._get_analyses(active_config):
    _ = _validate_safe_name(analysis, "analysis")

if active_config.rulesets:
    for ruleset in active_config.rulesets:
        _ = _validate_safe_name(ruleset, "ruleset")
```

**Status**: ✅ **SECURE**
- All user inputs are validated before script generation
- `_validate_safe_name()` enforces strict whitelist: `^[a-zA-Z0-9_\-]+$`
- Configuration validation checks auth-mode-specific requirements

**Validation Functions Reviewed**:
```python
_UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_SECRET_PATTERN = re.compile(r"^[a-zA-Z0-9_.~\-]{1,256}$")
_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
_SAFE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")
_SCAN_SITE_PATTERN = re.compile(r"^https://[a-zA-Z0-9._/-]+$")

_ALLOWED_COLLECT_MODULES = {
    "ExchangeOnline", "SharePointOnline", "Purview", "MicrosoftTeams", "AdminPortal"
}
_ALLOWED_EXPORT_FORMATS = {"JSON", "HTML", "CSV", "CLIXML"}
```

These are **comprehensive and secure** validation patterns that prevent injection attacks.

---

#### PowerShell Parameter Construction - Lines 386-426
```python
safe_monkey365_dir = _escape_ps_string(str(self.monkey365_path.parent))
provider_value = str(active_config.provider)
if isinstance(active_config.provider, M365Provider):
    provider_value = active_config.provider.value
safe_provider = _escape_ps_string(provider_value)
safe_output = _escape_ps_string(str(output_path))
export_to = ", ".join(f"'{_escape_ps_string(fmt)}'" for fmt in active_config.export_to)
include_entra_id = "$true" if active_config.include_entra_id else "$false"
```

**Status**: ✅ **SECURE**
- Every user-controlled parameter is escaped using `_escape_ps_string()`
- Boolean values are converted to PowerShell booleans (`$true`/`$false`), not user strings
- Provider values come from enum (validated)
- Export formats are validated against whitelist before use

---

#### Conditional Credential Handling - Lines 428-468

**CRITICAL SECURITY FEATURE**: The code implements **conditional parameter passing** based on authentication mode. This is a **best practice** that prevents credential leakage.

**INTERACTIVE Mode** (Lines 429-433):
```python
if auth_mode_value == Monkey365AuthMode.INTERACTIVE.value:
    script += """    PromptBehavior = 'SelectAccount';
"""
```
- ✅ **No credentials in script**
- ✅ Only prompts for interactive login

**DEVICE_CODE Mode** (Lines 435-439):
```python
elif auth_mode_value == Monkey365AuthMode.DEVICE_CODE.value:
    script += """    DeviceCode     = $true;
"""
```
- ✅ **No credentials in script**
- ✅ Uses device code flow (secure for headless)

**ROPC Mode** (Lines 441-453):
```python
elif auth_mode_value == Monkey365AuthMode.ROPC.value:
    safe_tenant = _escape_ps_string(active_config.tenant_id)
    safe_username = _escape_ps_string(active_config.username)
    safe_password = _escape_ps_string(active_config.password)
    script += f"""    TenantId       = '{safe_tenant}';
    Username       = '{safe_username}';
    Password       = (ConvertTo-SecureString '{safe_password}' -AsPlainText -Force);
"""
```
- ✅ All credentials escaped before insertion
- ✅ Password converted to `SecureString` in PowerShell
- ✅ Tenant ID validated as UUID
- ✅ Username validated as email format

**CLIENT_CREDENTIALS Mode** (Lines 455-467):
```python
elif auth_mode_value == Monkey365AuthMode.CLIENT_CREDENTIALS.value:
    safe_tenant = _escape_ps_string(active_config.tenant_id)
    safe_client_id = _escape_ps_string(active_config.client_id)
    safe_secret = _escape_ps_string(active_config.client_secret)
    script += f"""    TenantId       = '{safe_tenant}';
    ClientId       = '{safe_client_id}';
    ClientSecret   = (ConvertTo-SecureString '{safe_secret}' -AsPlainText -Force);
"""
```
- ✅ All credentials escaped before insertion
- ✅ Secret converted to `SecureString`
- ✅ Tenant ID and Client ID validated as UUIDs
- ✅ Client Secret validated against safe character set

**Status**: ✅ **SECURE** - This is **exemplary security design**.

---

### 3. ⚠️ MEDIUM: Hardcoded Temporary File Path

**Location**: `run_scan()` - Line 490
```python
ps1_path = Path("D:/AssistantAudit/temp/monkey365_scan.ps1")
```

**Issues**:
1. **Hardcoded absolute path**: Not portable across systems
2. **Predictable location**: Attacker could guess the file location
3. **Race condition potential**: Multiple scans could overwrite each other
4. **No path validation**: If `scan_id` is user-controlled, it could be manipulated

**Risk Level**: ⚠️ **MEDIUM**
- Risk is mitigated by the fact that the file is deleted after execution (line 557-558)
- However, a race condition could allow an attacker to read credentials during the brief window the file exists

**Recommendations**:
1. **Use `tempfile.NamedTemporaryFile()` or `tempfile.mkstemp()`** to generate secure temporary files
2. **Include scan_id in filename** to prevent race conditions between concurrent scans
3. **Set restrictive permissions** on the temporary file (owner read/write only)

**Suggested Fix**:
```python
import tempfile
import os
import stat

def run_scan(self, scan_id: str) -> dict[str, object]:
    """Lance le scan Monkey365 (synchrone)"""
    self.ensure_monkey365_ready()
    self._active_scan_id = scan_id

    script = self.build_script(scan_id)
    
    # Use secure temporary file with restricted permissions
    temp_dir = Path(tempfile.gettempdir()) / "assistantaudit_monkey365"
    temp_dir.mkdir(parents=True, exist_ok=True, mode=0o700)  # Owner only
    
    ps1_path = temp_dir / f"scan_{scan_id}_{os.getpid()}.ps1"
    ps1_path.write_text(script, encoding="utf-8")
    
    # Set file permissions to owner read/write only (Windows & Unix)
    try:
        os.chmod(ps1_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass  # Windows may not support POSIX permissions
    
    # ... rest of function
```

---

### 4. ✅ SECURE: Environment Variable Handling

**Location**: `run_scan()` - Lines 496-497
```python
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"
```

**Status**: ✅ **SECURE**
- Environment is copied, not modified in place (prevents global pollution)
- Only one benign variable added (`PYTHONIOENCODING`)
- No user-controlled environment variables
- No credential leakage through environment

**Recommendation**: None required. This is secure.

---

### 5. ✅ SECURE: Output Capture and File Handling

#### Output Capture - Lines 509-526
```python
result = subprocess.run(
    [...],
    capture_output=True,
    text=True,
    timeout=3600,
    [...]
)

raw_output = {
    "stdout": result.stdout,
    "stderr": result.stderr,
    "returncode": result.returncode,
    "duration_seconds": time.time() - start_time,
}

(output_path / "powershell_raw_output.json").write_text(
    json.dumps(raw_output, indent=2),
    encoding="utf-8",
)
```

**Status**: ✅ **SECURE**
- `capture_output=True` safely captures output
- `text=True` ensures proper text handling
- `timeout=3600` prevents indefinite execution
- Output is written to controlled directory

**Potential Issue**: ⚠️ **LOW** - If PowerShell output contains sensitive data (credentials logged by Monkey365), it will be written to disk unencrypted.

**Recommendation**: Consider sanitizing `stdout`/`stderr` before writing to disk to remove potential credentials.

---

#### JSON Parsing - Lines 565-576
```python
for json_file in output_path.rglob("*.json"):
    try:
        data: object = cast(object, json.loads(json_file.read_text(encoding="utf-8")))
        if isinstance(data, list):
            for item in cast(list[object], data):
                if isinstance(item, dict):
                    results.append(cast(dict[str, object], item))
        elif isinstance(data, dict):
            results.append(cast(dict[str, object], data))
    except (json.JSONDecodeError, UnicodeDecodeError):
        continue
```

**Status**: ✅ **MOSTLY SECURE**
- `rglob("*.json")` is safe (no path traversal - only traverses subdirectories of `output_path`)
- JSON parsing errors are caught and ignored (fail-safe behavior)
- No arbitrary code execution risk

**Minor Issue**: ⚠️ **LOW** - No file size limit check
- A malicious or corrupted Monkey365 output could create a massive JSON file
- Reading it with `.read_text()` could cause memory exhaustion

**Recommendation**:
```python
MAX_JSON_SIZE = 100 * 1024 * 1024  # 100 MB

for json_file in output_path.rglob("*.json"):
    try:
        if json_file.stat().st_size > MAX_JSON_SIZE:
            logger.warning(f"Skipping large file: {json_file.name} ({json_file.stat().st_size} bytes)")
            continue
        data: object = cast(object, json.loads(json_file.read_text(encoding="utf-8")))
        [...]
```

---

### 6. ✅ SECURE: Credential Validation

**UUID Validation** (Lines 67-73):
```python
def _validate_uuid(value: str, field_name: str) -> str:
    if not _UUID_PATTERN.match(value):
        raise ValueError(
            f"{field_name} invalide : format UUID attendu"
        )
    return value
```
- ✅ Strict UUID format enforcement
- ✅ Prevents injection via tenant_id/client_id

**Secret Validation** (Lines 76-83):
```python
def _validate_secret(value: str) -> str:
    if not _SECRET_PATTERN.match(value):
        raise ValueError(
            "Client secret contient des caractères non autorisés"
        )
    return value
```
- ✅ Whitelist approach: only `[a-zA-Z0-9_.~\-]{1,256}`
- ✅ Length limit (256 characters) prevents buffer overflow attempts
- ✅ Prevents PowerShell metacharacters

**Email Validation** (Lines 86-92):
```python
def _validate_email(value: str, field_name: str) -> str:
    if not _EMAIL_PATTERN.match(value):
        raise ValueError(f"{field_name} invalide : format email attendu")
    return value
```
- ✅ Standard email format validation
- ✅ Prevents injection via username field

**Status**: ✅ **SECURE** - Comprehensive validation.

---

### 7. ✅ SECURE: Password Masking

**Location**: Lines 105-107
```python
def _mask_password(password: str) -> str:
    """Masque un mot de passe pour les logs (NEVER log plaintext passwords)."""
    return "***" if password else ""
```

**Usage**: Lines 450-452, 465-466
```python
logger.info(
    f"Building ROPC auth script (tenant={active_config.tenant_id}, "
    f"username={active_config.username})"
)
# Password is NOT logged

logger.info(
    f"Building CLIENT_CREDENTIALS auth script (tenant={active_config.tenant_id}, "
    f"client_id={active_config.client_id}, secret={_mask_password(active_config.client_secret)})"
)
```

**Status**: ✅ **SECURE**
- Passwords are **never logged in plaintext**
- Secrets are masked before logging
- Good security hygiene

**Recommendation**: None required. This is best practice.

---

### 8. ⚠️ LOW: Git Clone URL Not Validated

**Location**: Lines 266-277
```python
clone_result = subprocess.run(
    [
        "git",
        "clone",
        "--depth=1",
        "https://github.com/silverhack/monkey365.git",
        str(monkey365_dir),
    ],
    [...]
)
```

**Issue**: The Git repository URL is hardcoded and not validated. If an attacker could modify the source code or configuration to change this URL, they could clone a malicious repository.

**Risk Level**: ⚠️ **LOW**
- URL is hardcoded in source code (not user-controlled)
- Would require code modification to exploit
- Mitigated by code review and access controls

**Recommendation**: Add URL validation if this becomes configurable:
```python
ALLOWED_REPO_URL = "https://github.com/silverhack/monkey365.git"

if repo_url != ALLOWED_REPO_URL:
    raise ValueError(f"Unauthorized repository URL: {repo_url}")
```

---

## Summary of Findings

| Severity | Count | Issues |
|----------|-------|--------|
| **CRITICAL** | 0 | None ✅ |
| **HIGH** | 0 | None ✅ |
| **MEDIUM** | 1 | Hardcoded temporary file path |
| **LOW** | 2 | Git URL not validated, No JSON file size limits |
| **INFO** | 0 | None |

---

## Required Mitigations

### 1. ⚠️ MEDIUM - Fix Temporary File Handling (RECOMMENDED)

**File**: `executor.py`, Line 490  
**Issue**: Hardcoded path `D:/AssistantAudit/temp/monkey365_scan.ps1`

**Mitigation**:
```python
import tempfile
import stat

def run_scan(self, scan_id: str) -> dict[str, object]:
    self.ensure_monkey365_ready()
    self._active_scan_id = scan_id
    script = self.build_script(scan_id)
    
    # Use secure temporary file
    temp_dir = Path(tempfile.gettempdir()) / "assistantaudit_monkey365"
    temp_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    ps1_path = temp_dir / f"scan_{scan_id}_{os.getpid()}.ps1"
    ps1_path.write_text(script, encoding="utf-8")
    
    # Restrict permissions (Windows + Unix)
    try:
        os.chmod(ps1_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass
    
    # ... rest of function
```

---

### 2. ⚠️ LOW - Add JSON File Size Limit (OPTIONAL)

**File**: `executor.py`, Line 565  
**Issue**: No file size validation before reading JSON

**Mitigation**:
```python
MAX_JSON_SIZE = 100 * 1024 * 1024  # 100 MB

for json_file in output_path.rglob("*.json"):
    if json_file.stat().st_size > MAX_JSON_SIZE:
        logger.warning(f"Skipping oversized file: {json_file.name}")
        continue
    try:
        data = json.loads(json_file.read_text(encoding="utf-8"))
        # ... rest of parsing
```

---

### 3. ⚠️ LOW - Validate Git URL if Configurable (OPTIONAL)

**File**: `executor.py`, Line 271  
**Issue**: Git URL is hardcoded but not validated

**Mitigation** (only if URL becomes configurable):
```python
ALLOWED_REPO_URL = "https://github.com/silverhack/monkey365.git"

def ensure_monkey365_ready(self, repo_url: str = ALLOWED_REPO_URL) -> Path:
    if repo_url != ALLOWED_REPO_URL:
        raise ValueError(f"Unauthorized repository: {repo_url}")
    # ... rest of function
```

---

## Additional Recommendations

### 1. Rate Limiting for Scans
Consider implementing rate limiting to prevent abuse:
```python
from functools import wraps
import time

class RateLimiter:
    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            self.calls = [c for c in self.calls if now - c < self.period]
            if len(self.calls) >= self.max_calls:
                raise RuntimeError(f"Rate limit exceeded: {self.max_calls} scans per {self.period}s")
            self.calls.append(now)
            return func(*args, **kwargs)
        return wrapper

@RateLimiter(max_calls=5, period=3600)  # 5 scans per hour
def run_scan(self, scan_id: str) -> dict[str, object]:
    # ... existing code
```

### 2. Audit Logging
Add security-relevant audit logging:
```python
def run_scan(self, scan_id: str) -> dict[str, object]:
    logger.info(
        f"[SECURITY AUDIT] Scan initiated: scan_id={scan_id}, "
        f"auth_mode={self.config.auth_mode}, "
        f"user={os.getenv('USER')}, "
        f"timestamp={time.time()}"
    )
    # ... existing code
```

### 3. Secrets in Memory
Consider using libraries like `cryptography` to handle secrets more securely in memory:
```python
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Use SecretStr type that zeros memory on deletion
```

---

## Testing Recommendations

### Security Test Cases

1. **Injection Tests**:
   ```python
   # Test PowerShell injection via credentials
   config = Monkey365Config(
       auth_mode="client_credentials",
       tenant_id="'; Invoke-Expression 'calc.exe'; #",
       client_id="...",
       client_secret="..."
   )
   # Should RAISE ValueError during validation
   ```

2. **Path Traversal Tests**:
   ```python
   # Test if scan_id can escape output directory
   executor.run_scan("../../etc/passwd")
   # Should be safely contained within output_dir
   ```

3. **Credential Leakage Tests**:
   ```python
   # Verify passwords are not logged
   config = Monkey365Config(
       auth_mode="ropc",
       password="SuperSecret123"
   )
   # Check logs - should NOT contain "SuperSecret123"
   ```

4. **Race Condition Tests**:
   ```python
   # Run multiple scans concurrently
   import concurrent.futures
   with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
       futures = [executor.submit(run_scan, f"scan_{i}") for i in range(10)]
   # Verify no file collisions or credential leakage
   ```

---

## Conclusion

The Monkey365 executor is **well-designed from a security perspective** with:
- ✅ Comprehensive input validation
- ✅ Proper PowerShell escaping
- ✅ Secure subprocess handling
- ✅ Conditional credential handling
- ✅ Password masking in logs

The identified issues are **low to medium severity** and are mitigated by application-level controls. The **MEDIUM** issue (hardcoded temp path) should be addressed for production use, but does not represent an immediate critical vulnerability.

**Recommendation**: **APPROVE** with suggested improvements for temporary file handling.

---

## Security Checklist

- [x] Subprocess arguments passed as list (no shell=True)
- [x] User inputs validated with whitelist patterns
- [x] PowerShell strings properly escaped
- [x] Credentials validated (UUIDs, emails, secrets)
- [x] Passwords never logged in plaintext
- [x] Timeout enforced on subprocess execution
- [x] Environment variables handled safely
- [x] Output capture uses safe methods
- [x] JSON parsing errors handled gracefully
- [ ] **TODO**: Use secure temporary file generation
- [ ] **TODO**: Add file size limits for JSON parsing
- [ ] **TODO**: Consider rate limiting for scan operations

---

**Overall Security Rating**: ⭐⭐⭐⭐ (4/5) - Very Good

*One star deducted for the temporary file handling issue. With that fix, this would be 5/5.*
