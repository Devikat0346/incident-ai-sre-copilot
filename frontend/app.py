import sys
import pandas as pd
import streamlit as st

sys.path.append(".")

from backend.app.anomaly.detector import load_events, detect_anomalies

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

st.subheader("Likely Root Cause")
root_cause = anomalies.iloc[0]["message"] if not anomalies.empty else "No root cause detected"
st.error(root_cause)

st.subheader("Suggested Runbook")
st.write("""
1. Check active database connections.
2. Identify long-running queries.
3. Restart unhealthy auth-service pods if needed.
4. Scale database connection pool.
5. Validate payment-service error rate recovery.
""")
