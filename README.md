# Self-Healing Observability Platform

A production-grade microservices observability platform that demonstrates **failure detection**, **automated alerting**, **distributed tracing**, and **self-healing auto-recovery** — the core SRE skill set.

Built with Spring Boot, Prometheus, Grafana, Jaeger, Alertmanager, and custom Python scripts for autonomous container recovery.

---

## Architecture

```
                         ┌─────────────────────┐
                         │   Load Generator     │
                         │  (Python script)     │
                         └─────────┬───────────┘
                                   │ POST /orders
                                   ▼
                         ┌─────────────────────┐
                         │   Orders Service     │
                         │     (port 8081)      │
                         │    [Orchestrator]    │
                         └────┬───────────┬────┘
                              │           │
              POST /inventory/reserve     POST /payments/charge
                              │           │
                    ┌─────────▼───┐   ┌───▼─────────┐
                    │  Inventory  │   │  Payments    │
                    │  Service    │   │  Service     │
                    │ (port 8082) │   │ (port 8083)  │
                    │ [Failure    │   │ [Timeout     │
                    │  Injector]  │   │  Injector]   │
                    └──────┬──────┘   └──────┬───────┘
                           │                 │
                           └────────┬────────┘
                                    ▼
                          ┌──────────────────┐
                          │   PostgreSQL 15   │
                          │   (port 5432)     │
                          │  ordersdb         │
                          │  inventorydb      │
                          │  paymentsdb       │
                          └──────────────────┘

    ┌─────────────────── Observability Layer ───────────────────┐
    │                                                           │
    │  Prometheus ──► Alertmanager ──► Slack                    │
    │  (port 9090)    (port 9093)                               │
    │       │                                                   │
    │       ▼                                                   │
    │   Grafana (port 3000)     Jaeger (port 16686)             │
    │   [4-panel dashboard]     [Distributed traces]            │
    │                                                           │
    └───────────────────────────────────────────────────────────┘

    ┌──────────────── Self-Healing Layer ───────────────────────┐
    │                                                           │
    │  self_healer.py ── polls /actuator/health every 30s       │
    │                    auto-restarts after 2 consecutive       │
    │                    failures via `docker restart`           │
    │                                                           │
    └───────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Version |
|---|---|---|
| Language | Java | 17 |
| Framework | Spring Boot | 3.2.5 |
| Build | Maven | 3.9.x |
| Database | PostgreSQL | 15 |
| Metrics | Micrometer + Prometheus | latest |
| Tracing | OpenTelemetry + Jaeger | OTel 2.4.0-alpha / Jaeger 1.55 |
| Logging | Logback + logstash-logback-encoder | 7.4 |
| Dashboards | Grafana | 10.2.0 |
| Alerting | Prometheus Alertmanager | 0.26.0 |
| Containers | Docker Compose | v3.8 |
| Scripts | Python 3, Bash | 3.8+ |

---

## What Each Service Does

### Orders Service (Orchestrator) — Port 8081

Receives order requests, saves as `PENDING`, calls Inventory to reserve stock, calls Payments to charge, then marks the order `CONFIRMED` or `FAILED`.

- **Endpoints:** `POST /orders`, `GET /orders/{id}`, `GET /orders`
- **Failure behavior:** If Inventory or Payments is down/slow, the order is marked `FAILED`. RestTemplate has a 5-second read timeout.

### Inventory Service (Failure Injector) — Port 8082

Manages product stock (5 products seeded: PROD-001 to PROD-005, qty 100 each). Randomly injects:
- **Latency:** 0–2000ms sleep on every request
- **Failures:** 20% chance of `RuntimeException` (configurable)

- **Endpoints:** `POST /inventory/reserve`, `GET /inventory/{productId}`, `GET /inventory`

### Payments Service (Timeout Injector) — Port 8083

Processes payments. Randomly injects:
- **Timeouts:** 30% chance of 3-second sleep (approaches the 5s timeout on orders-service)
- **Failures:** 15% chance of `RuntimeException`

- **Endpoints:** `POST /payments/charge`, `GET /payments/{id}`, `GET /payments/order/{orderId}`

---

## Observability Features

### Metrics (Prometheus + Micrometer)
- All services expose `/actuator/prometheus` with HTTP request metrics, percentile histograms, and custom counters
- Custom metrics: `orders_created_total`, `inventory_reserve_total`, `inventory_failure_simulated_total`, `payments_charge_total`, `payments_timeout_simulated_total`

### Distributed Tracing (OpenTelemetry + Jaeger)
- Auto-instruments HTTP requests, RestTemplate calls, and JDBC queries
- 100% trace sampling — every request generates a trace
- Trace context propagates across all 3 services (a single order request shows spans from orders → inventory → payments)

### Structured JSON Logging
- Every log line is JSON with fields: `timestamp`, `level`, `service`, `traceId`, `spanId`, `message`
- Trace IDs are injected via OpenTelemetry's SLF4J MDC integration

### Alerting (Prometheus Rules + Alertmanager)

| Alert | Condition | Severity |
|---|---|---|
| **HighErrorRate** | 5xx rate > 5% for 1 minute | critical |
| **HighLatency** | p95 > 500ms for 1 minute | warning |
| **ServiceDown** | `up == 0` for 30 seconds | critical |

Alerts route to Slack via Alertmanager with formatted messages including summary, severity, and description.

### Grafana Dashboard

Auto-provisioned "Microservices Overview" dashboard with 4 panels:

| Panel | Type | What It Shows |
|---|---|---|
| Request Throughput | Time series | Requests/sec per service |
| Error Rate (5xx) | Gauge | Overall 5xx percentage — green/yellow/red thresholds |
| p95 Latency | Time series | 95th percentile response time with 500ms threshold line |
| Service Health | Stat | UP (green) / DOWN (red) per service |

### Self-Healing

Python script (`self_healer.py`) that:
1. Polls `/actuator/health` on all 3 services every 30 seconds
2. Tracks consecutive failures per service
3. After 2 consecutive failures, runs `docker restart <container>`
4. Logs all actions as structured JSON

---

## Prerequisites

- **Docker** and **Docker Compose** installed
- **Python 3.8+** (for scripts — uses only stdlib, no pip install needed)
- Ports available: 3000, 4317, 4318, 5433, 8081, 8082, 8083, 9090, 9093, 16686

---

## Quick Start

### Step 1: Clone the Repository

```bash
git clone https://github.com/RohitKumar2306/self-healing-observability-platform.git
cd self-healing-observability-platform
```

### Step 2: Start All Containers

```bash
docker-compose up --build -d
```

This builds 3 Spring Boot services from source (multi-stage Docker builds) and starts all 8 containers. First build takes 3–5 minutes for Maven dependency downloads.

**Expected output:**

```
[+] Building 180.2s (32/32) FINISHED
[+] Running 8/8
 ✔ Container postgres           Healthy
 ✔ Container jaeger             Started
 ✔ Container prometheus         Started
 ✔ Container alertmanager       Started
 ✔ Container grafana            Started
 ✔ Container orders-service     Started
 ✔ Container inventory-service  Started
 ✔ Container payments-service   Started
```

### Step 3: Verify All Services Are Running

```bash
docker-compose ps
```

<!-- Screenshot: docker-compose ps output showing all 8 containers running -->

Wait ~30 seconds for Spring Boot services to initialize, then verify health:

```bash
curl localhost:8081/actuator/health
curl localhost:8082/actuator/health
curl localhost:8083/actuator/health
```

**Expected output for each:**
```json
{"status":"UP"}
```

<!-- Screenshot: curl health check outputs -->

### Step 4: Verify Observability Stack

```bash
# Prometheus targets
curl -s localhost:9090/api/v1/targets | python3 -m json.tool | head -20

# Grafana health
curl -s localhost:3000/api/health

# Jaeger services
curl -s "localhost:16686/api/services" | python3 -m json.tool
```

---

## Execution Guide

### Generate Traffic

Open a terminal and start the load generator:

```bash
python3 scripts/load_generator.py
```

**Expected output:**

```
[2026-03-30T10:00:00+00:00] Load generator started
  Target: http://localhost:8081/orders
  Interval: 2s
  Summary every 30 requests

[OK ] #0001 | 201 |   842ms | product=PROD-003 qty=2 | order=a1b2c3d4-... status=CONFIRMED
[FAIL] #0002 | 500 |  1205ms | product=PROD-001 qty=1 | order=e5f6g7h8-... status=FAILED
[OK ] #0003 | 201 |   342ms | product=PROD-005 qty=3 | order=i9j0k1l2-... status=CONFIRMED
[OK ] #0004 | 201 |  3142ms | product=PROD-002 qty=1 | order=m3n4o5p6-... status=CONFIRMED
...

============================================================
  SUMMARY (last 30 requests)
  Success: 18/30 (60.0%)
  Failed:  12/30 (40.0%)
  Errors:  0/30
  Avg latency: 1247ms
  Min latency: 203ms
  Max latency: 5012ms
============================================================
```

<!-- Screenshot: load generator terminal output -->

The ~60% success rate is expected — inventory fails 20% of requests, payments times out 30% and fails 15%.

### Start the Self-Healer

Open a second terminal:

```bash
python3 scripts/self_healer.py
```

**Expected output (all healthy):**

```json
{"timestamp": "2026-03-30T10:01:00+00:00", "level": "INFO", "service": "self-healer", "target": "all", "message": "Self-healer started", "interval": 30, "threshold": 2}
{"timestamp": "2026-03-30T10:01:00+00:00", "level": "INFO", "service": "self-healer", "target": "orders-service", "message": "Health check passed", "status": "UP"}
{"timestamp": "2026-03-30T10:01:00+00:00", "level": "INFO", "service": "self-healer", "target": "inventory-service", "message": "Health check passed", "status": "UP"}
{"timestamp": "2026-03-30T10:01:00+00:00", "level": "INFO", "service": "self-healer", "target": "payments-service", "message": "Health check passed", "status": "UP"}
```

<!-- Screenshot: self-healer terminal with healthy checks -->

### Simulate Failures

Open a third terminal:

```bash
bash scripts/simulate_failure.sh
```

**Menu:**

```
  Self-Healing Observability Platform
  Failure Simulator

===========================================
  Failure Simulation Menu
===========================================
  1) Stop inventory-service
  2) Stop payments-service
  3) Stop postgres
  4) Restart all services
  5) Set inventory failure rate to 80%
  6) Reset inventory failure rate to 20%
  7) Show container status
  0) Exit
===========================================
  Choose an option:
```

<!-- Screenshot: simulate_failure.sh menu -->

---

## Demo Scenarios

### Scenario 1: Stop a Service and Watch Self-Healing

**Steps:**

1. Ensure load generator and self-healer are running
2. In the simulate_failure menu, press `1` to stop inventory-service

**What happens:**

| Time | Event |
|---|---|
| T+0s | inventory-service container stops |
| T+2s | Load generator starts showing all requests as FAILED (connection refused) |
| T+15s | Prometheus scrape detects `up == 0`, ServiceDown alert goes to PENDING |
| T+30s | Self-healer detects first health check failure (consecutive_failures = 1) |
| T+45s | ServiceDown alert fires as ACTIVE |
| T+60s | Self-healer detects second failure (consecutive_failures = 2), runs `docker restart inventory-service` |
| T+90s | inventory-service comes back up, self-healer logs "Service recovered" |
| T+90s+ | Load generator starts showing CONFIRMED orders again |

**Self-healer output during recovery:**

```json
{"timestamp": "...", "level": "WARN", "target": "inventory-service", "message": "Health check failed", "consecutive_failures": 1}
{"timestamp": "...", "level": "WARN", "target": "inventory-service", "message": "Health check failed", "consecutive_failures": 2}
{"timestamp": "...", "level": "ERROR", "target": "inventory-service", "message": "Failure threshold reached, triggering restart", "consecutive_failures": 2}
{"timestamp": "...", "level": "WARN", "target": "inventory-service", "message": "Restarting container"}
{"timestamp": "...", "level": "INFO", "target": "inventory-service", "message": "Container restarted successfully"}
{"timestamp": "...", "level": "INFO", "target": "inventory-service", "message": "Service recovered", "previous_failures": 2}
```

<!-- Screenshot: self-healer detecting failure and auto-restarting -->

<!-- Screenshot: Grafana dashboard showing the dip and recovery -->

### Scenario 2: Increase Error Rate to 80%

**Steps:**

1. In the simulate_failure menu, press `5` to set inventory failure rate to 80%
2. Watch Grafana error rate gauge turn red

**What happens:**

- ~80% of orders fail at inventory reservation
- Grafana Error Rate gauge goes from yellow to **red** (>5% threshold)
- Prometheus HighErrorRate alert fires after 1 minute
- Alertmanager sends notification to Slack

<!-- Screenshot: Grafana error rate gauge in red -->

<!-- Screenshot: Prometheus alerts page showing HighErrorRate firing -->

**Reset:**

Press `6` to reset to 20%, then watch metrics return to normal.

### Scenario 3: Stop PostgreSQL

**Steps:**

1. Press `3` to stop postgres

**What happens:**

- All 3 services lose their database connection
- All health checks fail
- 3 ServiceDown alerts fire simultaneously
- Self-healer restarts all 3 services (but they'll keep failing until postgres comes back)

Press `4` to restart all services including postgres.

<!-- Screenshot: all services DOWN in Grafana Service Health panel -->

---

## Observability UI Walkthrough

### Grafana Dashboard

**URL:** http://localhost:3000 — Login: `admin` / `admin`

Navigate to Dashboards → "Microservices Overview"

<!-- Screenshot: full Grafana dashboard with all 4 panels -->

**Panels explained:**

1. **Request Throughput** (top-left) — Shows requests/second per service. When a service is stopped, its line drops to zero.

2. **Error Rate (5xx)** (top-right) — Gauge showing overall 5xx percentage. Green = healthy (<2%), Yellow = degraded (2-5%), Red = critical (>5%).

3. **p95 Latency** (bottom-left) — 95th percentile response time. The red horizontal line at 500ms is the alert threshold. Payments-service timeouts cause spikes above this line.

4. **Service Health** (bottom-right) — Shows UP (green) or DOWN (red) for each service. Instantly reflects when a container is stopped.

### Jaeger Traces

**URL:** http://localhost:16686

Select service `orders-service` and click "Find Traces".

<!-- Screenshot: Jaeger trace list -->

Click on a trace to see the full call chain:

```
orders-service: POST /orders (1.2s)
  ├── inventory-service: POST /inventory/reserve (800ms)
  └── payments-service: POST /payments/charge (400ms)
```

<!-- Screenshot: Jaeger trace detail showing 3 spans -->

Failed traces show error tags on the failing span, making it easy to identify which downstream service caused the failure.

### Prometheus

**URL:** http://localhost:9090

**Useful queries:**

```promql
# Request rate per service
sum by (job)(rate(http_server_requests_seconds_count[1m]))

# Error rate percentage
sum(rate(http_server_requests_seconds_count{status=~"5.."}[1m])) / sum(rate(http_server_requests_seconds_count[1m])) * 100

# p95 latency
histogram_quantile(0.95, sum by (job, le)(rate(http_server_requests_seconds_bucket[1m])))

# Service up/down
up{job=~"orders-service|inventory-service|payments-service"}
```

Navigate to **Alerts** tab to see alert states (inactive/pending/firing).

<!-- Screenshot: Prometheus Alerts tab -->

### Alertmanager

**URL:** http://localhost:9093

Shows currently firing alerts with labels and annotations.

<!-- Screenshot: Alertmanager UI with active alerts -->

---

## Project Structure

```
self-healing-observability-platform/
├── docker-compose.yml              ← 8 containers (3 services + 5 infra)
├── services/
│   ├── orders-service/             ← Orchestrator (port 8081)
│   ├── inventory-service/          ← Failure injector (port 8082)
│   └── payments-service/           ← Timeout injector (port 8083)
├── observability/
│   ├── prometheus/
│   │   ├── prometheus.yml          ← Scrape config (15s interval)
│   │   └── alert_rules.yml        ← 3 alert rules
│   └── grafana/provisioning/
│       ├── datasources/            ← Prometheus data source
│       └── dashboards/             ← Auto-provisioned dashboard
├── alerting/alertmanager/
│   └── alertmanager.yml            ← Slack routing
└── scripts/
    ├── self_healer.py              ← Health monitor + auto-restart
    ├── load_generator.py           ← Traffic generator
    ├── simulate_failure.sh         ← Chaos testing menu
    └── init-databases.sql          ← PostgreSQL DB initialization
```

---

## Port Reference

| Service | Port | URL |
|---|---|---|
| Orders API | 8081 | http://localhost:8081 |
| Inventory API | 8082 | http://localhost:8082 |
| Payments API | 8083 | http://localhost:8083 |
| PostgreSQL | 5433 | `psql -h localhost -p 5433 -U postgres` |
| Grafana | 3000 | http://localhost:3000 (admin/admin) |
| Jaeger | 16686 | http://localhost:16686 |
| Prometheus | 9090 | http://localhost:9090 |
| Alertmanager | 9093 | http://localhost:9093 |

---

## Configuration

All failure simulation parameters are configurable via environment variables in `docker-compose.yml`:

| Variable | Default | Description |
|---|---|---|
| `INVENTORY_LATENCY_ENABLED` | true | Enable random latency injection |
| `INVENTORY_MAX_LATENCY_MS` | 2000 | Max simulated latency (ms) |
| `INVENTORY_FAILURE_RATE` | 0.20 | Probability of simulated failure (0.0–1.0) |
| `PAYMENTS_TIMEOUT_ENABLED` | true | Enable timeout injection |
| `PAYMENTS_TIMEOUT_MS` | 3000 | Simulated timeout duration (ms) |
| `PAYMENTS_TIMEOUT_RATE` | 0.30 | Probability of timeout (0.0–1.0) |
| `PAYMENTS_FAILURE_RATE` | 0.15 | Probability of payment failure (0.0–1.0) |
| `SLACK_WEBHOOK_URL` | placeholder | Slack incoming webhook for alerts |

---

## Cleanup

```bash
# Stop all containers
docker-compose down

# Stop and remove volumes (deletes database data)
docker-compose down -v
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Separate databases per service | Microservices best practice — no shared schema coupling |
| `@Version` on InventoryItem | Optimistic locking prevents race conditions on concurrent stock reservations |
| RestTemplate with 5s timeout | Prevents orders-service from hanging indefinitely when payments simulate 3s timeouts |
| Structured JSON logging with traceId | Enables log correlation across services — search by traceId to follow a request through all 3 services |
| Python stdlib-only scripts | Zero dependencies — works on any machine with Python 3 installed |
| Multi-stage Docker builds | Keeps runtime images small (~200MB JRE-only instead of ~800MB with full JDK + Maven) |
| 100% trace sampling | Demo project — in production you'd use probabilistic sampling |

---

## Author

**Rohit Kumar Chintamani**

Portfolio project targeting DevOps / SRE / Backend Engineering roles.