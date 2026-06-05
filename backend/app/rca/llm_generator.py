def build_rca_context(cluster_events, graph_analysis, severity=None, severity_score=None):
    if cluster_events is None or cluster_events.empty:
        return {
            "severity": severity or "Healthy",
            "severity_score": severity_score or 0,
            "probable_root_service": None,
            "affected_services": [],
            "blast_radius": [],
            "propagation_paths": [],
            "evidence": [],
        }

    events = cluster_events.copy()
    affected_services = sorted(set(events.get("service", []).dropna()))
    probable_root_service = graph_analysis.get("probable_root_service") if graph_analysis else None

    evidence = []
    for _, event in events.sort_values("timestamp").head(10).iterrows():
        evidence.append(
            {
                "timestamp": event.get("timestamp"),
                "service": event.get("service"),
                "metric": event.get("metric"),
                "value": event.get("value"),
                "ml_anomaly_score": event.get("ml_anomaly_score"),
                "message": event.get("message", ""),
            }
        )

    return {
        "severity": severity or "Unknown",
        "severity_score": severity_score or 0,
        "probable_root_service": probable_root_service,
        "affected_services": affected_services,
        "blast_radius": graph_analysis.get("blast_radius", []) if graph_analysis else [],
        "propagation_paths": graph_analysis.get("propagation_paths", []) if graph_analysis else [],
        "evidence": evidence,
    }


def _format_services(services):
    return ", ".join(services) if services else "no services"


def _format_paths(paths):
    if not paths:
        return ["No dependency propagation path was found."]
    return [" -> ".join(path) for path in paths]


def generate_llm_rca_report(context):
    root_service = context.get("probable_root_service") or "unknown service"
    affected_services = context.get("affected_services", [])
    blast_radius = context.get("blast_radius", [])
    propagation_paths = _format_paths(context.get("propagation_paths", []))
    evidence = context.get("evidence", [])

    if not evidence:
        return {
            "executive_summary": "No active incident cluster is available for RCA generation.",
            "business_impact": "No customer or business impact identified.",
            "technical_rca": "No anomalous cluster evidence was provided.",
            "remediation_steps": [],
            "evidence": [],
        }

    highest_signal = max(evidence, key=lambda item: item.get("ml_anomaly_score") or 0)

    executive_summary = (
        f"IncidentGPT identified a clustered service degradation likely originating in {root_service}. "
        f"The cluster spans {_format_services(affected_services)} and is currently classified as "
        f"{context.get('severity')} with score {context.get('severity_score')}."
    )

    business_impact = (
        f"Impacted services include {_format_services(affected_services)}. "
        f"If {root_service} continues to degrade, dependency analysis indicates potential blast radius across "
        f"{_format_services(blast_radius)}."
    )

    technical_rca = (
        f"The strongest anomalous signal is {highest_signal.get('service')} "
        f"{highest_signal.get('metric')}={highest_signal.get('value')} "
        f"at {highest_signal.get('timestamp')}. Graph analysis points to {root_service} as the probable origin. "
        f"Observed propagation path candidates: {'; '.join(propagation_paths)}."
    )

    remediation_steps = [
        f"Start investigation with {root_service} logs, traces, recent deployments, and resource metrics.",
        "Validate the earliest anomalous services against deployment and infrastructure change history.",
        "Check upstream dependencies and downstream callers shown in the propagation paths.",
        "Apply the relevant service runbook, then watch ML anomaly score and error/latency recovery.",
        "Keep the incident open until affected services return to baseline and no new alerts join the cluster.",
    ]

    return {
        "executive_summary": executive_summary,
        "business_impact": business_impact,
        "technical_rca": technical_rca,
        "remediation_steps": remediation_steps,
        "evidence": evidence,
    }
