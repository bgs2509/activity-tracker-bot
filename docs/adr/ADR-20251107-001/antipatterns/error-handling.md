# Anti-Pattern: Error Handling

> **ADR**: ADR-20251107-001  
> **Category**: 🟠 HIGH  
> [← Back to Anti-Patterns Index](README.md)

---

## Overview

Silent exception handling makes production debugging impossible.

**Symptom**: Silent failures, hidden bugs, impossible to debug

**Impact**: Production issues go unnoticed, debugging takes hours instead of minutes

---

## ❌ Anti-Pattern 2.1: Bare except:pass

### Problem

No way to know errors occurred, production debugging impossible

### Example (WRONG)

```python
# ❌ services/tracker_activity_bot/src/application/services/scheduler_service.py:103
if user_id in self.jobs:
    try:
        self.scheduler.remove_job(self.jobs[user_id])
    except Exception:
        pass  # ⚠️ Silently swallows ALL exceptions!
```

### Why This Matters

- Production debugging becomes impossible
- No way to know something went wrong
- Hidden bugs accumulate unnoticed
- Violates observability requirements
- Error patterns remain undiscovered

### Solution (CORRECT)

```python
# ✅ Always log with context
if user_id in self.jobs:
    try:
        self.scheduler.remove_job(self.jobs[user_id])
    except Exception as e:
        logger.warning(
            "Failed to remove scheduler job",
            extra={
                "user_id": user_id,
                "job_id": self.jobs.get(user_id),
                "error": str(e),
                "error_type": type(e).__name__
            }
        )
```

### Architecture Rule

> **NEVER use bare except:pass. All exceptions MUST be logged with context.**

---

## Best Practices

### 1. Always Log Exceptions

```python
# ✅ GOOD
try:
    risky_operation()
except SpecificError as e:
    logger.error("Operation failed", extra={"error": str(e), "context": ...})
    # Optionally re-raise or handle
```

### 2. Include Context

```python
# ✅ GOOD - Rich context
logger.error(
    "Failed to create activity",
    extra={
        "user_id": user_id,
        "category_id": category_id,
        "start_time": start_time.isoformat(),
        "error": str(e),
        "error_type": type(e).__name__,
        "traceback": traceback.format_exc()
    }
)
```

### 3. Use Appropriate Log Level

```python
# ✅ GOOD - Different levels for different situations
logger.debug("Debugging info")        # Development only
logger.info("Operation completed")   # Normal operation
logger.warning("Recoverable issue")  # Non-critical
logger.error("Operation failed")     # Critical
```

### 4. Catch Specific Exceptions

```python
# ❌ BAD
try:
    operation()
except Exception:  # Too broad!
    pass

# ✅ GOOD
try:
    operation()
except ValueError as e:  # Specific exception
    logger.error("Invalid value", extra={"error": str(e)})
except KeyError as e:  # Another specific exception
    logger.error("Missing key", extra={"error": str(e)})
```

---

## Related Documents

- [← Back to Anti-Patterns Index](README.md)
- [Resource Management →](resource-management.md)
- [Lifecycle Management →](lifecycle-management.md)
- [Structured Logging →](../03-architectural-principles.md#7-structured-logging)
