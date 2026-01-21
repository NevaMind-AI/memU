```yaml
---
name: production-microservice-deployment
description: Production-ready guide for deploying microservices using blue-green strategy with validated infrastructure, monitoring, and rollback safeguards.
version: 0.3.0
status: Evolving
---
```

# Production Microservice Deployment with Blue-Green Strategy

This guide provides a battle-tested procedure for safely deploying microservices in production using the blue-green deployment strategy. It is intended for use when zero-downtime rollouts, risk mitigation under real traffic, and rapid recovery are required. The steps are derived from real deployment outcomes across three iterations, including two failures and one successful cutover.

Use this guide when:
- Deploying versioned services with stateless workloads
- Database schema and query performance have been pre-validated
- Monitoring, alerting, and rollback tooling are active
- Traffic shifting is managed via service mesh or load balancer

---

## Deployment Context

**Strategy**: Blue-green deployment with incremental traffic shift (10% → 100%) over 36 minutes  
**Environment**: Kubernetes-based platform with service mesh routing control  
**Target Service**: `recommendation-service` v2.5.0  
**Goals**:
- Achieve zero-downtime cutover
- Validate performance under real production load
- Stay within SLOs (P99 latency < 500ms, error rate < 0.5%)
- Maintain database stability under dual-environment load

---

## Pre-Deployment Checklist

### ✅ Database
- [CRITICAL] Confirm database `max_connections` supports combined blue/green load (minimum 250 for this service)  
- [CRITICAL] Verify all new queries have appropriate indexes; validate existence of `idx_user_segment`  
- [ ] Ensure per-pod connection pool size is adjusted to prevent exhaustion (e.g., HikariCP `maximumPoolSize`)  
- [ ] Confirm staging dataset mirrors production scale (≥50M rows for key tables)

### ✅ Monitoring & Alerting
- [CRITICAL] Active alerts on database connection usage (>80% threshold)  
- [CRITICAL] Query latency monitoring enabled for high-impact endpoints  
- [ ] P99 latency, error rate, and request volume dashboards accessible in real time  
- [ ] Rollback trigger thresholds defined (see Rollback Procedure)

### ✅ Infrastructure
- [ ] New environment (green) deployed and health-checked  
- [ ] Blue environment remains fully operational and stable  
- [ ] Routing controller ready for incremental traffic shifts  

### ✅ Testing & Validation
- [CRITICAL] Full-capacity integration test completed under dual-blue-green load  
- [ ] Performance testing executed with production-scale data volume  
- [ ] Indexing and query plan review performed for all new database access patterns  

---

## Deployment Procedure

1. **Deploy Green Environment**
   ```bash
   kubectl apply -f recommendation-service-v2.5.0.yaml
   ```
   Wait for all pods to reach `Running` and pass readiness checks.

2. **Validate Health**
   - Confirm logs show clean startup
   - Verify `/health` endpoint returns 200
   - Check metrics: no errors, CPU/MEM within expected range

3. **Begin Incremental Traffic Shift**
   Apply traffic weights via service mesh (example using Istio):
   ```bash
   # 10% to green
   istioctl traffic-shift set --to green --weight 10
   sleep 300  # Monitor for 5 minutes
   ```

4. **Monitor at Each Stage**
   After each shift, wait 5–10 minutes and verify:
   - P99 latency < 500ms
   - Error rate < 0.5%
   - Database active connections < 80% of max
   - No alerts firing

   Continue shifting:
   ```bash
   istioctl traffic-shift set --to green --weight 25
   sleep 300

   istioctl traffic-shift set --to green --weight 50
   sleep 600

   istioctl traffic-shift set --to green --weight 75
   sleep 600

   istioctl traffic-shift set --to green --weight 100
   ```

5. **Cutover Complete**
   - Confirm full traffic on green (1500 req/s observed in success case)
   - Average latency: 136ms, P99: 216ms, error rate: 0.2%

---

## Rollback Procedure

**Trigger Rollback If**:
- P99 latency > 500ms for >2 minutes
- Error rate > 0.5% sustained
- Database connection usage hits 90%
- Any critical alert fires during shift

**Execute Immediate Rollback**:
```bash
istioctl traffic-shift set --to blue --weight 100
```

**Expected Recovery Time**: ≤1.5 minutes  
**Post-Rollback Actions**:
- Preserve logs and metrics for root cause analysis
- Disable green environment if not needed for debugging
- Update incident log with timestamp, metrics, and rollback reason

---

## Common Pitfalls & Solutions

| Issue | Symptom | Root Cause | Solution |
|------|--------|-----------|----------|
| Database connection exhaustion | 5xx errors during 50% shift, "too many connections" logs | `max_connections=100` insufficient for dual environments | Increase limit to 250; reduce per-pod pool size |
| Latency spike at 75% traffic | P99 jumps to 780ms, SLO violation | Missing `idx_user_segment`, full table scan on 50M-row table | Create index; test with production-scale data |
| No alert on connection usage | Failure undetected until user impact | Missing monitoring on DB connection pool | Add Prometheus/Grafana alert at 80% threshold |
| Staging test passed but prod failed | No issues in staging, failure in production | Staging dataset too small (5M vs 50M rows) | Mirror production data scale in staging |

---

## Best Practices

- **Traffic Shifting**: Use conservative increments (10% → 100%) over ≥30 minutes to allow observation
- **Monitoring**: Focus on P99 latency, error rate, and database connection count—these were leading indicators
- **Testing**: Always run performance tests with production-scale datasets and query patterns
- **Validation**: Enforce mandatory pre-deployment checklist including indexing and capacity review
- **Timeline**: Allow 36+ minutes for full rollout with monitoring pauses; rollback completes in <2 minutes

---

## Key Takeaways

1. **Database capacity must account for peak deployment states**—blue-green requires double the normal load capacity.
2. **Production-scale testing is non-negotiable**—small datasets hide scalability bugs like missing indexes.
3. **Connection pools and infrastructure limits must be proactively monitored and alerted**—silent exhaustion causes outages.
4. **Incremental traffic shifting with staged validation enables safe rollout**—real-load testing catches what synthetic tests miss.
5. **Lessons must become checklists**—operationalize fixes (index reviews, pool sizing) to prevent recurrence.