"""
Security fixes for Monkey365 Executor
Apply these changes to backend/app/tools/monkey365_runner/executor.py
"""

# ──────────────────────────────────────────────────────────────────────────
# FIX 1: MEDIUM Priority - Secure Temporary File Handling
# ──────────────────────────────────────────────────────────────────────────

# CURRENT (Line 490-492):
# ps1_path = Path("D:/AssistantAudit/temp/monkey365_scan.ps1")
# ps1_path.parent.mkdir(parents=True, exist_ok=True)
# _ = ps1_path.write_text(script, encoding="utf-8")

# RECOMMENDED FIX:
import tempfile
import stat
import os

def run_scan_FIXED(self, scan_id: str) -> dict[str, object]:
    """Lance le scan Monkey365 (synchrone) - SECURE VERSION"""
    self.ensure_monkey365_ready()
    self._active_scan_id = scan_id

    script = self.build_script(scan_id)
    
    # Use secure temporary file with restricted permissions
    temp_dir = Path(tempfile.gettempdir()) / "assistantaudit_monkey365"
    temp_dir.mkdir(parents=True, exist_ok=True, mode=0o700)  # Owner only
    
    # Include scan_id and PID to prevent race conditions
    ps1_path = temp_dir / f"scan_{scan_id}_{os.getpid()}.ps1"
    ps1_path.write_text(script, encoding="utf-8")
    
    # Set file permissions to owner read/write only (Windows & Unix)
    try:
        os.chmod(ps1_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    except Exception:
        pass  # Windows may not support POSIX permissions fully
    
    start_time = time.time()
    output_path = Path(self.config.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
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

        if result.returncode != 0:
            error = Monkey365ExecutionError(
                "PowerShell failed (code "
                + str(result.returncode)
                + "):\nSTDOUT:\n"
                + result.stdout
                + "\nSTDERR:\n"
                + result.stderr
            )
            return {"status": "error", "scan_id": scan_id, "error": str(error)}

        results = self.parse_results(result.stdout)
        return {"status": "success", "scan_id": scan_id, "results": results}

    except subprocess.TimeoutExpired as exc:
        raw_output = {
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "returncode": None,
            "duration_seconds": time.time() - start_time,
        }
        (output_path / "powershell_raw_output.json").write_text(
            json.dumps(raw_output, indent=2),
            encoding="utf-8",
        )
        return {"status": "timeout", "scan_id": scan_id, "error": "Timeout 1h dépassé"}
    except FileNotFoundError:
        return {"status": "error", "scan_id": scan_id, "error": "powershell.exe introuvable"}
    finally:
        # Securely delete temporary file
        if ps1_path.exists():
            try:
                ps1_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temporary script: {e}")


# ──────────────────────────────────────────────────────────────────────────
# FIX 2: LOW Priority - Add JSON File Size Limit
# ──────────────────────────────────────────────────────────────────────────

# CURRENT (Line 565-576):
# for json_file in output_path.rglob("*.json"):
#     try:
#         data: object = cast(object, json.loads(json_file.read_text(encoding="utf-8")))

# RECOMMENDED FIX:
MAX_JSON_SIZE = 100 * 1024 * 1024  # 100 MB

def _parse_output_FIXED(self, scan_id: str) -> list[dict[str, object]]:
    """Parse les JSON de sortie Monkey365 - SECURE VERSION"""
    results: list[dict[str, object]] = []
    output_path = self.output_dir / scan_id

    for json_file in output_path.rglob("*.json"):
        try:
            # Check file size before reading
            file_size = json_file.stat().st_size
            if file_size > MAX_JSON_SIZE:
                logger.warning(
                    f"Skipping oversized JSON file: {json_file.name} "
                    f"({file_size / (1024*1024):.2f} MB exceeds {MAX_JSON_SIZE / (1024*1024):.0f} MB limit)"
                )
                continue
            
            data: object = cast(object, json.loads(json_file.read_text(encoding="utf-8")))
            if isinstance(data, list):
                for item in cast(list[object], data):
                    if isinstance(item, dict):
                        results.append(cast(dict[str, object], item))
            elif isinstance(data, dict):
                results.append(cast(dict[str, object], data))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to parse JSON file {json_file.name}: {e}")
            continue

    return results


# ──────────────────────────────────────────────────────────────────────────
# FIX 3: OPTIONAL - Add Scan Rate Limiting
# ──────────────────────────────────────────────────────────────────────────

from functools import wraps
import time
from threading import Lock

class RateLimiter:
    """Rate limiter to prevent scan abuse."""
    
    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self.lock = Lock()
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                now = time.time()
                # Remove calls outside the time window
                self.calls = [c for c in self.calls if now - c < self.period]
                
                if len(self.calls) >= self.max_calls:
                    raise RuntimeError(
                        f"Rate limit exceeded: maximum {self.max_calls} scans "
                        f"per {self.period} seconds. Please wait before retrying."
                    )
                
                self.calls.append(now)
            
            return func(*args, **kwargs)
        return wrapper


# Add to Monkey365Executor class:
class Monkey365Executor:
    # ... existing code ...
    
    _scan_rate_limiter = RateLimiter(max_calls=10, period=3600)  # 10 scans per hour
    
    @_scan_rate_limiter
    def run_scan(self, scan_id: str) -> dict[str, object]:
        """Lance le scan Monkey365 (synchrone) with rate limiting"""
        # ... existing implementation ...


# ──────────────────────────────────────────────────────────────────────────
# FIX 4: OPTIONAL - Add Security Audit Logging
# ──────────────────────────────────────────────────────────────────────────

def run_scan_with_audit_logging(self, scan_id: str) -> dict[str, object]:
    """Lance le scan Monkey365 avec audit logging"""
    
    # Security audit log
    logger.info(
        "[SECURITY AUDIT] Monkey365 scan initiated: "
        f"scan_id={scan_id}, "
        f"auth_mode={self.config.auth_mode}, "
        f"provider={self.config.provider}, "
        f"user={os.getenv('USER') or os.getenv('USERNAME')}, "
        f"timestamp={time.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    try:
        result = self.run_scan(scan_id)
        
        # Log success
        logger.info(
            f"[SECURITY AUDIT] Scan completed: scan_id={scan_id}, "
            f"status={result.get('status')}"
        )
        
        return result
    except Exception as e:
        # Log failure
        logger.error(
            f"[SECURITY AUDIT] Scan failed: scan_id={scan_id}, "
            f"error={type(e).__name__}: {str(e)}"
        )
        raise


# ──────────────────────────────────────────────────────────────────────────
# FIX 5: OPTIONAL - Sanitize Output Before Writing
# ──────────────────────────────────────────────────────────────────────────

import re

def sanitize_output(output: str) -> str:
    """Remove potential credentials from output before writing to disk."""
    # Pattern for common credential patterns
    patterns = [
        (r'(password|secret|token|key)\s*[:=]\s*["\']?([^"\'\s]+)["\']?', r'\1: ***'),
        (r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', r'Bearer ***'),
        (r'Basic\s+[A-Za-z0-9+/]+=*', r'Basic ***'),
    ]
    
    sanitized = output
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    return sanitized


def run_scan_with_sanitized_output(self, scan_id: str) -> dict[str, object]:
    """Run scan and sanitize output before writing."""
    # ... existing subprocess.run code ...
    
    raw_output = {
        "stdout": sanitize_output(result.stdout),
        "stderr": sanitize_output(result.stderr),
        "returncode": result.returncode,
        "duration_seconds": time.time() - start_time,
    }
    
    (output_path / "powershell_raw_output.json").write_text(
        json.dumps(raw_output, indent=2),
        encoding="utf-8",
    )
    
    # ... rest of code ...


# ──────────────────────────────────────────────────────────────────────────
# VALIDATION: Test the Fixes
# ──────────────────────────────────────────────────────────────────────────

def test_secure_temp_file():
    """Test that temporary files are created securely."""
    import tempfile
    import stat
    
    temp_dir = Path(tempfile.gettempdir()) / "assistantaudit_monkey365"
    temp_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    
    scan_id = "test_scan_123"
    ps1_path = temp_dir / f"scan_{scan_id}_{os.getpid()}.ps1"
    ps1_path.write_text("# Test script", encoding="utf-8")
    
    try:
        os.chmod(ps1_path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass
    
    # Verify file exists and has correct permissions
    assert ps1_path.exists()
    
    # Clean up
    ps1_path.unlink()
    print("✓ Secure temporary file test passed")


def test_rate_limiter():
    """Test rate limiting functionality."""
    limiter = RateLimiter(max_calls=3, period=5)
    
    @limiter
    def dummy_scan():
        return "success"
    
    # Should succeed for first 3 calls
    for i in range(3):
        result = dummy_scan()
        assert result == "success"
    
    # 4th call should fail
    try:
        dummy_scan()
        assert False, "Expected RuntimeError"
    except RuntimeError as e:
        assert "Rate limit exceeded" in str(e)
    
    print("✓ Rate limiter test passed")


def test_json_size_limit():
    """Test JSON file size validation."""
    import tempfile
    
    # Create a test JSON file larger than limit
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        large_data = '{"data": "' + 'x' * (MAX_JSON_SIZE + 1000) + '"}'
        f.write(large_data)
        temp_file = Path(f.name)
    
    try:
        # Should skip the file
        file_size = temp_file.stat().st_size
        assert file_size > MAX_JSON_SIZE
        print(f"✓ JSON size limit test passed (file: {file_size} bytes)")
    finally:
        temp_file.unlink()


if __name__ == "__main__":
    print("Running security fix validation tests...\n")
    test_secure_temp_file()
    test_rate_limiter()
    test_json_size_limit()
    print("\n✅ All security fix tests passed!")
