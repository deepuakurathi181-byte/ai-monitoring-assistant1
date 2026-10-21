
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any
from fastapi.middleware.cors import CORSMiddleware
import logging
import requests

app = FastAPI(title="AI Monitoring Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-monitoring-assistant")

# Service configuration
PROMETHEUS_URL = "http://prometheus:9090"
OLLAMA_URL = "http://host.docker.internal:11434/api/chat"
MODEL = "llama3.2:3b"


class Alert(BaseModel):
    alert_name: str
    status: str = "firing"
    description: str = "No description provided"


def query_prometheus(query: str):
    """Execute a PromQL query against Prometheus."""

    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "success":
            raise HTTPException(
                status_code=502,
                detail="Prometheus returned an unsuccessful query",
            )

        return data["data"]["result"]

    except requests.RequestException as exc:
        logger.exception("Prometheus query failed")
        raise HTTPException(
            status_code=502,
            detail=f"Unable to query Prometheus: {exc}",
        )


def collect_monitoring_context():
    """Collect current target health and CPU metrics."""

    target_results = query_prometheus("up")

    targets = [
        {
            "instance": item["metric"].get(
                "instance", "unknown"
            ),
            "job": item["metric"].get(
                "job", "unknown"
            ),
            "up": item["value"][1] == "1",
        }
        for item in target_results
    ]

    cpu_query = (
        '100 * (1 - avg by (instance) '
        '(rate(node_cpu_seconds_total{mode="idle"}[5m])))'
    )

    cpu_results = query_prometheus(cpu_query)

    cpu_usage = [
        {
            "instance": item["metric"].get(
                "instance", "unknown"
            ),
            "cpu_usage_percent": round(
                float(item["value"][1]), 2
            ),
        }
        for item in cpu_results
    ]

    return {
        "targets": targets,
        "target_count": len(targets),
        "targets_up": sum(
            1 for target in targets if target["up"]
        ),
        "targets_down": sum(
            1 for target in targets if not target["up"]
        ),
        "cpu_usage_percent": cpu_usage,
    }


def analyze_with_ollama(
    alert_name: str,
    status: str,
    description: str,
    monitoring_context: dict[str, Any],
    alert_details: dict[str, Any] | None = None,
):
    """Analyze an alert using supplied Alertmanager and Prometheus data."""

    alert_details = alert_details or {}

    prompt = f"""
You are an evidence-based infrastructure monitoring assistant.

Analyze the alert using only the information supplied below.

ALERT INFORMATION
Name: {alert_name}
Status: {status}
Description: {description}
Labels: {alert_details.get("labels", {})}
Annotations: {alert_details.get("annotations", {})}
Generator URL: {alert_details.get("generatorURL") or "Not available"}

CURRENT PROMETHEUS MONITORING DATA
{monitoring_context}

Provide your analysis using these sections:

1. OBSERVED FACTS
- Report only facts explicitly present in the supplied data.
- State current CPU usage and target health only when available.
- Distinguish the alert's firing status from independently
  verified current conditions.
- Do not assume the current metric value is the value that
  originally triggered the alert.

2. ALERT VALIDATION
- Compare the alert description and available threshold
  information with the current metrics.
- If values or thresholds are missing, say so.
- Flag discrepancies without assuming either value is wrong.
- Do not claim the alert expression or duration was verified
  unless the relevant evidence is supplied.
- Remember that current metrics and alert evaluation values
  may differ because of timing, aggregation, or instance selection.

3. POSSIBLE CAUSES
- List plausible causes relevant to the alert.
- Explain what supplied evidence supports each hypothesis.
- Never present a hypothesis as a confirmed root cause.

4. TROUBLESHOOTING STEPS
- Recommend prioritized, read-only checks.
- Identify relevant metrics, logs, processes, and alert rules.
- Do not claim that checks have already been performed.

5. MISSING EVIDENCE
- List additional data needed to confirm the cause.

RULES
- Never invent metrics, values, thresholds, logs, or observations.
- If information is missing, say:
  "Not available in the supplied data."
- A healthy monitoring target does not prove that the host is healthy.
- Do not assume an exporter is the source of a host performance issue.
- Do not treat an alert status alone as proof of current CPU usage.
- Do not execute remediation or change infrastructure.
- Keep the analysis clear and concise.
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "stream": False,
            },
            timeout=120,
        )

        response.raise_for_status()
        result = response.json()

        return result["message"]["content"]

    except requests.RequestException as exc:
        logger.exception("Ollama request failed")
        raise HTTPException(
            status_code=502,
            detail=f"Unable to reach Ollama: {exc}",
        )

    except (KeyError, ValueError, TypeError) as exc:
        logger.exception("Unexpected Ollama response")
        raise HTTPException(
            status_code=502,
            detail=f"Unexpected response from Ollama: {exc}",
        )


@app.get("/")
def home():
    return {
        "message": "AI Monitoring Assistant is running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/metrics")
def get_metrics():
    """Return monitoring information collected from Prometheus."""

    return collect_monitoring_context()


@app.post("/analyze")
def analyze_alert(alert: Alert):
    """Manually analyze an alert through the API."""

    monitoring_context = collect_monitoring_context()

    ai_analysis = analyze_with_ollama(
        alert_name=alert.alert_name,
        status=alert.status,
        description=alert.description,
        monitoring_context=monitoring_context,
    )

    return {
        "alert": alert.alert_name,
        "status": alert.status,
        "monitoring_context": monitoring_context,
        "ai_analysis": ai_analysis,
    }


@app.post("/webhook")
def receive_alertmanager_webhook(
    payload: dict[str, Any],
):
    """Receive Alertmanager webhook notifications."""

    alerts = payload.get("alerts", [])

    if not isinstance(alerts, list):
        raise HTTPException(
            status_code=400,
            detail="'alerts' must be a list",
        )

    if not alerts:
        return {
            "message": (
                "Webhook received, but no alerts were included"
            ),
            "results": [],
        }

    results = []

    for alert_data in alerts:
        if not isinstance(alert_data, dict):
            results.append({
                "error": "Invalid alert entry; expected an object",
            })
            continue

        labels = alert_data.get("labels") or {}
        annotations = alert_data.get("annotations") or {}

        if not isinstance(labels, dict):
            labels = {}

        if not isinstance(annotations, dict):
            annotations = {}

        alert_name = labels.get(
            "alertname",
            "UnknownAlert",
        )

        status = alert_data.get(
            "status",
            payload.get("status", "unknown"),
        )

        description = (
            annotations.get("description")
            or annotations.get("summary")
            or "No description provided by Alertmanager"
        )

        # Preserve the original alert context for AI analysis.
        alert_details = {
            "labels": labels,
            "annotations": annotations,
            "generatorURL": alert_data.get("generatorURL"),
        }

        logger.info(
            "Received Alertmanager alert: name=%s status=%s",
            alert_name,
            status,
        )

        # Acknowledge resolved alerts without running AI analysis.
        if status == "resolved":
            results.append({
                "alert": alert_name,
                "status": status,
                "message": (
                    "Resolved alert acknowledged; "
                    "AI analysis skipped"
                ),
            })
            continue

        try:
            monitoring_context = collect_monitoring_context()

            ai_analysis = analyze_with_ollama(
                alert_name=alert_name,
                status=status,
                description=description,
                monitoring_context=monitoring_context,
                alert_details=alert_details,
            )

            logger.info(
                "AI analysis completed for alert: %s",
                alert_name,
            )

            results.append({
                "alert": alert_name,
                "status": status,
                "alert_details": alert_details,
                "monitoring_context": monitoring_context,
                "ai_analysis": ai_analysis,
            })

        except HTTPException as exc:
            logger.error(
                "Analysis failed for alert %s: %s",
                alert_name,
                exc.detail,
            )

            results.append({
                "alert": alert_name,
                "status": status,
                "error": exc.detail,
            })

    return {
        "message": "Alertmanager webhook processed",
        "results": results,
    }
