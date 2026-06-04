# Incident AI SRE Copilot

An AI-powered SRE copilot that detects anomalies from observability events, correlates service failures, identifies probable root cause, and generates incident RCA summaries.

## Features

- Streamlit dashboard for incident timeline
- Threshold-based anomaly detection
- Service correlation engine
- RCA report generator
- Sample observability dataset
- Local-first setup

## Tech Stack

Python, Streamlit, Pandas, Scikit-learn, NetworkX

## Run Locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run frontend/app.py