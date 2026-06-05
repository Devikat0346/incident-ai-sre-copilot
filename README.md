# Incident AI SRE Copilot

An AI-powered SRE copilot that detects anomalies from observability events, correlates service failures, identifies probable root cause, and generates incident RCA summaries.

## Features

- Streamlit dashboard for incident timeline
- Threshold-based anomaly detection
- Isolation Forest anomaly detection with model evaluation
- DBSCAN incident clustering for related alerts
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

## Test

```bash
python -m unittest
```
