# Prometheus & Grafana Monitoring Stack

A Docker Compose monitoring stack: **Prometheus** for metrics, **Alertmanager** for alert routing,
and **Grafana** (auto-provisioned with a datasource + dashboard) for visualization. It monitors
host metrics via Node Exporter and web-server metrics via an Nginx exporter — everything wired
together and working on `docker compose up`, no manual clicks.

## Architecture

```
┌────────────┐      ┌────────────────┐      ┌──────────────┐
│  Grafana   │─────▶│  Prometheus    │─────▶│ Alertmanager │
│  :3000     │      │  :9090         │      │  :9093       │
│ (provisioned)     │  + alert rules │      │ (routing)    │
└────────────┘      └───────┬────────┘      └──────────────┘
                            │ scrapes
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
        ┌──────────┐  ┌───────────┐  ┌──────────┐
        │  Node    │  │  Nginx    │  │Prometheus│
        │ Exporter │  │ Exporter  │  │  (self)  │
        │  :9100   │  │  :9113    │  │  :9090   │
        └──────────┘  └─────┬─────┘  └──────────┘
                            │ /stub_status
                       ┌────▼────┐
                       │  Nginx  │
                       │  :8080  │
                       └─────────┘
```

## What's included

- **Prometheus** — scrapes all targets, loads alert rules, forwards to Alertmanager
- **Alertmanager** — alert routing with grouping, inhibition, and a ready-to-fill Slack example
- **Grafana** — **auto-provisioned** Prometheus datasource + a "Node Overview" dashboard
  (CPU / memory / disk / targets up) — no manual setup
- **Node Exporter** — host CPU, memory, disk, network metrics
- **Nginx + Nginx Exporter** — a sample web server with a properly configured `stub_status`
  endpoint that the exporter actually scrapes
- **Persistent storage** for both Prometheus TSDB and Grafana

## Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| Prometheus | `prom/prometheus:latest` | 9090 | Metrics collection, storage, rule evaluation |
| Alertmanager | `prom/alertmanager:latest` | 9093 | Alert routing & notifications |
| Grafana | `grafana/grafana:latest` | 3000 | Dashboards (auto-provisioned) |
| Node Exporter | `prom/node-exporter:latest` | 9100 | Host/system metrics |
| Nginx | `nginx:latest` | 8080 | Sample monitored web server |
| Nginx Exporter | `nginx/nginx-prometheus-exporter` | 9113 | Exports Nginx metrics |

## Alert Rules

Defined in `prometheus/alerts.yml`, loaded by Prometheus, routed through Alertmanager:

| Alert | Condition | Severity |
|-------|-----------|----------|
| `HighCPUUsage` | CPU > 80% for 5m | warning |
| `HighMemoryUsage` | Available memory < 10% for 5m | warning |
| `LowDiskSpace` | Root FS < 15% free for 5m | warning |
| `TargetDown` | Any scrape target down for 1m | critical |

> The previous CPU alert used a raw counter (`node_cpu_seconds_total < 20`), which never evaluates
> as a percentage. It's now a proper rate-based expression.

## Quick Start

```bash
cp .env.example .env        # set your Grafana admin password
docker compose up -d
docker compose ps
```

Access:
- **Grafana**: http://localhost:3000 — open the **Node Overview** dashboard (already provisioned)
- **Prometheus**: http://localhost:9090 — check Status → Targets and Alerts
- **Alertmanager**: http://localhost:9093
- **Nginx**: http://localhost:8080

## Wiring up real notifications

Edit `alertmanager/alertmanager.yml` and uncomment the `slack_configs` block (or add email /
PagerDuty), set your webhook, then:

```bash
docker compose restart alertmanager
```

## Project Structure

```
prometheus-grafana-docker/
├── docker-compose.yml
├── .env.example
├── prometheus/
│   ├── prometheus.yml          # scrape config + rule_files + alerting
│   └── alerts.yml              # alert rules
├── alertmanager/
│   └── alertmanager.yml        # routing, grouping, inhibition
├── grafana/
│   └── provisioning/
│       ├── datasources/prometheus.yml
│       └── dashboards/
│           ├── dashboards.yml
│           └── node-overview.json
├── nginx/
│   └── nginx.conf              # serves sample page + /stub_status
├── html-app/
│   └── index.html
└── README.md
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+)

## Stopping

```bash
docker compose down        # stop containers
docker compose down -v     # also remove volumes (deletes Grafana + Prometheus data)
```

## License

MIT


---

<div align="center">

### Built by

**Durrell Gemuh** - Founder @ NextGen Playground | DevOps & Cloud Infrastructure Engineer | AWS Community Builder

[![Portfolio](https://img.shields.io/badge/Portfolio-durrellgemuh.com-000?style=flat-square&logo=vercel)](https://durrellgemuh.com)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-durrello-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/durrello/)
[![Dev.to](https://img.shields.io/badge/Dev.to-durrello-0A0A0A?style=flat-square&logo=devdotto)](https://dev.to/durrello)
[![X](https://img.shields.io/badge/X-@durrelloo-000?style=flat-square&logo=x)](https://x.com/durrelloo)
[![GitHub](https://img.shields.io/badge/GitHub-durrello-181717?style=flat-square&logo=github)](https://github.com/durrello)
[![Email](https://img.shields.io/badge/Email-durrell.gemuh.a@gmail.com-EA4335?style=flat-square&logo=gmail)](mailto:durrell.gemuh.a@gmail.com)

---

⭐ **Star this repo** if you found it useful - it helps others discover it!

</div>
