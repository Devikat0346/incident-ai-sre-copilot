import sys
import streamlit as st

sys.path.append(".")

from backend.app.graph.dependency_graph import get_dependency_edges
from backend.app.tickets.generator import generate_ticket
from backend.app.severity.scorer import calculate_severity
from backend.app.anomaly.detector import load_events, detect_anomalies
from backend.app.correlation.engine import build_failure_chain
from backend.app.rca.generator import generate_rca_report

st.set_page_config(page_title="IncidentGPT", layout="wide")

st.title("IncidentGPT: AI SRE Copilot")
st.caption("Local MVP for anomaly detection, correlation, and RCA generation")

df = load_events()
df = detect_anomalies(df)

st.subheader("Incident Timeline")
st.dataframe(df)

st.subheader("Anomalies Detected")
anomalies = df[df["is_anomaly"] == True]
st.dataframe(anomalies)

st.subheader("Anomaly Score by Service")

score_df = df[["timestamp", "service", "metric", "value", "threshold", "is_anomaly"]].copy()

score_df["anomaly_score"] = score_df["value"] / score_df["threshold"]
score_df["label"] = score_df["service"] + " - " + score_df["metric"]

st.caption("Anomaly score = actual value divided by threshold. Scores above 1.0 are anomalous.")

st.bar_chart(
    score_df.set_index("label")["anomaly_score"]
)

df["anomaly_score"] = df["value"] / df["threshold"]
anomalies = df[df["is_anomaly"] == True]

severity, severity_score = calculate_severity(anomalies)

st.subheader("Incident Severity")
st.metric("Severity", severity)
st.metric("Severity Score", severity_score)

correlation_result = build_failure_chain(anomalies)
rca_report = generate_rca_report(correlation_result)

st.subheader("Failure Chain")

for event in correlation_result["failure_chain"]:
    st.write(
        f"{event['timestamp']} → **{event['service']}** → "
        f"{event['metric']} = {event['value']} → {event['message']}"
    )

st.subheader("Likely Root Cause")
st.error(correlation_result["summary"])

st.subheader("Suggested Runbook")
st.write("""
1. Check active database connections.
2. Identify long-running queries.
3. Restart unhealthy auth-service pods if needed.
4. Scale database connection pool.
5. Validate payment-service error rate recovery.
""")

st.subheader("RCA Report")

st.markdown("### Incident Summary")
st.info(rca_report["incident_summary"])

st.markdown("### Business Impact")
st.warning(rca_report["business_impact"])

st.markdown("### Evidence")
for item in rca_report["evidence"]:
    st.code(item)

st.markdown("### Next Actions")
for action in rca_report["next_actions"]:
    st.write(f"- {action}")

st.subheader("Mock Incident Ticket")

if st.button("Create Incident Ticket"):
    impacted_services = anomalies["service"].unique().tolist()
    root_cause = anomalies.iloc[0]["message"] if not anomalies.empty else "No active incident"

    ticket = generate_ticket(
        severity,
        severity_score,
        root_cause,
        impacted_services
    )

    st.json(ticket)

st.subheader("Service Dependency Graph")

edges = get_dependency_edges()

for source, target in edges:
    st.write(f"{source} → {target}")