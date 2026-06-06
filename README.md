# Incident AI SRE Copilot

An AI-powered SRE copilot that detects anomalies from observability events, correlates service failures, identifies probable root cause, and generates incident RCA summaries.

## Features

- Streamlit dashboard for incident timeline
- Threshold-based anomaly detection
- Isolation Forest anomaly detection with model evaluation
- DBSCAN incident clustering for related alerts
- Graph analytics for blast radius, propagation paths, and service risk
- AI-draft RCA generation from incident clusters and graph context
- Optional OpenAI-compatible and Ollama RCA providers with local fallback
- Random Forest root-cause prediction from labeled incident telemetry
- Service correlation engine
- RCA report generator
- Sample observability dataset
- Synthetic telemetry generator for realistic AIOps datasets
- Local-first setup

## Tech Stack

Python, Streamlit, Pandas, Scikit-learn, NetworkX

## Run Locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run frontend/app.py
```

## Generate Synthetic Telemetry

```bash
python -m backend.app.generator.synthetic_events
```

This creates synthetic observability datasets in `data/`:

- `synthetic_events.json`
- `synthetic_events_1000.json`
- `synthetic_events_5000.json`
- `synthetic_events_10000.json`

Each event includes timestamp, service, metric, value, severity, environment,
region, deployment version, known anomaly label, root cause label, incident ID,
and message fields. The dashboard automatically shows generated datasets in the
sidebar when the files exist.

## ML Anomaly Detection

The dashboard runs threshold detection and Isolation Forest detection side by side.
For synthetic datasets, ML results are evaluated against `known_anomaly` labels and
shown with precision, recall, F1, and a confusion matrix.
The sidebar lists distinct dataset sizes; `synthetic_events.json` is the same
1,000-row default export as `synthetic_events_1000.json`.

## Incident Clustering

ML anomalies are grouped with DBSCAN so related alerts can be viewed as incident
clusters. The dashboard shows cluster counts, impacted services, likely labels,
and the alerts within each cluster.

## Graph Analytics

Incident clusters are analyzed against the service dependency graph to estimate
the probable origin service, calculate blast radius, identify failure propagation
paths, rank critical services, and calculate betweenness centrality.

## AI RCA Generation

The dashboard can generate an AI-style RCA draft for a selected incident cluster.
The draft uses clustered anomaly evidence, probable origin service, blast radius,
propagation paths, severity, and affected services. The existing template RCA
remains available as a fallback mode.

By default, RCA generation uses the local deterministic draft generator. The
sidebar can also route AI RCA generation to an OpenAI-compatible API or a local
Ollama server.

OpenAI-compatible provider:

```bash
export OPENAI_API_KEY=your_api_key
export OPENAI_MODEL=gpt-4o-mini
export OPENAI_BASE_URL=https://api.openai.com/v1
```

Ollama provider:

```bash
export OLLAMA_MODEL=llama3.1
export OLLAMA_BASE_URL=http://localhost:11434
```

If a configured provider fails, the dashboard keeps working and shows the local
RCA draft as a fallback.

## Root Cause Prediction

Synthetic incident labels are used to train a Random Forest classifier that
predicts the most likely root cause for a selected incident cluster. The dashboard
shows predicted root cause, confidence, class probabilities, accuracy, macro F1,
and a confusion matrix when labeled synthetic data is selected.

## Test

```bash
python -m unittest
```
