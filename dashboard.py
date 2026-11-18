import json
import os
from datetime import datetime

import gradio as gr

from tools import (
    check_dns,
    check_https,
    check_nginx,
    check_loandocx,
    check_loandocx_port,
    check_backend,
)


# ============================================================
# CONFIGURATION
# ============================================================

INCIDENT_HISTORY_FILE = "/home/ec2-user/recovery-agent/incidents.json"


# ============================================================
# INCIDENT HISTORY
# ============================================================

def load_incidents():
    """
    Safely load persistent incident history.
    """

    if not os.path.exists(INCIDENT_HISTORY_FILE):
        return []

    try:

        with open(
            INCIDENT_HISTORY_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            content = f.read().strip()

        if not content:
            return []

        incidents = json.loads(content)

        if not isinstance(incidents, list):
            return []

        return incidents

    except (json.JSONDecodeError, OSError):

        return []


# ============================================================
# CURRENT SYSTEM STATUS
# ============================================================

def get_current_status():

    results = {}

    try:
        results["dns"] = check_dns()
    except Exception as exc:
        results["dns"] = {
            "status": "ERROR",
            "error": str(exc),
        }

    try:
        results["https"] = check_https()
    except Exception as exc:
        results["https"] = {
            "status": "ERROR",
            "error": str(exc),
        }

    try:
        results["nginx"] = check_nginx()
    except Exception as exc:
        results["nginx"] = {
            "status": "ERROR",
            "error": str(exc),
        }

    try:
        results["loandocx"] = check_loandocx()
    except Exception as exc:
        results["loandocx"] = {
            "status": "ERROR",
            "error": str(exc),
        }

    try:
        results["port"] = check_loandocx_port()
    except Exception as exc:
        results["port"] = {
            "status": "ERROR",
            "error": str(exc),
        }

    try:
        results["backend"] = check_backend()
    except Exception as exc:
        results["backend"] = {
            "status": "ERROR",
            "error": str(exc),
        }

    return results


# ============================================================
# STATUS HELPERS
# ============================================================

def status_icon(ok):
    return "🟢" if ok else "🔴"


def get_http_status(result):

    if not isinstance(result, dict):
        return None

    return (
        result.get("http_status")
        or result.get("status_code")
    )


# ============================================================
# BUILD STATUS DISPLAY
# ============================================================

def build_status():

    results = get_current_status()

    dns_ok = results["dns"].get("status") == "OK"

    https_ok = (
        results["https"].get("status") == "OK"
        and get_http_status(results["https"]) == 200
    )

    nginx_ok = (
        results["nginx"].get("status") == "RUNNING"
    )

    service_ok = (
        results["loandocx"].get("status") == "RUNNING"
    )

    port_ok = (
        results["port"].get("status") == "OPEN"
    )

    backend_ok = (
        results["backend"].get("status") == "RESPONDING"
        and get_http_status(results["backend"]) == 200
    )

    overall_ok = (
        dns_ok
        and https_ok
        and nginx_ok
        and service_ok
        and port_ok
        and backend_ok
    )

    overall_text = (
        "🟢 SYSTEM HEALTHY"
        if overall_ok
        else "🔴 SYSTEM UNHEALTHY"
    )

    hostname = results["dns"].get(
        "hostname",
        "Unknown",
    )

    return f"""
# LoanDocX AI Recovery Agent

## {overall_text}

### Current System Status

| Component | Status |
|---|---|
| DNS | {status_icon(dns_ok)} {"OK" if dns_ok else "FAILED"} |
| HTTPS | {status_icon(https_ok)} HTTP {get_http_status(results["https"]) or "ERROR"} |
| Nginx | {status_icon(nginx_ok)} {"RUNNING" if nginx_ok else "NOT RUNNING"} |
| LoanDocX Service | {status_icon(service_ok)} {"RUNNING" if service_ok else "NOT RUNNING"} |
| Port 7860 | {status_icon(port_ok)} {"OPEN" if port_ok else "CLOSED"} |
| Backend | {status_icon(backend_ok)} {"HTTP 200" if backend_ok else "NOT RESPONDING"} |

**Hostname:** `{hostname}`

**Last checked:** `{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}`
"""

# ============================================================
# LATEST INCIDENT
# ============================================================

def build_latest_incident():

    incidents = load_incidents()

    if not incidents:

        return """
## Latest AI Diagnosis

No incident history is available.
"""

    latest = incidents[-1]

    status = latest.get(
        "status",
        "UNKNOWN",
    )

    diagnosis = latest.get(
        "diagnosis",
        "No diagnosis available.",
    )

    recovery_action = latest.get(
        "recovery_action"
    )

    timestamp = latest.get(
        "timestamp",
        "Unknown",
    )

    return f"""
## Latest AI Diagnosis

**Incident:** `{latest.get("incident_id", "UNKNOWN")}`

**Time:** `{timestamp}`

**Status:** `{status}`

**Recovery Action:** `{recovery_action or "None"}`

### Diagnosis

{diagnosis}
"""


# ============================================================
# INCIDENT HISTORY TABLE
# ============================================================

def build_incident_history():

    incidents = load_incidents()

    if not incidents:

        return "No incident history available."

    rows = []

    for incident in reversed(incidents):

        incident_id = incident.get(
            "incident_id",
            "UNKNOWN",
        )

        timestamp = incident.get(
            "timestamp",
            "",
        )

        status = incident.get(
            "status",
            "UNKNOWN",
        )

        recovery = incident.get(
            "recovery_action"
        )

        recovery = recovery or "None"

        rows.append(
            f"| {incident_id} | {timestamp} | "
            f"{status} | {recovery} |"
        )

    return """
## Incident History

| Incident ID | Timestamp | Status | Recovery |
|---|---|---|---|
""" + "\n".join(rows)


# ============================================================
# TOOL HISTORY
# ============================================================

def build_tool_history():

    incidents = load_incidents()

    if not incidents:

        return "No tool execution history available."

    latest = incidents[-1]

    history = latest.get(
        "tool_history",
        [],
    )

    if not history:

        return "No tool execution history available."

    lines = [
        "## Latest Tool Execution History",
        "",
        "| Tool | Purpose | Result |",
        "|---|---|---|",
    ]

    for item in history:

        tool = item.get(
            "tool",
            "UNKNOWN",
        )

        purpose = item.get(
            "purpose",
            "",
        )

        result = item.get(
            "result",
            {},
        )

        result_text = json.dumps(
            result,
            ensure_ascii=False,
        )

        lines.append(
            f"| `{tool}` | {purpose} | `{result_text}` |"
        )

    return "\n".join(lines)


# ============================================================
# REFRESH DASHBOARD
# ============================================================

def refresh_dashboard():

    print("\n" + "=" * 60)
    print("DASHBOARD REFRESH REQUEST RECEIVED")
    print("=" * 60)

    status = build_status()

    diagnosis = build_latest_incident()

    history = build_incident_history()

    tools = build_tool_history()

    print("Dashboard data rebuilt successfully.")

    return (
        status,
        diagnosis,
        history,
        tools,
    )
# ============================================================
# GRADIO DASHBOARD
# ============================================================

with gr.Blocks(
    title="LoanDocX AI Recovery Agent",
) as dashboard:

    gr.Markdown(
        """
# 🤖 LoanDocX AI Recovery Agent

### Autonomous Server Monitoring • Diagnosis • Recovery • Verification
"""
    )

    refresh_button = gr.Button(
        "🔄 Refresh Dashboard",
        variant="primary",
    )

    with gr.Row():

        with gr.Column():

            status_display = gr.Markdown(
                value=build_status()
            )

        with gr.Column():

            diagnosis_display = gr.Markdown(
                value=build_latest_incident()
            )

    history_display = gr.Markdown(
        value=build_incident_history()
    )

    tools_display = gr.Markdown(
        value=build_tool_history()
    )

    refresh_button.click(
        fn=refresh_dashboard,
        inputs=[],
        outputs=[
            status_display,
            diagnosis_display,
            history_display,
            tools_display,
        ],
    )


# ============================================================
# LAUNCH
# ============================================================

if __name__ == "__main__":

    dashboard.launch(
        server_name="0.0.0.0",
        server_port=7861,
        root_path="/dashboard",
        show_error=True,
    )
    
