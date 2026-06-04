import pandas as pd

SERVICE_DEPENDENCIES = {
    "api-gateway": ["payment-service"],
    "payment-service": ["auth-service"],
    "auth-service": ["database"],
    "database": []
}

def build_failure_chain(anomalies_df: pd.DataFrame):
    if anomalies_df.empty:
        return {
            "root_cause_service": None,
            "failure_chain": [],
            "summary": "No anomalies detected."
        }

    sorted_df = anomalies_df.sort_values("timestamp")

    root_event = sorted_df.iloc[0]
    root_service = root_event["service"]

    chain = []

    for _, row in sorted_df.iterrows():
        chain.append({
            "timestamp": row["timestamp"],
            "service": row["service"],
            "metric": row["metric"],
            "value": row["value"],
            "message": row["message"]
        })

    impacted_services = [item["service"] for item in chain]

    summary = (
        f"The earliest anomaly was detected in {root_service}. "
        f"Failures then propagated across: {' → '.join(impacted_services)}. "
        f"Likely root cause: {root_event['message']}."
    )

    return {
        "root_cause_service": root_service,
        "failure_chain": chain,
        "summary": summary
    }
