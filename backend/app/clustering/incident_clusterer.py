import pandas as pd
import warnings
from sklearn.cluster import DBSCAN
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


CATEGORICAL_FEATURES = ["service", "metric"]
NUMERIC_FEATURES = ["time_position", "metric_robust_zscore", "anomaly_signal"]
FEATURE_COLUMNS = [*CATEGORICAL_FEATURES, *NUMERIC_FEATURES]


def _anomaly_frame(df, anomaly_column):
    if anomaly_column in df:
        return df[df[anomaly_column] == True].copy()
    if "is_anomaly" in df:
        return df[df["is_anomaly"] == True].copy()
    return df.copy()


def _prepare_features(df, time_window_minutes):
    features = df.copy()

    features["timestamp"] = pd.to_datetime(features.get("timestamp"), errors="coerce")
    first_timestamp = features["timestamp"].min()
    if pd.isna(first_timestamp):
        features["time_position"] = range(len(features))
    else:
        minutes_since_first_alert = (
            (features["timestamp"] - first_timestamp).dt.total_seconds() / 60
        ).fillna(0)
        features["time_position"] = minutes_since_first_alert / time_window_minutes

    for column in CATEGORICAL_FEATURES:
        if column not in features:
            features[column] = "unknown"
        features[column] = features[column].fillna("unknown").astype(str)

    features["value"] = pd.to_numeric(features.get("value"), errors="coerce").fillna(0)
    metric_groups = features.groupby("metric")["value"]
    metric_median = metric_groups.transform("median")
    metric_mad = metric_groups.transform(lambda values: (values - values.median()).abs().median())
    metric_mad = metric_mad.replace(0, 1)
    features["metric_robust_zscore"] = (features["value"] - metric_median) / metric_mad

    if "ml_anomaly_score" in features:
        features["anomaly_signal"] = pd.to_numeric(features["ml_anomaly_score"], errors="coerce").fillna(0)
    elif "anomaly_score" in features:
        features["anomaly_signal"] = pd.to_numeric(features["anomaly_score"], errors="coerce").fillna(0)
    else:
        features["anomaly_signal"] = 1

    return features[FEATURE_COLUMNS]


def _build_clusterer(eps, min_samples):
    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("numeric", "passthrough", NUMERIC_FEATURES),
        ]
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", DBSCAN(eps=eps, min_samples=min_samples)),
        ]
    )


def cluster_incidents(df, anomaly_column="ml_is_anomaly", eps=2.6, min_samples=2, time_window_minutes=10):
    result = df.copy()
    result["incident_cluster_id"] = None

    anomalies = _anomaly_frame(result, anomaly_column)
    if anomalies.empty:
        return result

    if len(anomalies) < min_samples:
        result.loc[anomalies.index, "incident_cluster_id"] = "cluster_1"
        return result

    features = _prepare_features(anomalies, time_window_minutes)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="is_sparse is deprecated.*", category=DeprecationWarning)
        labels = _build_clusterer(eps, min_samples).fit_predict(features)

    cluster_ids = []
    next_noise_cluster = 1
    for label in labels:
        if label == -1:
            cluster_ids.append(f"noise_{next_noise_cluster}")
            next_noise_cluster += 1
        else:
            cluster_ids.append(f"cluster_{label + 1}")

    result.loc[anomalies.index, "incident_cluster_id"] = cluster_ids
    return result


def summarize_clusters(df):
    if "incident_cluster_id" not in df:
        return pd.DataFrame(columns=["incident_cluster_id", "alert_count", "services", "root_cause_labels", "start_time", "end_time"])

    clustered = df[df["incident_cluster_id"].notna()].copy()
    if clustered.empty:
        return pd.DataFrame(columns=["incident_cluster_id", "alert_count", "services", "root_cause_labels", "start_time", "end_time"])

    if "service" not in clustered:
        clustered["service"] = "unknown"
    if "root_cause_label" not in clustered:
        clustered["root_cause_label"] = "Unknown"
    if "timestamp" not in clustered:
        clustered["timestamp"] = None

    clustered["service"] = clustered["service"].fillna("unknown").astype(str)
    clustered["root_cause_label"] = clustered["root_cause_label"].fillna("Unknown").astype(str)
    clustered["timestamp"] = pd.to_datetime(clustered.get("timestamp"), errors="coerce")

    summary = (
        clustered.groupby("incident_cluster_id")
        .agg(
            alert_count=("incident_cluster_id", "size"),
            services=("service", lambda values: ", ".join(sorted(set(values)))),
            root_cause_labels=(
                "root_cause_label",
                lambda values: ", ".join(sorted({str(value) for value in values if str(value) != "None"})) or "Unknown",
            ),
            start_time=("timestamp", "min"),
            end_time=("timestamp", "max"),
        )
        .reset_index()
        .sort_values(["alert_count", "incident_cluster_id"], ascending=[False, True])
    )

    summary["start_time"] = summary["start_time"].astype(str)
    summary["end_time"] = summary["end_time"].astype(str)
    return summary
