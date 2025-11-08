# Documentation Structure

**Purpose**: This document describes the documentation structure for the Activity Tracker Bot project, designed for both human developers and AI-assisted development.

**Last Updated**: 2025-11-08
**Status**: ✅ Implemented (Core structure complete)

## Goals

1. **Fast Onboarding**: New developers productive in < 1 hour
2. **AI-Friendly**: Structured for Claude, GitHub Copilot, and other AI tools
3. **Prevent Code Duplication**: Clear patterns and examples
4. **Maintainable**: Living documentation that evolves with code

## Implementation Status

✅ **Completed**:
- docs/project-context/ - AI-specific documentation
- docs/api/ - API contracts and schemas
- docs/onboarding/ - Core onboarding guides (00, 01, 02)
- Service-specific READMEs

❌ **Not Implemented** (by design):
- docs/templates/ - Code templates (not needed)
- docs/patterns/ - Separate patterns directory (consolidated in project-context/)
- docs/examples/ - Separate examples directory (integrated into patterns)
- docs/conventions/ - Conventions directory (not needed)
- CONTRIBUTING.md - Contribution guide (not needed at this stage)

## Actual Structure (Implemented)

```
activity-tracker-bot/
│
├── README.md                          # Project overview, quick start
├── ARCHITECTURE.md                    # High-level architecture (EXISTS)
├── TESTING.md                         # Testing strategy (EXISTS)
├── LOGGING_IMPLEMENTATION.md          # Logging details (EXISTS)
│
├── .ai-framework/                     # 🤖 GENERAL AI FRAMEWORK (Submodule)
│   └── docs/                          # General patterns and workflows
│
├── docs/
│   │
│   ├── DOCUMENTATION_STRUCTURE.md     # ✅ This file
│   │
│   ├── project-context/               # ✅ AI-SPECIFIC DOCUMENTATION
│   │   ├── README.md                  # Navigation and overview
│   │   ├── architecture-snapshot.md   # Current architecture state (CRITICAL)
│   │   ├── code-patterns.md           # 8 established patterns with examples
│   │   ├── anti-patterns.md           # 10 common mistakes to avoid
│   │   └── quick-reference.md         # Cheat sheet for AI tools
│   │
│   ├── api/                           # ✅ API DOCUMENTATION
│   │   ├── README.md                  # API overview
│   │   ├── bot-to-api-contract.md     # Bot ↔ API contract (CRITICAL)
│   │   ├── endpoints-reference.md     # Complete endpoint reference
│   │   └── schemas/                   # JSON schemas
│   │       ├── user.json
│   │       ├── activity.json
│   │       ├── category.json
│   │       └── user_settings.json
│   │
│   ├── onboarding/                    # ✅ DEVELOPER ONBOARDING
│   │   ├── README.md                  # Start here! (~40 min to productive)
│   │   ├── 00-prerequisites.md        # Required tools (5 min)
│   │   ├── 01-setup.md                # First-time setup (15 min)
│   │   └── 02-architecture-tour.md    # Architecture walkthrough (20 min)
│   │
│   ├── adr/                           # 📝 ARCHITECTURE DECISIONS (EXISTS)
│   │   ├── README.md
│   │   └── ADR-20251107-001/
│   │
│   └── testing/                       # 🧪 TESTING DOCS (EXISTS)
│       └── TEST_GAPS_ANALYSIS.md
│
├── services/
│   ├── data_postgres_api/
│   │   ├── README.md                  # ✅ Service overview + patterns
│   │   └── src/
│   │
│   └── tracker_activity_bot/
│       ├── README.md                  # ✅ Service overview + patterns
│       └── src/
│
└── tests/                             # Integration and smoke tests
    ├── integration/
    └── smoke/
```

## Key Documentation Files

### For AI Tools (MOST IMPORTANT)

**Start Here**: `docs/project-context/architecture-snapshot.md`
- Complete current state of architecture as of 2025-11-08
- Service topology, technology stack, data models
- API endpoints, architectural decisions
- Critical constraints for AI code generation

**Patterns**: `docs/project-context/code-patterns.md`
- 8 established patterns with full code examples
- Generic Repository, Service Layer, Handler, FSM, DI, etc.
- Real examples from codebase

**Anti-Patterns**: `docs/project-context/anti-patterns.md`
- 10 common mistakes to AVOID
- Side-by-side ❌ WRONG vs ✅ CORRECT examples
- Red flags and green flags summary

**Quick Reference**: `docs/project-context/quick-reference.md`
- Cheat sheet for common tasks
- Quick decision tree
- File templates, commands, default values
- 10 NEVER violate rules

**API Contract**: `docs/api/bot-to-api-contract.md`
- Formal contract between bot and API
- Request/response formats
- Error handling patterns
- Critical for inter-service communication

### For Human Developers

**Onboarding Start**: `docs/onboarding/README.md`
- 3-step path: Prerequisites → Setup → Architecture Tour
- ~40 minutes to productive first PR
- Success criteria checklist

**Setup Guide**: `docs/onboarding/01-setup.md`
- Step-by-step first-time setup
- Docker, environment, verification
- Common issues and fixes

**Architecture Tour**: `docs/onboarding/02-architecture-tour.md`
- Layer architecture explained
- Data flow examples
- "Where to find things" guide

**API Reference**: `docs/api/endpoints-reference.md`
- Complete API endpoint documentation
- Request/response formats
- Query parameters, errors
- Curl examples for testing

## Documentation Principles

### For Humans
1. **Progressive Disclosure**: Start simple, add complexity gradually
2. **Show, Don't Tell**: Code examples over prose
3. **Searchable**: Clear headings, good file names
4. **Up-to-date**: Living docs that evolve with code

### For AI
1. **Structured Context**: Clear hierarchy and organization
2. **Explicit Patterns**: Document the "how" and "why"
3. **Anti-patterns**: Explicitly state what NOT to do
4. **Examples**: Concrete, working code examples
5. **Contracts**: Clear interfaces and expectations

## Maintenance Strategy

1. **Every PR**: Update relevant documentation
2. **Monthly Review**: Check for outdated docs
3. **Quarterly Audit**: Comprehensive documentation review
4. **Version Control**: Documentation versioned with code

## Tools

- **Markdown**: All documentation in Markdown
- **Mermaid**: Diagrams as code (rendered by GitHub)
- **JSON Schema**: API contracts
- **Templates**: Python files with `# TODO:` markers

## Success Metrics

- **Time to First PR**: < 1 hour for new developer
- **Code Duplication**: < 5% (measured by jscpd)
- **Pattern Compliance**: > 90% (code review metric)
- **AI Accuracy**: > 85% correct code generation

## Navigation Quick Links

### 🤖 For AI Tools
1. Start: [Architecture Snapshot](project-context/architecture-snapshot.md)
2. Patterns: [Code Patterns](project-context/code-patterns.md)
3. Don'ts: [Anti-Patterns](project-context/anti-patterns.md)
4. Cheat Sheet: [Quick Reference](project-context/quick-reference.md)
5. API: [Bot-to-API Contract](api/bot-to-api-contract.md)

### 👨‍💻 For Developers
1. Start: [Onboarding Guide](onboarding/README.md)
2. Setup: [Setup Guide](onboarding/01-setup.md)
3. Learn: [Architecture Tour](onboarding/02-architecture-tour.md)
4. Reference: [API Endpoints](api/endpoints-reference.md)
5. Service Docs: [Bot README](../services/tracker_activity_bot/README.md) | [API README](../services/data_postgres_api/README.md)

### 📚 Reference
- [Architecture Details](../ARCHITECTURE.md)
- [Testing Guide](../TESTING.md)
- [ADRs](adr/README.md)
- [Test Gap Analysis](testing/TEST_GAPS_ANALYSIS.md)

---

**Last Updated**: 2025-11-08
**Status**: ✅ Core documentation structure implemented
**Next Steps**: Keep documentation updated with code changes
