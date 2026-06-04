from datetime import datetime

def generate_ticket(severity, severity_score, root_cause, impacted_services):
    ticket_id = "INC-" + datetime.now().strftime("%Y%m%d%H%M%S")

    return {
        "ticket_id": ticket_id,
        "status": "Open",
        "severity": severity,
        "severity_score": severity_score,
        "short_description": f"{severity} incident detected by IncidentGPT",
        "root_cause": root_cause,
        "impacted_services": impacted_services,
        "assigned_team": "SRE Platform Team",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
