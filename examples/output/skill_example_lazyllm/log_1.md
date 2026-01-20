```yaml
---
name: production-microservice-deployment
description: Production-ready guide for deploying a microservice using blue-green deployment strategy with monitoring, rollback safeguards, and lessons from real deployment attempts.
version: 0.1.0
status: Evolving
---
```

# Production Microservice Deployment with Blue-Green Strategy

## Introduction

This guide provides a battle-tested procedure for safely deploying a microservice to production using the blue-green deployment strategy. It is intended for use when minimizing downtime and enabling rapid rollback are critical. The steps reflect lessons learned from active deployment attempts and focus on practical execution in cloud-native environments using Kubernetes and CI/CD pipelines.

Use this guide during scheduled maintenance windows for major version updates or breaking changes where user impact must be contained.

---

## Deployment Context

- **Strategy**: Blue-green deployment  
- **Environment**: Kubernetes (EKS), AWS-hosted, Helm-managed services  
- **Traffic Management**: Istio service mesh with weighted routing  
- **Primary Goals**:
  - Zero-downtime deployment
  - Immediate rollback capability
  - Controlled traffic shift with observability
  - Validation of health before full cutover

---

## Pre-Deployment Checklist

### 🔧 Infrastructure & Configuration
- [x] New (green) environment provisioned and stable (`kubectl get nodes --selector=env=green`)  
- [x] Helm chart version tagged and immutable (e.g., `my-service-1.4.0`)  
- [x] ConfigMaps and Secrets verified for green environment (no dev defaults)  

### 🛢️ Database
- [x] Schema migrations are backward-compatible **(Critical)**  
- [x] Migration scripts tested in staging with production-like data  
- [ ] Downtime-free migration path confirmed (if applicable)  

### 📊 Monitoring & Observability
- [x] Prometheus metrics endpoints exposed on new pods  
- [x] Grafana dashboards updated to include green service instance  
- [x] Alertmanager rules cover deployment-phase anomalies (latency, error rate spikes)  
- [x] Distributed tracing (Jaeger) enabled and sampled at 100% during cutover  

### 🧪 Validation Readiness
- [x] Smoke test suite available and passing against staging  
- [x] Canaries configured to hit green service pre-cutover  
- [x] Rollback image tagged and accessible in registry (`v1.3.9-rollback`)  

---

## Deployment Procedure

> ⏱️ Estimated execution time: 18 minutes

1. **Deploy Green Service**
   ```bash
   helm upgrade my-service-green ./charts/my-service \
     --namespace production \
     --set environment=green \
     --set image.tag=v1.4.0 \
     --install
   ```

2. **Wait for Pod Readiness**
   ```bash
   kubectl wait --for=condition=ready pod -l app=my-service,environment=green -n production --timeout=5m
   ```
   - ✅ Monitoring Point: All pods report `Ready` status within 5 minutes  
   - ❌ If pending > 3 minutes: check resource quotas and node autoscaling

3. **Run Smoke Tests Against Green**
   ```bash
   ./scripts/smoke-test.sh --target https://api-green.example.com
   ```
   - ✅ Expected: All 7 tests pass, response time < 800ms  
   - ❌ Fail: Halt deployment, investigate logs and traces

4. **Shift 5% Traffic to Green (Canary)**
   Apply Istio traffic split:
   ```yaml
   apiVersion: networking.istio.io/v1alpha3
   kind: VirtualService
   metadata:
     name: my-service-route
   spec:
     hosts:
       - api.example.com
     http:
     - route:
       - destination:
           host: my-service-blue.production.svc.cluster.local
         weight: 95
       - destination:
           host: my-service-green.production.svc.cluster.local
         weight: 5
   ```
   ```bash
   kubectl apply -f virtualservice-split.yaml
   ```

5. **Monitor Key Metrics (5 minutes)**
   - Error rate (goal: < 0.5%)  
   - P95 latency (< 1.2s)  
   - Request volume consistency  
   - Check Jaeger traces for failed spans

6. **Shift 100% Traffic to Green**
   Update weights:
   ```yaml
   - weight: 0    # blue
   - weight: 100  # green
   ```
   ```bash
   kubectl apply -f virtualservice-split.yaml
   ```

7. **Verify Full Cutover**
   ```bash
   curl -H "Host: api.example.com" http://ingress/status | grep "version=1.4.0"
   ```

8. **Decommission Blue (After 1 hour)**
   ```bash
   helm uninstall my-service-blue --namespace production
   ```

---

## Rollback Procedure

### When to Roll Back

Roll back immediately if any of the following occur:
- Error rate > 5% sustained over 2 minutes  
- Latency P95 > 3s for 3+ minutes  
- Database connection pool exhaustion observed  
- Smoke test failure at any stage

### Steps

1. **Revert Traffic to Blue**
   ```bash
   kubectl patch virtualservice my-service-route --patch '
   spec:
     http:
     - route:
       - destination:
           host: my-service-blue.production.svc.cluster.local
         weight: 100
       - destination:
           host: my-service-green.production.svc.cluster.local
         weight: 0'
   ```

2. **Confirm Health of Blue Service**
   ```bash
   kubectl get pods -l app=my-service,environment=blue -n production
   ```
   - Ensure all replicas are running and ready

3. **Trigger Alert Acknowledgment**
   - Manually acknowledge firing alerts in Alertmanager  
   - Notify #prod-alerts: `@team Rollback initiated – green service degraded`

4. **Expected Recovery Time**: < 90 seconds from rollback initiation

---

## Common Pitfalls & Solutions

| Issue | Root Cause | Symptom | Solution |
|------|-----------|--------|---------|
| Green pods stuck in `Pending` | Node autoscaler not triggered | No new pods scheduled | Manually scale node group or reduce CPU requests temporarily |
| Sudden 503s after cutover | Misconfigured readiness probe | Pods accept traffic before DB connection | Add `initialDelaySeconds: 30` to probe config |
| Rollback fails due to blue already uninstalled | Premature cleanup | 503s across the board | Reinstall blue via Helm restore from last release revision |
| Traces missing in Jaeger | Sampling rate too low | Incomplete trace visibility | Set `tracing.sample-rate: 100` during deployment window |

---

## Best Practices

- Always keep the previous version deployable and tracked (tagged in Helm repository)  
- Run smoke tests against green **before** any traffic shift  
- Use immutable image tags — never `latest`  
- Schedule deployments during low-traffic periods (e.g., 02:00–04:00 local ops time)  
- Coordinate with SRE team for alert suspension/sensitivity adjustment during window

> ✅ Expected timeline:  
> - Preparation: 30 min  
> - Execution: 18 min  
> - Observation: 60 min  
> - Total: ~110 minutes

---

## Key Takeaways

1. **Backward-compatible schema changes are non-negotiable** — even minor migrations can break old instances during rollback.  
2. **Readiness probes must reflect actual service dependencies**, especially database and cache connectivity.  
3. **Never decommission the blue stack until post-cutover stability is confirmed** — rollback without it is impossible.  
4. **Observability must be pre-wired** — ad-hoc dashboard creation delays incident response.  
5. **Automated smoke tests are essential** — manual validation is unreliable under pressure.