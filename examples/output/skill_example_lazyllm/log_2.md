```yaml
---
name: production-microservice-deployment
description: Production-ready guide for deploying microservices using a blue-green strategy, based on real-world incidents involving connection exhaustion and performance degradation due to missing indexing.
version: 0.2.0
status: Evolving
---
```

# Production Microservice Deployment with Blue-Green Strategy

## Introduction

This guide provides a concise, production-grade procedure for safely deploying microservices using the blue-green deployment strategy. It is designed for use when zero-downtime deployments are required and rollback safety is critical. The steps and checks included are derived from actual deployment failures involving database connection exhaustion and performance degradation under load.

Use this guide during scheduled deployments of stateful or database-dependent services where infrastructure capacity and query performance must be validated at scale.

---

## Deployment Context

- **Strategy**: Blue-green deployment with incremental traffic shifting (10% → 25% → 50% → 75% → 100%)
- **Environment**: Kubernetes-based platform with service mesh routing; PostgreSQL backend
- **Goals**:
  - Achieve zero-downtime release
  - Detect issues before full cutover
  - Ensure system stability during dual-environment operation
  - Enable rapid rollback (<2 minutes) if thresholds are breached

---

## Pre-Deployment Checklist

### ✅ Database
- [**CRITICAL**] Validate that all new queries have appropriate indexes (e.g., `user_segment`)
- [**CRITICAL**] Confirm database `max_connections` supports combined blue + green load
- [**CRITICAL**] Verify per-pod connection pool size is adjusted to prevent pool overflow
- Ensure staging environment uses production-scale data (e.g., 50M rows, not 5M)

### ✅ Monitoring & Alerts
- [**CRITICAL**] Query latency monitoring enabled (P99 tracked in real time)
- Connection pool usage monitored with alerting (threshold: >80% of max_connections)
- SLO violation detection active (latency >500ms triggers alert)

### ✅ Testing & Validation
- [**CRITICAL**] Full-capacity integration test completed with dual environments running
- Performance testing executed using production-like dataset sizes
- Indexing review performed for all schema-affecting changes
- Rollback procedure tested in staging

### ✅ Process
- Deployment checklist updated and reviewed
- Incident response roles assigned (on-call engineer, comms lead)
- Emergency rollback command pre-validated

---

## Deployment Procedure

1. **Deploy Green Environment**
   ```bash
   kubectl apply -f recommendation-service-green.yaml
   ```
   Wait for all pods to reach `Running` and pass readiness checks:
   ```bash
   kubectl get pods -l app=recommendation-service,version=v2.5.0
   ```

2. **Verify Health & Connectivity**
   - Check logs for connection errors
   - Confirm database connectivity and migration success
   - Validate `/health` endpoint returns 200

3. **Begin Incremental Traffic Shift**
   Apply traffic split via service mesh:
   ```bash
   # 10% to green
   istioctl replace -f traffic-split-10pct.yaml
   sleep 180
   ```

4. **Monitor Key Metrics After Each Step**
   - P99 latency (<500ms)
   - Error rate (<0.5%)
   - Active DB connections (<80% of max)
   - CPU/Memory utilization stable

   Repeat shift:
   ```bash
   istioctl replace -f traffic-split-25pct.yaml; sleep 300
   istioctl replace -f traffic-split-50pct.yaml; sleep 600
   istioctl replace -f traffic-split-75pct.yaml; sleep 900
   ```

5. **Final Cutover (100%)**
   ```bash
   istioctl replace -f traffic-split-100pct.yaml
   ```

6. **Decommission Blue**
   After 30 minutes of stable operation:
   ```bash
   kubectl delete deployment recommendation-service-blue --namespace=production
   ```

---

## Rollback Procedure

### When to Rollback
Roll back immediately if **any** of the following occur:
- P99 latency exceeds **500ms** for >2 minutes
- Error rate spikes above **1%**
- Database connection usage reaches **90%**
- SLO violation detected

### Execute Rollback
```bash
istioctl replace -f traffic-split-0pct.yaml
```
> ⚠️ This command routes 100% traffic back to the blue (stable) environment.

### Expected Recovery Time
- **Target**: <2 minutes
- Service should stabilize within 90 seconds
- Confirm health endpoints and metrics return to baseline

---

## Common Pitfalls & Solutions

| Issue | Symptom | Root Cause | Solution |
|------|--------|-----------|----------|
| Database connection exhaustion | 5xx errors during traffic shift, "too many connections" logs | `max_connections=100` too low; per-pod pools not scaled down | Increase DB limit; reduce per-pod pool size |
| Latency spike at 75% shift | P99 jumps to 780ms, SLO breach | Missing index on `user_segment` causes full table scan | Add index; validate all queries pre-deploy |
| No early warning | Alerts silent during degradation | No monitoring on connection count or query latency | Add alerts on key DB and service metrics |
| Staging passes, prod fails | Deployment works locally but fails in production | Staging uses 5M rows vs. 50M in prod | Mirror production data volume in staging |

---

## Best Practices

- Always test blue-green states under full expected load
- Use incremental shifts with pauses aligned to metric collection intervals
- Run emergency rollback drills monthly
- Enforce mandatory index reviews for any code introducing new queries
- Keep staging data within 10% of production scale

**Expected Timeline**:
- Deployment window: 45–60 minutes
- Rollback execution: ≤2 minutes
- Post-cutover observation: 30 minutes minimum

---

## Key Takeaways

1. **Connection pools must account for peak concurrency during dual-environment operation** — always size pools and DB limits for combined blue+green load.
2. **Missing indexes can cause catastrophic performance degradation at scale** — enforce pre-deployment indexing validation and query reviews.
3. **Staging environments must mirror production data volume** — 5M-row datasets won’t catch scalability issues present in 50M+ tables.
4. **Monitoring must include infrastructure-level metrics** — connection usage, query latency, and SLOs are critical for safe rollouts.
5. **Lessons must become process** — integrate remediation actions (e.g., checklist updates, index creation) directly into deployment pipelines.