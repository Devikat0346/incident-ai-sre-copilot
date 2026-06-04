import sys
import streamlit as st

sys.path.append(".")

from backend.app.anomaly.detector import load_events, detect_anomalies
from backend.app.correlation.engine import build_failure_chain

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

correlation_result = build_failure_chain(anomalies)

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