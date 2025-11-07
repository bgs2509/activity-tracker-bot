# Phase 1-2: Type Safety & Quality

> **ADR**: ADR-20251107-001  
> **Priority**: 🔴 CRITICAL  
> **Time**: 16-20 hours  
> [← Back to Implementation Index](README.md)

---

## Phase 1: Core Architecture ✅ COMPLETE

Already implemented:
- ✅ Service structure (DDD/Hexagonal: domain/, application/, infrastructure/, api/)
- ✅ HTTP-only data access (Bot → Data API via HTTP)
- ✅ PostgreSQL with Alembic migrations
- ✅ Redis for FSM storage
- ✅ Docker Compose orchestration

**Status**: Phase 1 complete as of 2025-11-07

---

## Phase 2: Type Safety & Quality

### Task 2.1: Create Application Service Layer (4-5 hours)

**Goal**: Add application/services/ in data_postgres_api

**Current Problem**: API routes directly call repositories (violates DDD)

**Solution**: Add Application Service layer between API and repositories

**Steps**:
1. Create directory: `services/data_postgres_api/src/application/services/`
2. Implement ActivityService, CategoryService, UserService
3. Create dependencies.py for DI
4. Update API routes to use services

**Checklist**:
- [ ] Create application/services/ directory
- [ ] Implement ActivityService
- [ ] Implement CategoryService
- [ ] Implement UserService
- [ ] Implement UserSettingsService
- [ ] Create api/dependencies.py
- [ ] Update all API routes
- [ ] Test endpoints still work

**Full Details**: `artifacts/analysis/refactor-2025-11-07.md` Task 2.1

---

### Task 2.2: Add mypy Configuration (2-3 hours)

**Goal**: Enable strict type checking with mypy

**Current Problem**: No mypy configuration, type violations undetected

**Steps**:
1. Create pyproject.toml (both services) with strict settings
2. Run mypy, fix violations iteratively
3. Add type-check target to Makefile

**Configuration**:
```toml
[tool.mypy]
python_version = "3.12"
strict = true
disallow_untyped_defs = true
warn_return_any = true
```

**Checklist**:
- [ ] Create pyproject.toml in data_postgres_api
- [ ] Create pyproject.toml in tracker_activity_bot
- [ ] Run mypy, fix violations
- [ ] Update Makefile with type-check target
- [ ] Verify make type-check passes

**Full Details**: `artifacts/analysis/refactor-2025-11-07.md` Task 2.2

---

### Task 2.3: Add Complete Type Hints (3-4 hours)

**Goal**: All HTTP methods return typed Pydantic models

**Current Problem**: HTTP clients return dict/Any instead of typed models

**Steps**:
1. Create response models in bot service (schemas/)
2. Update base HTTP client with generic type support
3. Update service clients to return typed models

**Checklist**:
- [ ] Create schemas/ directory in bot service
- [ ] Implement ActivityResponse, ActivityListResponse
- [ ] Implement CategoryResponse, UserResponse
- [ ] Update DataAPIClient with TypeVar[T]
- [ ] Update all service clients
- [ ] Run mypy to verify

**Full Details**: `artifacts/analysis/refactor-2025-11-07.md` Task 2.3

---

### Task 2.4: Add Comprehensive Docstrings (4-5 hours)

**Goal**: All public functions have Args/Returns/Raises docstrings

**Pattern**:
```python
def function_name(arg1: Type1) -> ReturnType:
    """
    One-line summary.
    
    Args:
        arg1: Description of arg1
    
    Returns:
        Description of return value
    
    Raises:
        ExceptionType: When this exception is raised
    """
```

**Files to Update**:
- All handlers in tracker_activity_bot/src/api/handlers/
- All services in data_postgres_api/src/application/services/
- All repositories in data_postgres_api/src/infrastructure/repositories/
- All HTTP clients in tracker_activity_bot/src/infrastructure/http_clients/

**Checklist**:
- [ ] Update activity.py handler
- [ ] Update categories.py handler
- [ ] Update all service classes
- [ ] Update all repository classes
- [ ] Update all HTTP client classes

**Full Details**: `artifacts/analysis/refactor-2025-11-07.md` Task 2.4

---

### Task 2.5: Implement Dependency Injection (2-3 hours)

**Goal**: Replace global HTTP client instances with DI

**Current Problem**: Global instances in handlers, never closed

**Solution**: Create dependencies.py with shared client

**Checklist**:
- [ ] Create api/dependencies.py
- [ ] Implement get_api_client()
- [ ] Implement get_activity_service()
- [ ] Implement get_category_service()
- [ ] Update handlers to use DI
- [ ] Test all endpoints work

**Full Details**: `artifacts/analysis/refactor-2025-11-07.md` Task 2.5

---

## Summary

**Total Time**: 16-20 hours  
**Tasks**: 5 major tasks  
**Priority**: 🔴 CRITICAL (must do after Phase 0)

---

## Related Documents

- [← Implementation Index](README.md)
- [Previous: Phase 0 URGENT](phase-0-urgent.md)
- [Next: Phase 3-5 →](phase-3-5.md)
- **Full Details**: `artifacts/analysis/refactor-2025-11-07.md` Phase 2
