```markdown
---
name: production-microservice-deployment
description: Production-ready guide for deploying a microservice using blue-green deployment strategy with zero-downtime, validated monitoring, and rapid rollback capability.
version: 1.0.0
status: Production-Ready
---

# Production Microservice Deployment with Blue-Green Strategy

## Introduction

This guide provides a battle-tested procedure for safely deploying a microservice to production using the blue-green deployment strategy. It ensures zero downtime, enables immediate rollback on failure, and integrates real-time validation via observability tools. Use this guide for any stateless microservice upgrade in Kubernetes-based environments where service continuity is critical.

## Deployment Context

- **Strategy**: Blue-green deployment  
- **Environment**: Kubernetes (EKS), AWS infrastructure, Istio service mesh  
- **Goals**:
  - Zero downtime during deployment
  - Traffic switch within 30 seconds
  - Full observability during cutover
  - Rollback within 2 minutes if thresholds breached
  - Minimal blast radius

## Pre-Deployment Checklist

### Infrastructure & Configuration
- [x] **(Critical)** New blue environment (v2) pods are running and ready (`kubectl get pods -l app=<service>,version=v2`)
- [x] **(Critical)** All secrets and configmaps mounted correctly in v2 pods
- [x] Readiness and liveness probes configured and passing for v2

### Database
- [x] **(Critical)** Schema migrations are backward-compatible and applied *before* deployment
- [x] No pending data backfills or long-running jobs blocking cutover

### Monitoring & Observability
- [x] **(Critical)** Prometheus metrics endpoints exposed and scraped for v2
- [x] Grafana dashboards updated to include v2 version filtering
- [x] Alertmanager rules evaluate both v1 and v2 independently
- [x] Distributed tracing (Jaeger) enabled for service mesh traffic

### Traffic Management
- [x] Istio VirtualService configured with named subsets (`blue`/`green`)  
- [x] Initial traffic weight set to 0% for new version (blue)

### Validation
- [x] Smoke test suite available and passes against staging
- [x] Synthetic health check endpoint (`/live` and `/ready`) accessible and returning 200

## Deployment Procedure

1. **Deploy v2 Artifacts**
   ```bash
   kubectl apply -f deploy/v2-deployment.yaml
   kubectl apply -f deploy/service.yaml
   ```

2. **Wait for Pod Readiness**
   ```bash
   kubectl wait --for=condition=ready pod -l app=<service>,version=v2 --timeout=180s
   ```

3. **Apply Istio Traffic Shift (100% to Blue)**
   ```bash
   kubectl apply -f istio/virtualservice-blue.yaml
   ```
   > `virtualservice-blue.yaml` sets traffic weight: blue=100, green=0

4. **Monitor Key Metrics (First 5 Minutes)**
   - HTTP 5xx rate < 0.5%
   - P99 latency < 800ms
   - Error logs per second < 2
   - Circuit breaker open count = 0
   - Use:
     ```bash
     kubectl top pods -l app=<service>,version=v2
     ```

5. **Run Smoke Tests Against Live Endpoint**
   ```bash
   ./scripts/smoke-test.sh https://<service>/health-check
   ```

6. **Confirm Stability (10-Minute Hold)**
   - Watch dashboards continuously
   - Verify no alerts triggered
   - Confirm user transaction traces succeed

7. **Promote v2 to Production Label**
   ```bash
   kubectl label deployment <service>-v2 env=prod --overwrite
   ```

## Rollback Procedure

### When to Rollback
Rollback immediately if **any** of the following occur:
- HTTP 5xx rate ≥ 5% sustained over 2 minutes
- P99 latency > 2s for 3 consecutive minutes
- Smoke test fails
- Critical alert fires (e.g., DB connection pool exhaustion)

### Steps

1. **Revert Traffic to Green (v1)**
   ```bash
   kubectl apply -f istio/virtualservice-green.yaml
   ```
   > Switches 100% traffic back to stable v1

2. **Verify Rollback Success**
   ```bash
   kubectl get virtualservice <service> -o jsonpath='{.spec.http[0].route}'
   # Output should show green subset at 100%
   ```

3. **Monitor Recovery**
   - Expected recovery time: ≤ 2 minutes
   - Confirm metrics return to baseline
   - Ensure no cascading failures in dependent services

## Common Pitfalls & Solutions

| Issue | Root Cause | Symptom | Solution |
|------|-----------|--------|----------|
| 5xx spike after cutover | Missing CORS headers in v2 | Clients blocked | Revert; add `Access-Control-Allow-Origin` header |
| Pods stuck in `CrashLoopBackOff` | Incorrect secret mount path | Container exits with code 1 | Check `kubectl describe pod`, verify volumeMount paths match |
| Latency degradation | Unindexed query introduced | DB CPU > 85%, slow traces | Rollback; add index; retest in staging |
| Partial rollout due to mislabeled pods | Version label typo in YAML | Some traffic routed incorrectly | Fix labels; redeploy; validate with `kubectl get pods -L version` |

## Best Practices

- **Always test blue-green failover weekly** in pre-prod using automation
- **Use canary first**: Route 1% of production traffic to v2 before full blue-green
- **Automate smoke tests** as part of CI/CD pipeline
- **Keep both versions running for 1 hour post-cutover** before scaling down v1
- **Expected timeline**:
  - Deployment: 4 minutes
  - Monitoring window: 10 minutes
  - Total execution: ≤ 15 minutes

## Key Takeaways

1. Backward-compatible schema changes are non-negotiable — always deploy DB changes ahead of application updates.
2. Misconfigured Istio subsets cause partial outages — validate routing rules with dry-run checks.
3. Real-time observability is essential — without live dashboards, you’re flying blind during cutover.
4. Automated smoke tests catch integration issues missed in staging.
5. Rollback speed determines incident impact — practice it like a fire drill.
```