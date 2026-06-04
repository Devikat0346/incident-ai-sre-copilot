import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="IncidentGPT", layout="wide")

st.title("IncidentGPT: AI SRE Copilot")
st.caption("Local MVP for anomaly detection, correlation, and RCA generation")

with open("data/sample_events.json", "r") as file:
    events = json.load(file)

df = pd.DataFrame(events)

st.subheader("Incident Timeline")
st.dataframe(df)

st.subheader("Detected Impact Chain")
st.write("""
Database connection pool saturation caused auth-service latency.
Auth-service latency caused payment authentication failures.
Payment failures increased API Gateway 5xx errors.
""")

st.subheader("Likely Root Cause")
st.error("Database connection pool exhaustion")

st.subheader("Suggested Runbook")
st.write("""
1. Check active database connections.
2. Identify long-running queries.
3. Restart unhealthy auth-service pods if needed.
4. Scale database connection pool.
5. Validate payment-service error rate recovery.
""")

st.subheader("Generated Incident Summary")
st.success("""
IncidentGPT detected a cascading failure starting from database connection pool saturation.
The issue propagated to auth-service, payment-service, and API Gateway.
Recommended action is to investigate database connections and query latency first.
""")
