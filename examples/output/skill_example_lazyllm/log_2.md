```markdown
---
name: production-microservice-deployment
description: Production-ready guide for deploying microservices using a blue-green deployment strategy with real-world lessons learned from partial deployment attempts.
version: 0.2.0
status: Evolving
---

# Production Microservice Deployment with Blue-Green Strategy

## Introduction

This guide provides a practical, step-by-step procedure for safely deploying a microservice in production using the blue-green deployment pattern. It is intended for use when minimizing downtime and enabling rapid rollback are critical. The procedures, checks, and pitfalls documented here are derived from two prior deployment attempts (1 successful phase, 1 partial failure), capturing actionable insights from real operational experience.

Use this guide during scheduled production releases where traffic switching, data consistency, and observability are required.

## Deployment Context

- **Strategy**: Blue-green deployment using Kubernetes `Service` selector switch
- **Environment**: Kubernetes 1.25+ (EKS), AWS RDS backend, Prometheus/Grafana/Loki stack
- **Goals**:
  - Zero-downtime cutover
  - Sub-5-minute rollback if thresholds breached
  - Full observability during transition
  - Data schema compatibility across versions

## Pre-Deployment Checklist

### Infrastructure & Configuration
- [ ] **(Critical)** New green environment (v2) pods are running and passing readiness/liveness probes  
- [ ] **(Critical)** Database schema changes (if any) are backward compatible with both v1 (blue) and v2 (green)
- [ ] Green service endpoint (`svc-green`) exists and routes to v2 pods
- [ ] Blue service endpoint (`svc-blue`) remains active and unchanged

### Monitoring & Observability
- [ ] **(Critical)** Prometheus metrics for request rate, error rate, and latency are available per version (via `version` label)
- [ ] Loki logs are tagged with `app_version` and searchable by deployment color
- [ ] Grafana dashboard loaded with real-time view of both blue and green services

### Traffic & Networking
- [ ] Current production traffic is routed through `svc-production` → `version=blue`
- [ ] `svc-production` selector can be patched atomically to switch to `version=green`
- [ ] DNS TTLs and client-side caching do not interfere with immediate routing control

## Deployment Procedure

1. **Deploy v2 (Green) Pods**
   ```bash
   kubectl apply -f deployment-v2.yaml
   ```
   - Wait until all pods are `Running` and pass readiness checks:
     ```bash
     kubectl get pods -l app=my-microservice,version=v2
     ```

2. **Validate Green Service Internally**
   - Send test traffic via port-forward:
     ```bash
     kubectl port-forward svc/svc-green 8080:80 &
     curl http://localhost:8080/health
     ```
   - Confirm logs show `version=v2` and no startup errors.

3. **Switch Traffic to Green**
   ```bash
   kubectl patch svc svc-production -p '{"spec": {"selector": {"version": "v2"}}}'
   ```
   - This switches all traffic from blue to green atomically.

4. **Monitor Transition (First 5 Minutes)**
   - **Monitoring Points**:
     - Error rate (target: <0.5%)
     - P95 latency (<200ms)
     - Request volume parity (match pre-switch levels)
     - Pod restarts or crashes in v2
   - Use Grafana dashboard to compare v1 (historical) vs v2 (live) metrics.

5. **Stabilization Check**
   - After 5 minutes of stable performance:
     - Confirm no alerts triggered
     - Verify business logic via synthetic transaction
     - Log success: `Deployment v2 now serving production traffic`

## Rollback Procedure

### When to Roll Back
Roll back immediately if **any** of the following occur within 10 minutes post-cutover:
- Error rate > 2% sustained over 2 minutes
- Latency P95 > 800ms for >3 minutes
- Database connection pool saturation in v2
- Any critical alert from monitoring system

### Rollback Command
```bash
kubectl patch svc svc-production -p '{"spec": {"selector": {"version": "v1"}}}'
```

- Expected recovery time: **< 3 minutes** (limited by kube-proxy sync interval)
- Post-rollback:
  - Confirm v1 pods absorb traffic (check metrics)
  - Preserve v2 logs for root cause analysis
  - Trigger incident review if rollback executed

## Common Pitfalls & Solutions

| Issue | Root Cause | Symptom | Solution |
|------|-----------|--------|----------|
| 503 errors after cutover | Misconfigured readiness probe in v2 | Pods running but not receiving traffic | Fix `/health` endpoint logic; re-roll v2 before switching |
| DB lock contention | v2 introduced long-lived transaction | Increased latency and connection pool exhaustion | Revert code change; apply statement-level timeout |
| Logs missing version tag | Incorrect label injection in init container | Inability to filter v2 logs in Loki | Patch DaemonSet to inject `app_version` env var |
| Partial traffic switch | Sticky sessions at LB layer | Mixed v1/v2 traces in Jaeger | Disable session affinity on ALB before deployment |

## Best Practices

- **Test Selector Patch Locally**: Validate `kubectl patch` syntax in staging first
- **Pre-warm caches**: If applicable, trigger cache population in v2 before cutover
- **Atomic Switch Only**: Never use weighted routing unless A/B testing is goal
- **Timeline Expectations**:
  - v2 rollout: 2–3 minutes
  - Validation: 2 minutes
  - Cutover + monitoring: 5–10 minutes
  - Total window: ≤15 minutes

## Key Takeaways

1. **Selector-based switching is reliable only if labels and selectors are rigorously tested pre-deploy**
2. **Backward-compatible database schema changes are non-negotiable—v1 must tolerate v2 writes**
3. **Real-time observability by version is critical—without it, rollback decisions are blind**
4. **A failed deployment is acceptable; a slow or uncontrolled rollback is not**
5. **Always preserve pre-cutover state—never scale down blue until green is proven stable**
```