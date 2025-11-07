# YAGNI Exclusions

> **ADR**: ADR-20251107-001  
> [← Back to Index](README.md) | [← Previous: Tech Stack](04-technology-stack.md) | [Next: Alternatives →](06-alternatives-considered.md)

---

## What We DELIBERATELY Exclude

Following **KISS** and **YAGNI** principles, we DO NOT include these components in the current architecture. Each exclusion is justified and includes criteria for when to add it later.

---

## 1. ❌ Nginx API Gateway

**Reason**: Only 2 services, direct Docker networking sufficient

**Current Solution**: Docker Compose internal network

**When to Add**: Level 3+ (Pre-Production)
- Multiple business services (>3)
- Need for SSL/TLS termination
- Rate limiting requirements
- Geographic distribution
- Load balancing needs

---

## 2. ❌ RabbitMQ Message Broker

**Reason**: No async event processing between services

**Current Solution**: Synchronous HTTP requests are sufficient

**When to Add**: When we need:
- Async notifications (email, push)
- Background data processing
- Event-driven workflows
- Job queues
- Message guarantees (at-least-once delivery)

---

## 3. ❌ MongoDB

**Reason**: All data fits relational model, no unstructured data

**Current Solution**: PostgreSQL with JSONB for tags

**When to Add**: When we have:
- Unstructured data (logs, analytics)
- Flexible schema requirements
- Document storage needs
- Very high write throughput requirements

---

## 4. ❌ Prometheus + Grafana

**Reason**: PoC level, CloudWatch/Docker logs sufficient

**Current Solution**: Structured JSON logs, Docker stats

**When to Add**: Level 2+ (Development)
- Performance metrics tracking
- Custom dashboards
- Alerting on SLIs/SLOs
- Historical data analysis

---

## 5. ❌ Jaeger Distributed Tracing

**Reason**: Only 2 services, logs sufficient for debugging

**Current Solution**: Correlation IDs in structured logs

**When to Add**: Level 3+ when we have:
- >5 services
- Complex request flows
- Performance bottleneck analysis
- Latency investigation needs

---

## 6. ❌ ELK Stack (Elasticsearch, Logstash, Kibana)

**Reason**: PoC level, Docker logs sufficient

**Current Solution**: `docker logs`, structured JSON

**When to Add**: Level 4 (Production)
- Centralized log aggregation
- Advanced log search
- Log retention policies (>30 days)
- Complex log analytics

---

## 7. ❌ Kubernetes

**Reason**: Single-host deployment, Docker Compose sufficient

**Current Solution**: Docker Compose with restart policies

**When to Add**: Level 4 (Production)
- Multi-host orchestration
- Auto-scaling (horizontal pod autoscaling)
- Rolling updates without downtime
- High availability requirements
- Multiple environments (staging, prod)

---

## 8. ❌ OAuth2 / JWT Authentication

**Reason**: Telegram Bot authentication sufficient

**Current Solution**: Telegram user ID as authentication

**When to Add**: When we add:
- Web frontend
- Mobile app
- Third-party API access
- Public API endpoints

---

## Summary Table

| Component | Reason for Exclusion | When to Add | Current Solution |
|-----------|---------------------|-------------|------------------|
| Nginx | Only 2 services | Level 3+ (>3 services) | Docker networking |
| RabbitMQ | No async events | Event-driven workflows | Sync HTTP |
| MongoDB | Relational data only | Unstructured data | PostgreSQL + JSONB |
| Prometheus | PoC level | Level 2+ (metrics) | Docker stats |
| Jaeger | Only 2 services | Level 3+ (>5 services) | Correlation IDs |
| ELK Stack | PoC level | Level 4 (production) | docker logs |
| Kubernetes | Single host | Level 4 (multi-host) | Docker Compose |
| OAuth2/JWT | Telegram auth OK | Web/mobile app | Telegram user ID |

---

## YAGNI Compliance Check

✅ **We have perfect YAGNI compliance** — No unnecessary components!

This keeps:
- Architecture simple
- Maintenance burden low
- Development velocity high
- Infrastructure costs minimal

We can add these components incrementally as requirements emerge.

---

## Related Documents

- [← Previous: Technology Stack](04-technology-stack.md)
- [Next: Alternatives Considered →](06-alternatives-considered.md)
- [Decision Overview](01-decision-overview.md)
- [← Back to Index](README.md)
