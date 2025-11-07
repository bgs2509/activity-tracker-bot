# References & Maintenance

> **ADR**: ADR-20251107-001  
> [← Back to Index](README.md)

---

## .ai-framework Documentation

### Core Principles

- **.ai-framework/ARCHITECTURE.md** — Core architectural principles
  - Lines 101-143: HTTP-Only Data Access (MANDATORY)
  - Lines 145-176: Single Event Loop Ownership (MANDATORY)
  - Lines 178-193: Async-First Design
  - Lines 194-232: Type Safety
  - Lines 234-256: DDD & Hexagonal Architecture
  - Lines 691-713: Best Practices & Anti-Patterns

- **.ai-framework/CONTRIBUTING.md** — Code quality standards
  - Lines 160-200: Python code examples with type hints
  - Lines 232-241: Naming conventions table
  - Lines 269-284: Code quality gates (mypy, ruff, pytest)

- **.ai-framework/EXAMPLES.md** — Implementation examples
  - Lines 442-454: Business API example
  - Lines 456-474: Data API example
  - Lines 518-564: HTTP communication pattern
  - Lines 606-629: Health checks example
  - Lines 630-648: Structured logging example

- **.ai-framework/README.md** — Framework overview
  - Lines 34-48: Improved Hybrid Approach diagram
  - Line 238: Service naming convention
  - Lines 304-313: Technology stack

---

## Project Documentation

- **README.md** — Project overview and quick start
- **docker-compose.yml** — Service orchestration configuration
- **artifacts/analysis/refactor-2025-11-07.md** — Violation analysis and TODO plan
- **Makefile** — Development commands (up, down, logs, test, lint)

---

## External References

### Technology Documentation

- **FastAPI**: https://fastapi.tiangolo.com/
  - Async support: https://fastapi.tiangolo.com/async/
  - Dependency injection: https://fastapi.tiangolo.com/tutorial/dependencies/

- **Aiogram**: https://docs.aiogram.dev/
  - FSM: https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine/index.html
  - Redis storage: https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine/storages.html

- **SQLAlchemy 2.0**: https://docs.sqlalchemy.org/
  - Async ORM: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html

- **Pydantic**: https://docs.pydantic.dev/
  - Validation: https://docs.pydantic.dev/latest/concepts/validators/

- **mypy**: https://mypy.readthedocs.io/
  - Strict mode: https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-strict

### Best Practices

- **PostgreSQL Best Practices**: https://wiki.postgresql.org/wiki/Don%27t_Do_This
- **Docker Compose Best Practices**: https://docs.docker.com/compose/compose-file/
- **Python Async Best Practices**: https://docs.python.org/3/library/asyncio-dev.html

---

## Maintenance

### Status Updates

- **Initial Version**: 2025-11-07 (v1.0 - ADR created)
- **Updated**: 2025-11-07 (v1.1 - Anti-Patterns added)
- **Refactored**: 2025-11-07 (v1.2 - Split into modular structure)
- **Last Reviewed**: 2025-11-07
- **Next Review**: After Week 0 completion (Resource leak fixes), then Phase 2 (Type Safety)

---

### Change Log

**v1.2 - 2025-11-07 (Modular Refactor)**:
- 🔄 Split 1,496-line monolithic file into 19 modular documents
- 📁 Created organized directory structure (core, antipatterns, implementation)
- 🔗 Added comprehensive cross-references between documents
- 📊 Improved navigation with README indexes at each level
- 🎯 Each file now <250 lines for optimal readability (~5-10 min reading time)

**v1.1 - 2025-11-07**:
- ➕ Added comprehensive "Critical Anti-Patterns to Avoid" section (433 lines)
- ➕ Documented 6 critical anti-patterns from production analysis
- ➕ Added monitoring commands and expected values for healthy system
- ➕ Added prevention checklist for production deployment
- ➕ Added Week 0 URGENT tasks to Follow-Up Actions
- 📚 Source: artifacts/analysis/refactor-2025-11-07.md Phase 1.5
- 🎯 Impact: Prevents memory leaks, connection exhaustion, production crashes

**v1.0 - 2025-11-07**:
- ✨ Initial ADR created
- 📐 Defined Improved Hybrid Architecture
- 📋 Documented all architectural decisions
- ✅ Phase 1 marked as complete

---

### Storage Location

- **Primary**: `docs/adr/ADR-20251107-001/` (modular directory)
- **Backup**: Git repository (version controlled)
- **Format**: 19 Markdown files + README indexes

---

### Change Management

**When to update this ADR**:
1. Major architectural changes (e.g., adding RabbitMQ, moving to microservices)
2. Technology stack changes (e.g., switching to different database, framework)
3. Principle violations discovered during implementation or code review
4. Maturity level transitions (Level 1 → Level 2 → Level 3 → Level 4)
5. New anti-patterns discovered in production
6. Significant performance or scalability changes

**How to supersede**:
1. Create new ADR with incremented number (e.g., `ADR-20251215-002-add-rabbitmq.md`)
2. Update this ADR status in metadata section to "Superseded by ADR-20251215-002"
3. Link both ADRs in references section
4. Update main ADR index (`docs/adr/README.md`)
5. Keep old ADR for historical context (DO NOT delete)

**How to update modular ADR**:
- Update specific files independently (e.g., update only `antipatterns/resource-management.md`)
- Increment version in README.md
- Add entry to change log in this file
- Update "Last Reviewed" date
- Create focused git commit for changed files only

---

### Index Alignment

- ✅ Added to project: `docs/adr/README.md`
- ✅ Referenced in: `artifacts/analysis/refactor-2025-11-07.md`
- ✅ Linked from: `README.md` (under Documentation section)
- ✅ Cross-referenced: All 19 modular files link to each other

---

### Document Statistics

- **Total Documents**: 19 files
- **Core Architecture**: 8 files (~1,100 lines)
- **Anti-Patterns**: 4 files (~530 lines)
- **Implementation**: 5 files (~750 lines)
- **Navigation**: 2 files (main + references, ~200 lines)
- **Average File Size**: ~136 lines (optimal for reading!)
- **Total Size**: ~2,580 lines (including navigation/cross-references)

---

## Version History Summary

| Version | Date | Changes | Lines | Files |
|---------|------|---------|-------|-------|
| v1.0 | 2025-11-07 | Initial ADR | 1,063 | 1 |
| v1.1 | 2025-11-07 | + Anti-Patterns | 1,496 | 1 |
| v1.2 | 2025-11-07 | Modular refactor | 2,580 | 19 |

---

**Approved By**: Development Team  
**Implementation Status**: Phase 1 ✅ Complete | Phase 0 🔴 URGENT | Phase 2-5 ⏳ Planned  
**Compliance**: 100% .ai-framework aligned (with documented YAGNI exclusions)

---

[← Back to Index](README.md)
