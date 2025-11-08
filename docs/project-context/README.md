# Project Context for AI Tools

**Purpose**: This directory contains project-specific context optimized for AI-assisted development (Claude, GitHub Copilot, Cursor, etc.).

> **Note**: This complements the general `.ai-framework` submodule with Activity Tracker Bot specific patterns and constraints.

## Quick Navigation

| File | Purpose | When to Read |
|------|---------|--------------|
| `architecture-snapshot.md` | Current architecture state | Always read first |
| `code-patterns.md` | Established patterns in THIS project | Before writing code |
| `anti-patterns.md` | Common mistakes to AVOID | Before writing code |
| `quick-reference.md` | Cheat sheet for AI tools | For quick lookups |

## How AI Should Use This

### When Generating New Code

1. **Read** `architecture-snapshot.md` - Understand current state
2. **Check** `code-patterns.md` - Follow established patterns
3. **Avoid** `anti-patterns.md` - Don't repeat past mistakes
4. **Reference** `quick-reference.md` - Quick decisions

### When Modifying Existing Code

1. **Identify** which layer you're working in (API/Application/Infrastructure/Domain)
2. **Follow** existing patterns in that layer
3. **Check** `anti-patterns.md` to ensure no violations
4. **Maintain** consistency with surrounding code

## Integration with .ai-framework

```
.ai-framework/               ← General microservices patterns (READ-ONLY submodule)
├── docs/atomic/            ← Atomic documentation (databases, integrations, etc.)
├── docs/guides/            ← Implementation guides
└── docs/quality/           ← Quality checklists

docs/project-context/       ← THIS PROJECT specific context (THIS repository)
├── architecture-snapshot.md   ← How Activity Tracker Bot is built NOW
├── code-patterns.md           ← Patterns we actually USE in this project
├── anti-patterns.md           ← Mistakes we MADE and fixed
└── quick-reference.md         ← Quick decisions for this project
```

**Key Difference**:
- `.ai-framework` = Generic patterns for ANY async microservice project
- `docs/project-context/` = Specific to Activity Tracker Bot only

## Maintenance

- **Update on every PR**: If you introduce new pattern or fix anti-pattern
- **Monthly review**: Keep architecture snapshot current
- **Version**: Document major architectural changes

## Success Metrics

AI-generated code should:
- ✅ Match existing code style and structure
- ✅ Follow layer boundaries (no bot direct DB access)
- ✅ Use Generic Repository pattern for new models
- ✅ Not duplicate existing code
- ✅ Include proper type hints and docstrings

---

**Last Updated**: 2025-11-08
**Maintainer**: Development Team
