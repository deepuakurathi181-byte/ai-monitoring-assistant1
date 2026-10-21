# User Manual — Prometheus & Grafana Monitoring Stack

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation & Setup](#2-installation--setup)
3. [Starting the Stack](#3-starting-the-stack)
4. [Using Prometheus](#4-using-prometheus)
5. [Using Grafana](#5-using-grafana)
6. [Monitoring Nginx](#6-monitoring-nginx)
7. [Understanding Node Exporter Metrics](#7-understanding-node-exporter-metrics)
8. [Alerting](#8-alerting)
9. [Adding Custom Scrape Targets](#9-adding-custom-scrape-targets)
10. [Maintenance & Troubleshooting](#10-maintenance--troubleshooting)

---

## 1. Prerequisites

Before you begin, ensure you have the following installed:

- **Docker** v20.10 or later — [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose** v2.0 or later — [Install Docker Compose](https://docs.docker.com/compose/install/)

Verify your installation:

```bash
docker --version
docker compose version
```

---

## 2. Installation & Setup

Clone the repository and navigate into the project directory:

```bash
git clone <repo-url>
cd prometheus-grafana-docker
```

No additional dependencies or configuration are required. The stack is ready to run out of the box.

---

## 3. Starting the Stack

### Start all services

```bash
docker compose up -d
```

This starts all five services in detached mode (background).

### Verify services are running

```bash
docker compose ps
```

You should see all containers in a `running` state:

| Container | Port |
|-----------|------|
| prometheus | 0.0.0.0:9090→9090 |
| grafana | 0.0.0.0:3000→3000 |
| nodeexporter | 0.0.0.0:9100→9100 |
| nginx | 0.0.0.0:8080→80 |
| nginxexporter | 0.0.0.0:9113→9113 |

### View logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f prometheus
```

### Stop the stack

```bash
docker compose down
```

---

## 4. Using Prometheus

### Access the UI

Open your browser and navigate to: **http://localhost:9090**

### Running Queries

1. Click the **Graph** tab in the top navigation.
2. Enter a PromQL expression in the query box. Examples:

| Query | Description |
|-------|-------------|
| `up` | Shows which targets are up (1) or down (0) |
| `node_cpu_seconds_total` | Total CPU seconds by mode |
| `rate(node_cpu_seconds_total{mode="idle"}[5m])` | Rate of idle CPU over 5 minutes |
| `node_memory_MemAvailable_bytes` | Available memory in bytes |
| `nginx_connections_active` | Current active Nginx connections |

3. Click **Execute** to run the query.
4. Switch between **Table** and **Graph** views to see results in different formats.

### Checking Targets

1. Navigate to **Status → Targets** in the top menu.
2. You will see three scrape jobs:
   - `prometheus` — self-monitoring
   - `node_exporter` — system metrics
   - `nginx` — Nginx metrics via the exporter
3. All targets should show a green **UP** state.

### Checking Configuration

Navigate to **Status → Configuration** to view the active Prometheus configuration.

---

## 5. Using Grafana

### First Login

1. Open your browser and navigate to: **http://localhost:3000**
2. Log in with the default credentials:
   - **Username**: `admin`
   - **Password**: `admin`
3. You will be prompted to change the password. You can skip this for development use.

### Adding Prometheus as a Data Source

1. Click the **gear icon** (⚙️) in the left sidebar → **Data Sources**.
2. Click **Add data source**.
3. Select **Prometheus**.
4. Set the URL to: `http://prometheus:9090`
5. Click **Save & Test**. You should see a green "Data source is working" message.

### Creating Your First Dashboard

1. Click the **+** icon in the left sidebar → **Dashboard**.
2. Click **Add visualization**.
3. Select your Prometheus data source.
4. In the query editor, enter a PromQL expression, for example:
   ```
   rate(node_cpu_seconds_total{mode="idle"}[5m])
   ```
5. Choose a visualization type (Time series, Gauge, Stat, etc.).
6. Click **Apply** to add the panel.
7. Click the **save icon** (💾) to save your dashboard.

### Importing Pre-built Dashboards

Grafana has a library of community dashboards. To import one:

1. Click **+** → **Import**.
2. Enter a dashboard ID from [Grafana Dashboards](https://grafana.com/grafana/dashboards/). Recommended:
   - **1860** — Node Exporter Full
   - **12708** — Nginx Overview
3. Click **Load**.
4. Select your Prometheus data source.
5. Click **Import**.

### Dashboard Tips

- Use **variables** to create dynamic dashboards (e.g., filter by instance).
- Set **auto-refresh** intervals (top-right dropdown) to keep dashboards live.
- Use **annotations** to mark deployment events on graphs.

---

## 6. Monitoring Nginx

### Accessing Nginx

The Nginx web server is available at: **http://localhost:8080**

It serves the default Nginx welcome page.

### Nginx Metrics

The Nginx Exporter scrapes the `stub_status` module and exposes metrics at: **http://localhost:9113/metrics**

Key metrics available:

| Metric | Description |
|--------|-------------|
| `nginx_connections_active` | Current active connections |
| `nginx_connections_accepted` | Total accepted connections |
| `nginx_connections_handled` | Total handled connections |
| `nginx_connections_reading` | Connections reading request |
| `nginx_connections_writing` | Connections writing response |
| `nginx_connections_waiting` | Idle connections |
| `nginx_http_requests_total` | Total HTTP requests |

### Generating Test Traffic

To see metrics change, generate some traffic to Nginx:

```bash
# Single request
curl http://localhost:8080

# Multiple requests
for i in $(seq 1 100); do curl -s http://localhost:8080 > /dev/null; done
```

Then query `nginx_http_requests_total` in Prometheus to see the count increase.

---

## 7. Understanding Node Exporter Metrics

Node Exporter provides system-level metrics from the host machine. Access raw metrics at: **http://localhost:9100/metrics**

### Common Metrics

| Category | Example Metric | Description |
|----------|---------------|-------------|
| CPU | `node_cpu_seconds_total` | CPU time by mode (idle, user, system) |
| Memory | `node_memory_MemTotal_bytes` | Total system memory |
| Memory | `node_memory_MemAvailable_bytes` | Available memory |
| Disk | `node_filesystem_avail_bytes` | Available disk space |
| Disk | `node_disk_io_time_seconds_total` | Disk I/O time |
| Network | `node_network_receive_bytes_total` | Bytes received |
| Network | `node_network_transmit_bytes_total` | Bytes transmitted |

### Useful PromQL Queries

```promql
# CPU usage percentage
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage percentage
(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100

# Disk usage percentage
(1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100

# Network throughput (bytes/sec received)
rate(node_network_receive_bytes_total[5m])
```

---

## 8. Alerting

### Current Alert Rules

The stack includes an example alert in `prometheus/alerts.yml`:

- **HighCPUUsage**: Triggers when idle CPU drops below 20% for 1 minute.

### Enabling Alert Rules in Prometheus

To activate the alert rules, add the following to `prometheus/prometheus.yml` under the `global` section:

```yaml
rule_files:
  - /etc/prometheus/alerts.yml
```

Then mount the alerts file in `docker-compose.yml` under the prometheus service volumes:

```yaml
volumes:
  - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
  - ./prometheus/alerts.yml:/etc/prometheus/alerts.yml
```

Restart Prometheus:

```bash
docker compose restart prometheus
```

### Viewing Alerts

1. Open Prometheus at http://localhost:9090.
2. Navigate to **Alerts** in the top menu.
3. You will see alert rules and their current state (inactive, pending, or firing).

### Adding New Alert Rules

Edit `prometheus/alerts.yml` and add new rules under the `groups` section:

```yaml
groups:
  - name: example_alerts
    rules:
      - alert: HighMemoryUsage
        expr: (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) > 0.9
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Memory usage exceeds 90%"
```

---

## 9. Adding Custom Scrape Targets

To monitor additional services, edit `prometheus/prometheus.yml` and add a new job:

```yaml
scrape_configs:
  # ... existing jobs ...

  - job_name: 'my_custom_app'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

Then reload Prometheus:

```bash
docker compose restart prometheus
```

### Custom Metrics Example

The `html-app/metrics.txt` file shows the format for custom Prometheus metrics:

```
# HELP myapp_requests_total Total requests to HTML app
# TYPE myapp_requests_total counter
myapp_requests_total 5
```

Your application needs to expose an HTTP endpoint (typically `/metrics`) that returns text in this format.

---

## 10. Maintenance & Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| Container won't start | Check logs: `docker compose logs <service>` |
| Target shows DOWN in Prometheus | Verify the container is running and the port is correct |
| Grafana shows "No data" | Ensure the data source URL is `http://prometheus:9090` (not localhost) |
| Port conflict | Change the host port in `docker-compose.yml` (e.g., `9091:9090`) |
| Nginx exporter fails | Ensure Nginx container is running first (check `depends_on`) |

### Restarting Individual Services

```bash
docker compose restart prometheus
docker compose restart grafana
```

### Updating Images

```bash
docker compose pull
docker compose up -d
```

### Resetting Grafana

To reset Grafana to a clean state (removes all dashboards and settings):

```bash
docker compose down -v
docker compose up -d
```

### Checking Resource Usage

```bash
docker stats
```

### Backing Up Grafana Data

Grafana data is stored in a named Docker volume (`grafana-data`). To back it up:

```bash
docker run --rm -v grafana-data:/data -v $(pwd):/backup alpine tar czf /backup/grafana-backup.tar.gz /data
```

### Persistent Data

- **Grafana**: Dashboards and settings are persisted in the `grafana-data` Docker volume.
- **Prometheus**: Metrics data is stored inside the container. Add a volume mount to persist it:

```yaml
prometheus:
  volumes:
    - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    - prometheus-data:/prometheus
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start stack | `docker compose up -d` |
| Stop stack | `docker compose down` |
| View logs | `docker compose logs -f` |
| Restart service | `docker compose restart <service>` |
| Check status | `docker compose ps` |
| Update images | `docker compose pull && docker compose up -d` |
| Reset everything | `docker compose down -v && docker compose up -d` |

| Service | URL |
|---------|-----|
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| Nginx | http://localhost:8080 |
| Node Exporter Metrics | http://localhost:9100/metrics |
| Nginx Exporter Metrics | http://localhost:9113/metrics |
