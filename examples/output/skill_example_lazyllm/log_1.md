```yaml
---
name: production-microservice-deployment
description: Production-ready guide for deploying microservices using a blue-green strategy, based on real incident learnings to prevent connection exhaustion and ensure safe rollouts.
version: 0.1.0
status: Evolving
---
```

# Production Microservice Deployment with Blue-Green Strategy

## Introduction

This guide provides a practical, experience-driven procedure for safely deploying microservices in production using the blue-green deployment strategy. It is intended for use during versioned service updates where minimizing user impact and enabling rapid rollback are critical. The steps and checks herein are derived from a real-world failure involving database connection exhaustion during traffic shift.

Use this guide when:
- Deploying stateful services that maintain database connections
- Employing blue-green deployments in Kubernetes or similar orchestration platforms
- Ensuring infrastructure capacity aligns with peak deployment load

---

## Deployment Context

- **Strategy**: Blue-green deployment  
- **Environment**: Production, containerized (e.g., Kubernetes), PostgreSQL backend  
- **Traffic Shift**: Gradual (e.g., 0% → 50% → 100%) via service mesh or ingress controller  
- **Goal**: Zero-downtime deployment with full rollback capability within 2 minutes if anomalies occur  
- **Critical Risk**: Resource contention during dual-environment operation (blue + green)

---

## Pre-Deployment Checklist

Ensure all items are verified **before** initiating deployment.

### Database
- [ ] **Validate `max_connections` limit supports combined blue and green load** *(Critical)*  
  > Ensure total expected connections from both environments ≤ database limit  
- [ ] **Adjust per-pod connection pool size** *(Critical)*  
  > Scale down individual pod pools to prevent oversubscription during overlap  

### Monitoring & Alerts
- [ ] **Enable monitoring of active database connections** *(Critical)*  
  > Track metric: `pg_stat_database.numbackends` or equivalent  
- [ ] **Set up alert thresholds for connection pool usage (>80%)** *(Critical)*  
  > Trigger alerts during deployment phase  
- [ ] Confirm end-to-end metrics pipeline is active (Prometheus/Grafana or equivalent)

### Testing & Validation
- [ ] **Perform full-capacity load test under dual-environment conditions** *(Critical)*  
  > Simulate blue + green traffic concurrently  
- [ ] Verify no performance degradation or connection errors at peak load  
- [ ] Confirm rollback mechanism works in staging

---

## Deployment Procedure

> ⚠️ Monitor all systems continuously during execution.

1. **Deploy Green Environment**
   ```bash
   kubectl apply -f recommendation-service-v2.5.0-green.yaml
   ```
   - Wait for all pods to reach `Running` and pass readiness probes
   - Confirm logs show clean startup with no connection errors

2. **Verify Green Service Health**
   - Access `/health` endpoint directly (bypassing router)
   - Confirm database connectivity and query responsiveness
   - Check metrics dashboard: baseline connection count established

3. **Begin Traffic Shift (0% → 50%)**
   ```bash
   kubectl apply -f traffic-shift-50pct.yaml
   ```
   - Update canary weight or virtual service routing rules accordingly
   - Allow 2–3 minutes for traffic stabilization

4. **Monitor During 50% Shift**
   - Observe:
     - Error rates (must remain <0.5%)
     - Latency (P95 < 300ms)
     - **Active database connections** (must not exceed 80% of max)
   - If any threshold breached → **Initiate Rollback Immediately**

5. **Proceed to 100% Traffic (if stable)**
   ```bash
   kubectl apply -f traffic-shift-100pct.yaml
   ```
   - Redirect all traffic to green
   - Decommission blue environment after confirmation:
     ```bash
     kubectl delete -f recommendation-service-v2.4.0-blue.yaml
     ```

---

## Rollback Procedure

### When to Rollback
Immediate rollback required if:
- Error rate exceeds **1% for 60 seconds**
- Latency P95 > **1s for 2+ minutes**
- Database connections ≥ **90% of max_connections**
- Emergency signal from SRE team

### Execute Rollback
1. Revert traffic to blue:
   ```bash
   kubectl apply -f traffic-shift-100pct-blue.yaml
   ```
2. Confirm traffic rerouted within **60 seconds**
3. Terminate green pods:
   ```bash
   kubectl delete -f recommendation-service-v2.5.0-green.yaml
   ```
4. Validate blue service stability via health checks and dashboards

✅ **Expected Recovery Time**: ≤ 1.5 minutes  
✅ **Impact Window**: ~1.5 minutes at <5% error rate (historically observed)

---

## Common Pitfalls & Solutions

| Issue | Symptom | Root Cause | Solution |
|------|--------|-----------|----------|
| Database connection exhaustion | Errors during 50% shift, timeouts | `max_connections=100` too low; per-pod pools oversized | Increase DB limit; reduce per-pod pool size |
| No early warning | Failure detected too late | Missing alerts on connection usage | Implement proactive monitoring at 80% threshold |
| Undetected bottleneck | Load test passed but failed live | Test did not simulate dual blue-green load | Add full-capacity integration testing pre-deploy |

---

## Best Practices

- **Always size infrastructure for peak deployment states**, not just steady-state
- **Test under realistic overlap conditions** — blue and green running simultaneously
- **Integrate checklist items into CI/CD gates** — block deployment if validations missing
- **Expect rollout duration**: ~8–12 minutes (including verification windows)
- **Rollback drills**: Conduct quarterly in staging

---

## Key Takeaways

1. **Connection pools must be sized for combined blue and green load** — never assume steady-state capacity suffices.
2. **Infrastructure limits (e.g., `max_connections`) must be validated pre-deployment** — silent failures occur when shared resources are exhausted.
3. **Proactive monitoring of key database metrics is non-negotiable** — lack of alerts delays detection and increases blast radius.
4. **Full-capacity and dual-environment testing is mandatory** — unit and single-instance tests do not reveal integration bottlenecks.
5. **Remediation actions must become standard checks** — update checklists and automate where possible to prevent recurrence.