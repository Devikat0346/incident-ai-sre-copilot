import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
import streamlit as st
import matplotlib.pyplot as plt
import networkx as nx
from backend.app.graph.dependency_graph import build_service_graph
sys.path.append(".")

from backend.app.tickets.generator import generate_ticket
from backend.app.severity.scorer import calculate_severity
from backend.app.anomaly.detector import load_events, detect_anomalies
from backend.app.anomaly.ml_detector import detect_ml_anomalies, evaluate_ml_detector
from backend.app.clustering.incident_clusterer import cluster_incidents, summarize_clusters
from backend.app.correlation.engine import build_failure_chain
from backend.app.graph.analytics import analyze_incident_cluster, rank_service_risk
from backend.app.prediction.root_cause_predictor import evaluate_root_cause_model, predict_root_cause
from backend.app.rca.generator import generate_rca_report
from backend.app.rca.llm_generator import build_rca_context, generate_llm_rca_report
from backend.app.rca.provider import (
    RcaProviderConfig,
    RcaProviderError,
    get_default_provider_config,
    generate_rca_with_provider,
)

st.set_page_config(page_title="IncidentGPT", layout="wide")

st.title("IncidentGPT: AI SRE Copilot")
st.caption("Local MVP for anomaly detection, correlation, and RCA generation")

dataset_labels = {
    "sample_events.json": "Sample events (14 rows)",
    "synthetic_events_1000.json": "Synthetic events (1,000 rows)",
    "synthetic_events_5000.json": "Synthetic events (5,000 rows)",
    "synthetic_events_10000.json": "Synthetic events (10,000 rows)",
}
data_files = [
    Path("data/sample_events.json"),
    Path("data/synthetic_events_1000.json"),
    Path("data/synthetic_events_5000.json"),
    Path("data/synthetic_events_10000.json"),
]
available_data_files = [path for path in data_files if path.exists()]
selected_data_file = st.sidebar.selectbox(
    "Dataset",
    available_data_files,
    format_func=lambda path: dataset_labels.get(path.name, path.name),
)
st.sidebar.caption("`synthetic_events.json` is the default 1,000-row export and is hidden here to avoid duplicate choices.")

rca_provider_label = st.sidebar.selectbox(
    "AI RCA Provider",
    ["Local Draft", "OpenAI-compatible", "Ollama"],
)
rca_provider_key = {
    "Local Draft": "local",
    "OpenAI-compatible": "openai",
    "Ollama": "ollama",
}[rca_provider_label]
default_rca_provider_config = get_default_provider_config(rca_provider_key)
rca_provider_model = None
rca_provider_base_url = None
rca_provider_api_key = None

if rca_provider_key != "local":
    rca_provider_model = st.sidebar.text_input(
        "RCA Model",
        value=default_rca_provider_config.model or "",
    )
    rca_provider_base_url = st.sidebar.text_input(
        "RCA Base URL",
        value=default_rca_provider_config.base_url or "",
    )

if rca_provider_key == "openai":
    rca_provider_api_key = st.sidebar.text_input(
        "OpenAI API Key",
        value=default_rca_provider_config.api_key or "",
        type="password",
    )

rca_provider_config = RcaProviderConfig(
    provider=rca_provider_key,
    model=rca_provider_model or default_rca_provider_config.model,
    base_url=rca_provider_base_url or default_rca_provider_config.base_url,
    api_key=rca_provider_api_key or default_rca_provider_config.api_key,
)

with st.spinner(f"Loading {selected_data_file.name}..."):
    df = load_events(str(selected_data_file))
    df = detect_anomalies(df)
    df = detect_ml_anomalies(df)
    df = cluster_incidents(df)

cluster_summary = summarize_clusters(df)
selected_cluster = None
cluster_events = None
graph_analysis = None

st.subheader("Dataset Overview")
overview_col1, overview_col2, overview_col3, overview_col4 = st.columns(4)
overview_col1.metric("Dataset", selected_data_file.name)
overview_col2.metric("Rows", f"{len(df):,}")
overview_col3.metric("Threshold Anomalies", f"{int(df['is_anomaly'].sum()):,}")
overview_col4.metric("ML Anomalies", f"{int(df['ml_is_anomaly'].sum()):,}")

time_range = ""
if "timestamp" in df and not df.empty:
    timestamps = df["timestamp"].astype(str)
    time_range = f"{timestamps.iloc[0]} -> {timestamps.iloc[-1]}"
st.caption(f"Selected dataset: `{selected_data_file}` | Time range: {time_range or 'Unavailable'}")

st.subheader("Incident Timeline")
st.dataframe(df)

st.subheader("Threshold Anomalies Detected")
anomalies = df[df["is_anomaly"] == True]
st.dataframe(anomalies)

st.subheader("ML Anomalies Detected")
ml_anomalies = df[df["ml_is_anomaly"] == True]
st.dataframe(ml_anomalies)

ml_evaluation = evaluate_ml_detector(df)
if ml_evaluation:
    st.subheader("ML Model Evaluation")
    col1, col2, col3 = st.columns(3)
    col1.metric("Precision", ml_evaluation["precision"])
    col2.metric("Recall", ml_evaluation["recall"])
    col3.metric("F1", ml_evaluation["f1"])
    st.json(ml_evaluation["confusion_matrix"])

root_cause_evaluation = evaluate_root_cause_model(df)
if root_cause_evaluation:
    st.subheader("Root Cause Model Evaluation")
    eval_col1, eval_col2 = st.columns(2)
    eval_col1.metric("Accuracy", root_cause_evaluation["accuracy"])
    eval_col2.metric("Macro F1", root_cause_evaluation["macro_f1"])
    st.json(
        {
            "labels": root_cause_evaluation["labels"],
            "confusion_matrix": root_cause_evaluation["confusion_matrix"],
        }
    )

st.subheader("Incident Clusters")
if cluster_summary.empty:
    st.info("No incident clusters detected.")
else:
    st.dataframe(cluster_summary)

    selected_cluster = st.selectbox(
        "Cluster Details",
        cluster_summary["incident_cluster_id"].tolist(),
    )
    cluster_events = df[df["incident_cluster_id"] == selected_cluster]
    st.dataframe(cluster_events)

    graph_analysis = analyze_incident_cluster(cluster_events)
    st.subheader("Cluster Graph Analysis")
    graph_col1, graph_col2, graph_col3 = st.columns(3)
    graph_col1.metric("Probable Origin", graph_analysis["probable_root_service"] or "Unknown")
    graph_col2.metric("Affected Services", len(graph_analysis["affected_services"]))
    graph_col3.metric("Blast Radius", len(graph_analysis["blast_radius"]))

    if graph_analysis["propagation_paths"]:
        st.markdown("#### Failure Propagation Paths")
        for path in graph_analysis["propagation_paths"]:
            st.write(" -> ".join(path))
    else:
        st.info("No dependency-based propagation path found for this cluster.")

    root_cause_prediction = predict_root_cause(cluster_events, df)
    st.subheader("Root Cause Prediction")
    if root_cause_prediction:
        pred_col1, pred_col2 = st.columns(2)
        pred_col1.metric("Predicted Root Cause", root_cause_prediction["predicted_root_cause"])
        pred_col2.metric("Confidence", root_cause_prediction["confidence"])
        st.json(root_cause_prediction["class_probabilities"])
    else:
        st.info("Root cause prediction requires labeled synthetic incident data.")

st.subheader("Anomaly Score by Service")

score_df = df[["timestamp", "service", "metric", "value", "threshold", "is_anomaly"]].copy()

score_df["anomaly_score"] = score_df["value"] / score_df["threshold"]
score_df["label"] = score_df["service"] + " - " + score_df["metric"]

st.caption("Anomaly score = actual value divided by threshold. Scores above 1.0 are anomalous.")

st.bar_chart(
    score_df.set_index("label")["anomaly_score"]
)

st.subheader("ML Anomaly Score by Service")
ml_score_df = df[["service", "metric", "ml_anomaly_score"]].copy()
ml_score_df["label"] = ml_score_df["service"] + " - " + ml_score_df["metric"]
ml_score_df = ml_score_df.sort_values("ml_anomaly_score", ascending=False).head(25)
st.caption("Higher ML anomaly scores are more unusual according to Isolation Forest.")
st.bar_chart(ml_score_df.set_index("label")["ml_anomaly_score"])

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
        f"{event['timestamp']} -> **{event['service']}** -> "
        f"{event['metric']} = {event['value']} -> {event['message']}"
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
rca_mode = st.radio("RCA Mode", ["Template", "AI Draft"], horizontal=True)

if rca_mode == "AI Draft" and cluster_events is not None:
    rca_context = build_rca_context(cluster_events, graph_analysis or {}, severity, severity_score)
    if rca_provider_key == "openai" and not rca_provider_config.api_key:
        st.info("Enter an OpenAI API key in the sidebar, or switch the AI RCA Provider to Local Draft.")
        ai_rca_report = generate_llm_rca_report(rca_context)
    else:
        try:
            ai_rca_report = generate_rca_with_provider(rca_context, rca_provider_config)
        except RcaProviderError as exc:
            st.warning(f"{rca_provider_label} RCA generation was unavailable: {exc}")
            st.caption("Showing the local deterministic RCA draft instead.")
            ai_rca_report = generate_llm_rca_report(rca_context)

    st.markdown("### Executive Summary")
    st.caption(f"Provider: {ai_rca_report.get('provider', 'local')} | Model: {ai_rca_report.get('model', 'deterministic')}")
    st.info(ai_rca_report["executive_summary"])

    st.markdown("### Business Impact")
    st.warning(ai_rca_report["business_impact"])

    st.markdown("### Technical RCA")
    st.write(ai_rca_report["technical_rca"])

    st.markdown("### Evidence")
    for item in ai_rca_report["evidence"]:
        st.json(item)

    st.markdown("### Remediation Steps")
    for action in ai_rca_report["remediation_steps"]:
        st.write(f"- {action}")
elif rca_mode == "AI Draft":
    st.info("Select an incident cluster to generate an AI RCA draft.")
else:
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

graph = build_service_graph()
service_risk = rank_service_risk(graph)

st.subheader("Service Risk Ranking")
st.dataframe(service_risk)
if not service_risk.empty:
    st.metric("Most Critical Service", service_risk.iloc[0]["service"])

fig, ax = plt.subplots(figsize=(8, 5))

pos = nx.spring_layout(graph, seed=42)
risk_by_service = service_risk.set_index("service")["risk_score"].to_dict()
node_risk = [risk_by_service.get(node, 0) for node in graph.nodes()]
node_sizes = [1800 + (risk_by_service.get(node, 0) * 3200) for node in graph.nodes()]

nx.draw(
    graph,
    pos,
    with_labels=True,
    node_size=node_sizes,
    node_color=node_risk,
    cmap=plt.cm.YlOrRd,
    font_size=9,
    arrows=True,
    ax=ax
)

st.pyplot(fig)
st.caption("Arrows point from a caller to its dependency. Larger, warmer nodes have higher operational risk.")
