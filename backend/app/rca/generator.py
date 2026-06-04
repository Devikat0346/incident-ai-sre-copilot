def generate_rca_report(correlation_result):
    root_service = correlation_result.get("root_cause_service")
    failure_chain = correlation_result.get("failure_chain", [])

    if not failure_chain:
        return {
            "incident_summary": "No active incident detected.",
            "business_impact": "No customer or business impact identified.",
            "evidence": [],
            "next_actions": []
        }

    impacted_services = [event["service"] for event in failure_chain]
    first_event = failure_chain[0]

    evidence = [
        f"{event['timestamp']} | {event['service']} | {event['metric']}={event['value']} | {event['message']}"
        for event in failure_chain
    ]

    next_actions = [
        f"Investigate {root_service} first because it showed the earliest anomaly.",
        "Validate whether the issue started after a deployment, config change, or traffic spike.",
        "Check logs, metrics, and traces for the impacted services.",
        "Apply the runbook steps and monitor recovery.",
        "Confirm error rate and latency return to baseline."
    ]

    business_impact = (
        f"The incident impacted {', '.join(impacted_services)}. "
        "Users may experience failed requests, increased latency, or payment/authentication errors."
    )

    incident_summary = (
        f"IncidentGPT detected a cascading failure starting from {root_service}. "
        f"The failure propagated through {' → '.join(impacted_services)}. "
        f"The likely root cause is: {first_event['message']}."
    )

    return {
        "incident_summary": incident_summary,
        "business_impact": business_impact,
        "evidence": evidence,
        "next_actions": next_actions
    }
