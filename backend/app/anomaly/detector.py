import json
import pandas as pd

THRESHOLDS = {
    "connection_pool_usage": 80,
    "latency_ms": 1000,
    "error_rate": 5,
    "5xx_rate": 5
}

def load_events(file_path="data/sample_events.json"):
    with open(file_path, "r") as file:
        return pd.DataFrame(json.load(file))

def detect_anomalies(df):
    df["threshold"] = df["metric"].map(THRESHOLDS)
    df["is_anomaly"] = df["value"] > df["threshold"]
    return df

if __name__ == "__main__":
    events_df = load_events()
    result = detect_anomalies(events_df)
    print(result)
