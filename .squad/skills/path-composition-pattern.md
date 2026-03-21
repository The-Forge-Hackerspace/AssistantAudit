# Path Composition Pattern in Service/Tool Architecture

## Problem
When architecting tool runners that receive file paths from service layers, double-nesting can occur if both layers add path segments that represent the same logical concept.

## Pattern Recognition
Look for this anti-pattern:
```python
# Service layer
output_path = base_dir / entity_id
executor_config = Config(output_dir=output_path)

# Tool runner (WRONG)
class Executor:
    def process(self):
        final_path = self.output_dir / self.scan_id  # entity_id added again!
```

## Solution
1. **Clear ownership**: Decide which layer is responsible for constructing the complete path
2. **Service layer** should compose the full path before passing to executor
3. **Executor** should use the path as-is without adding entity identifiers again

## Correct Pattern
```python
# Service layer (owns path composition)
scan_id = uuid.uuid4()
output_path = ensure_scan_directory(entity, scan_id)  # Complete path
executor_config = Config(output_dir=output_path)

# Tool runner (uses path directly)
class Executor:
    def process(self):
        final_path = self.output_dir  # Use as-is, don't add scan_id again
        self.write_to(final_path)
```

## Detection Checklist
- [ ] Executor receives `output_dir` containing entity ID
- [ ] Executor's build_script/parse methods add entity ID again
- [ ] Result: `{base}/{id}/{id}/{output}`

## Example: Monkey365 Bug
- **Files affected**: `executor.py` lines 151, 311
- **Issue**: `build_script()` did `self.output_dir / scan_id` but `self.output_dir` already included `scan_id`
- **Fix**: Use `self.output_dir` directly
- **Lesson**: Audit path composition at layer boundaries

## References
- AssistantAudit Monkey365 path nesting bug (Fixed in executor.py)
- Storage layer: `backend/app/core/storage.py` provides canonical path composition
- Service layer: `backend/app/services/monkey365_scan_service.py` demonstrates correct usage
