```yaml
---
name: production-microservice-deployment
description: Production-ready guide for deploying a microservice using a blue-green deployment strategy, based on real-world execution and lessons learned.
version: 0.3.0
status: Evolving
---
```

# Production Microservice Deployment with Blue-Green Strategy

## Introduction

This guide provides a field-validated procedure for safely deploying a microservice in production using the blue-green deployment strategy. It is intended for use when minimizing downtime and enabling rapid rollback are critical. The steps and checks herein are derived from three iterative deployment attempts, incorporating observed failures and optimizations.

Use this guide during scheduled production releases where service continuity and observability are required.

---

## Deployment Context

- **Strategy**: Blue-green deployment via Kubernetes `Service` selector switch  
- **Environment**: Kubernetes (v1.25+), Helm-managed workloads, Istio ingress  
- **Goals**:
  - Zero-downtime deployment
  - Sub-5-minute rollback if failure detected
  - Full observability during transition
  - Minimal impact on downstream consumers

---

## Pre-Deployment Checklist

### Database
- [ ] **Verify schema compatibility** with new version — *Critical*  
  Run: `helm test db-checks --namespace=db`
- [ ] Confirm migration scripts are idempotent and version-tagged

### Monitoring & Observability
- [ ] **Ensure metrics endpoints are enabled** in new image — *Critical*  
  Check: `/metrics` returns 200 in staging
- [ ] Validate Prometheus scrape config includes new pod labels
- [ ] Set up dashboard panels for latency, error rate, and request volume per color

### Networking
- [ ] Confirm Istio virtual service routes do not override color selectors
- [ ] Verify readiness/liveness probes are tuned for startup time (new version may be slower)

### Rollback Readiness
- [ ] **Pre-stage rollback script** with known-good revision — *Critical*  
  Store: `rollback-v2.1.0.yaml` in secure location
- [ ] Confirm `kubectl` context points to production cluster

---

## Deployment Procedure

1. **Deploy Green Instance (inactive)**
   ```bash
   helm upgrade --install mysvc-green ./charts/microservice \
     --namespace services \
     --set replicaCount=3 \
     --set image.tag=v2.2.0 \
     --set service.name=mysvc-green
   ```

2. **Wait for Pod Readiness**
   ```bash
   kubectl wait --for=condition=ready pod -l app=mysvc,version=v2.2.0 -n services --timeout=180s
   ```

3. **Run Smoke Tests Against Green**
   ```bash
   curl -H "x-bypass-router: green" http://mysvc.prod.svc.cluster.local/health
   # Expected: 200 OK + "green", no errors in logs
   ```

4. **Switch Traffic: Blue → Green**
   Update service selector to point to green version:
   ```bash
   kubectl patch svc mysvc -n services -p '{"spec": {"selector": {"version": "v2.2.0"}}}'
   ```

5. **Monitor Transition (First 5 Minutes)**
   - Watch for:
     - Error rate > 1% (via Grafana or `kubectl logs`)
     - Latency increase > 2x baseline
     - Drop in request volume (consumer breakage)
   - Use:
     ```bash
     kubectl top pods -n services -l app=mysvc
     ```

6. **Confirm Stability**
   - Sustained health for 10 minutes
   - No alerts triggered
   - Tracing shows full request flow

---

## Rollback Procedure

### When to Roll Back
- HTTP 5xx error rate > 2% sustained over 2 minutes
- Latency P95 > 1.5x baseline for 3+ minutes
- Database connection pool exhaustion observed
- Downstream services report failures

### Rollback Steps
1. **Immediately reroute traffic to blue (known stable):**
   ```bash
   kubectl patch svc mysvc -n services -p '{"spec": {"selector": {"version": "v2.1.0"}}}'
   ```

2. **Verify blue instance health:**
   ```bash
   kubectl get pods -n services -l app=mysvc,version=v2.1.0
   ```

3. **Expected Recovery Time**: < 4 minutes from rollback initiation to full restoration.

---

## Common Pitfalls & Solutions

| Issue | Root Cause | Symptom | Solution |
|------|-----------|--------|----------|
| Green pods crash after deploy | Missing config map mount | CrashLoopBackOff in logs | Explicitly declare all configMaps in Helm values |
| Service selector fails to switch | Misaligned pod labels | No traffic to green | Double-check label selectors in deployment vs service |
| High latency post-switch | Cold cache in new service | P95 spikes at switchover | Warm caches via pre-load job before cutover |
| Rollback fails due to blue scale-down | Auto-scaler terminated old pods | No healthy blue pods | Keep blue instance alive for 15 min post-switch |

---

## Best Practices

- **Keep both blue and green active during monitoring window** (min 15 minutes)  
- **Automate smoke tests** — run post-deploy, pre-cutover  
- **Tag images immutably** — never reuse `latest`  
- **Time deployments outside peak hours** — target 02:00–04:00 UTC  
- **Expected timeline**:
  - Deploy green: 2 min
  - Wait & test: 3 min
  - Cutover: 1 min
  - Monitor: 10 min
  - Total: ~16 minutes

---

## Key Takeaways

1. **Label consistency is critical** — mismatched selectors cause silent failures.
2. **Never assume backward compatibility** — always verify DB/schema interoperability.
3. **Rollback must be faster than detection** — automate the switch.
4. **Observability starts before cutover** — monitor green *before* routing traffic.
5. **Human error is the largest risk** — use pre-checked scripts, not CLI guesswork.