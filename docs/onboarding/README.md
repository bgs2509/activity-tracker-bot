# Developer Onboarding

**Welcome to Activity Tracker Bot!**

This guide will help you go from zero to productive in < 1 hour.

## Onboarding Path

Follow these guides in order:

| Step | Guide | Time | What You'll Learn |
|------|-------|------|-------------------|
| 0 | `00-prerequisites.md` | 5 min | What to install before starting |
| 1 | `01-setup.md` | 15 min | First-time project setup |
| 2 | `02-architecture-tour.md` | 20 min | Understand the codebase |

**Total Time**: ~40 minutes to productive first PR

## Quick Links

**For AI Tools**:
- [Project Context](../project-context/) - AI-specific documentation
- [Code Patterns](../project-context/code-patterns.md) - Patterns to follow
- [Anti-Patterns](../project-context/anti-patterns.md) - What NOT to do

**For Developers**:
- [API Documentation](../api/) - API endpoints and contracts
- [Testing Guide](../../TESTING.md) - How to test
- [Architecture Guide](../../ARCHITECTURE.md) - Detailed architecture

**For Operations**:
- [Makefile](../../Makefile) - Common development commands
- [Docker Compose](../../docker-compose.yml) - Service orchestration
- [README](../../README.md) - Project overview

## After Onboarding

Once you've completed the onboarding:

1. **Pick a Good First Issue**
   - Look for issues labeled `good-first-issue`
   - Start with something small (documentation, tests, minor bug fix)

2. **Join Development**
   - Read existing code before writing new code
   - Follow established patterns (see `docs/project-context/code-patterns.md`)
   - Ask questions if unclear

3. **Stay Updated**
   - Check documentation when patterns change
   - Review ADRs (Architecture Decision Records) for major changes
   - Keep your local environment up to date

## Getting Help

**Stuck on Setup?**
- Check `01-setup.md` troubleshooting section
- Review logs: `make logs-bot` or `make logs-api`
- Check if all containers are running: `docker ps`

**Don't Understand Architecture?**
- Re-read `02-architecture-tour.md`
- Check `ARCHITECTURE.md` for detailed patterns
- Look at existing similar code

**AI Generating Wrong Code?**
- Review `docs/project-context/anti-patterns.md`
- Check if pattern exists in `docs/project-context/code-patterns.md`
- Look at real examples in codebase

## Success Criteria

You've successfully onboarded when you can:

- ✅ Start all services (`make up`)
- ✅ Run all tests (`make test-all-docker`)
- ✅ Understand service topology (Bot ↔ API ↔ DB)
- ✅ Find your way around the codebase
- ✅ Identify which layer code belongs to (API/Application/Infrastructure/Domain)
- ✅ Add a simple handler or API endpoint

**Ready to start?** → Open `00-prerequisites.md`

---

**Last Updated**: 2025-11-08
**Maintained By**: Development Team
