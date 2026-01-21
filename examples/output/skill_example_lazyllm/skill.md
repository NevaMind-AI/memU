```yaml
---
name: production-microservice-deployment
description: Production-ready guide for deploying microservices using blue-green strategy, based on real-world failure and success patterns.
version: 1.0.0
status: Production-Ready
---
```

# Production Microservice Deployment with Blue-Green Strategy

## Introduction

This guide provides a battle-tested, step-by-step procedure for safely deploying a microservice to production using the blue-green deployment strategy. It is designed for use when minimizing downtime and risk during version upgrades is critical. The procedures, checks, and thresholds are derived from actual deployment attempts—two failures and one successful rollout—of the `recommendation-service` v2.5.0.

Use this guide for any stateful or database-dependent microservice where traffic shifting must account for infrastructure capacity, performance under load, and safe rollback readiness.

---

## Deployment Context

- **Strategy**: Blue-green deployment with incremental traffic shifting (10% → 100%)
- **Environment**: Kubernetes-based production cluster with external PostgreSQL database
- **Traffic Management**: Service mesh (e.g., Istio) or ingress controller managing traffic split
- **Goals**:
  - Zero-downtime cutover
  - Validation of performance under real user load
  - Immediate rollback capability if SLOs are violated
  - Full operational hygiene post-cutover

---

## Pre-Deployment Checklist

> ✅ All items must be verified before initiating deployment.

### Database
- [CRITICAL] Confirm database `max_connections` supports combined blue + green load  
  → *Increase from 100 to 250 if necessary*
- [CRITICAL] Validate all new query patterns have required indexes  
  → *Ensure `idx_user_segment` exists on `user_segment` column*
- [CRITICAL] Verify staging dataset size mirrors production (e.g., 50M rows) to detect scalability issues
- Adjust per-pod connection pool size to prevent exhaustion under dual-environment traffic

### Monitoring & Alerts
- [CRITICAL] Ensure monitoring is enabled for:
  - Database active connections
  - Query latency (P99) for key endpoints
  - HTTP error rates and request volume
- Confirm alerts are configured to trigger on:
  - P99 latency > 500ms (SLO threshold)
  - Connection pool saturation (>80% of max)
  - Error rate > 1%

### Testing & Validation
- [CRITICAL] Complete full-capacity integration test simulating blue-green state
- Run production-scale load test with realistic query patterns
- Review all database schema changes and indexing decisions in PR

### Operational Readiness
- Confirm rollback path is tested and executable within 2 minutes
- Verify deployment checklist is integrated into CI/CD pipeline gates
- Ensure logging and tracing are aligned across both environments

---

## Deployment Procedure

1. **Deploy Green Environment**
   ```bash
   kubectl apply -f recommendation-service-v2.5.0.yaml
   ```
   Wait for all pods to reach `Running` and pass readiness probes.

2. **Initialize Traffic at 10%**
   ```bash
   istioctl traffic-split set --namespace prod --green-weight 10 --blue-weight 90
   ```
   Monitor for 5 minutes:
   - Confirm no spike in errors or latency
   - Check database connections: must remain <40% of max

3. **Shift to 25% Traffic**
   ```bash
   istioctl traffic-split set --namespace prod --green-weight 25
   ```
   Monitor for 7 minutes:
   - P99 latency ≤ 500ms
   - Error rate ≤ 0.5%
   - No alert triggers

4. **Proceed to 50%, Then 75%**
   ```bash
   istioctl traffic-split set --namespace prod --green-weight 50
   # After 10 min stable →
   istioctl traffic-split set --namespace prod --green-weight 75
   ```
   At each stage:
   - Watch for query degradation
   - Confirm connection usage remains under 70%

5. **Cutover to 100%**
   ```bash
   istioctl traffic-split set --namespace prod --green-weight 100
   ```
   Final validation:
   - Sustained load: ≥1500 req/s
   - Average latency ≤ 140ms, P99 ≤ 250ms
   - Error rate ≤ 0.3%
   - DB connection usage ≤ 50%

6. **Post-Cutover Actions**
   - Decommission blue environment
     ```bash
     kubectl delete -f recommendation-service-v2.4.0.yaml
     ```
   - Activate continuous monitoring dashboard
   - Record deployment outcome and lessons in runbook

---

## Rollback Procedure

### Trigger Conditions (Rollback Immediately If):
- P99 latency > 500ms for >2 minutes
- Error rate > 1% sustained over 3 minutes
- Database connection errors observed
- Any alert on connection pool saturation

### Execute Rollback
```bash
istioctl traffic-split set --namespace prod --blue-weight 100 --green-weight 0
```
→ Revert traffic fully to stable blue version.

### Expected Outcome
- Service stability restored within **≤1.5 minutes**
- Error rate returns to baseline
- Latency normalizes to pre-deployment levels

Post-rollback:
- Preserve logs and metrics for root cause analysis
- Halt further deployments until remediation complete

---

## Common Pitfalls & Solutions

| Issue | Symptom | Root Cause | Solution |
|------|--------|-----------|----------|
| Database connection exhaustion | Errors during 50% shift, "too many connections" logs | `max_connections=100` insufficient for dual environments | Increase limit to 250; reduce per-pod pool size |
| Latency spike at 75% traffic | P99 jumps to 780ms, SLO breach | Missing index on `user_segment`, full table scan on 50M rows | Create `idx_user_segment`; validate all queries |
| No early warning | No alerts before rollback | Missing monitoring on connection count and query latency | Add alerts for DB connections (>80%) and P99 (>400ms) |
| Staging environment false confidence | Performance fine in staging | Data volume too small (5M vs 50M) | Mirror production data scale in staging |

---

## Best Practices

- **Traffic Shifting**: Use conservative increments (10% → 25% → 50% → 75% → 100%) with monitoring pauses
- **Validation Window**: Minimum 5–10 minutes per stage depending on traffic ramp
- **Monitoring Focus**: Prioritize database-level metrics and end-to-end latency
- **Timeline**: Allow 30–40 minutes for full cutover including observation periods
- **Checklist Enforcement**: Integrate pre-deployment validations into CI/CD approval gates

---

## Key Takeaways

1. **Database capacity must account for peak deployment states** — blue-green requires double the normal load capacity; validate `max_connections` and pool sizing upfront.
2. **Performance testing must use production-scale datasets** — staging with 10% data volume will not catch full-table-scan bottlenecks.
3. **Indexing is a deployment gate** — every new query pattern must be reviewed and indexed before release.
4. **Monitoring must cover infrastructure dependencies** — track database connections, query latency, and pool utilization as first-class signals.
5. **Safe deployment is procedural** — gradual traffic shifts, staged validation, and rollback readiness enable recovery from unforeseen issues without user impact.