import pandas as pd
import warnings
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split


METRIC_FEATURES = [
    "latency_ms",
    "error_rate",
    "cpu_usage",
    "memory_usage",
    "connection_pool_usage",
    "queue_depth",
    "5xx_rate",
]

EXTRA_FEATURES = ["alert_count", "unique_service_count", "max_ml_anomaly_score"]
FEATURE_COLUMNS = [*METRIC_FEATURES, *EXTRA_FEATURES]


def _labeled_anomalies(df):
    if "root_cause_label" not in df:
        return pd.DataFrame()

    events = df.copy()
    events = events[events["root_cause_label"].notna()]
    events = events[events["root_cause_label"].astype(str) != "None"]
    events = events[events["root_cause_label"].astype(str) != "Unknown"]

    if "known_anomaly" in events:
        events = events[events["known_anomaly"] == True]

    return events


def _aggregate_events(events, group_column):
    if events.empty:
        return pd.DataFrame(columns=[group_column, "root_cause_label", *FEATURE_COLUMNS])

    working = events.copy()
    working["value"] = pd.to_numeric(working.get("value"), errors="coerce").fillna(0)
    if "ml_anomaly_score" not in working:
        working["ml_anomaly_score"] = 0
    working["ml_anomaly_score"] = pd.to_numeric(working["ml_anomaly_score"], errors="coerce").fillna(0)

    metric_pivot = (
        working.pivot_table(
            index=group_column,
            columns="metric",
            values="value",
            aggfunc="max",
            fill_value=0,
        )
        .reindex(columns=METRIC_FEATURES, fill_value=0)
        .reset_index()
    )

    extras = (
        working.groupby(group_column)
        .agg(
            alert_count=("metric", "size"),
            unique_service_count=("service", "nunique"),
            max_ml_anomaly_score=("ml_anomaly_score", "max"),
            root_cause_label=("root_cause_label", lambda values: values.mode().iloc[0]),
        )
        .reset_index()
    )

    return metric_pivot.merge(extras, on=group_column)


def build_training_frame(df):
    events = _labeled_anomalies(df)
    if events.empty:
        return pd.DataFrame(columns=["incident_id", "root_cause_label", *FEATURE_COLUMNS])

    group_column = "incident_id" if "incident_id" in events else "root_cause_label"
    events[group_column] = events[group_column].fillna(events["root_cause_label"])
    return _aggregate_events(events, group_column)


def build_cluster_feature_frame(cluster_events):
    if cluster_events.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS)

    events = cluster_events.copy()
    events["cluster_key"] = "selected_cluster"
    if "root_cause_label" not in events:
        events["root_cause_label"] = "Unknown"
    frame = _aggregate_events(events, "cluster_key")
    return frame[FEATURE_COLUMNS]


def train_root_cause_model(df, random_state=42):
    training_frame = build_training_frame(df)
    if training_frame.empty or training_frame["root_cause_label"].nunique() < 2:
        return None

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=random_state,
        class_weight="balanced",
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="is_sparse is deprecated.*", category=DeprecationWarning)
        model.fit(training_frame[FEATURE_COLUMNS], training_frame["root_cause_label"])
    return model


def predict_root_cause(cluster_events, training_events, random_state=42):
    model = train_root_cause_model(training_events, random_state=random_state)
    if model is None or cluster_events is None or cluster_events.empty:
        return None

    features = build_cluster_feature_frame(cluster_events)
    if features.empty:
        return None

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="is_sparse is deprecated.*", category=DeprecationWarning)
        probabilities = model.predict_proba(features)[0]
    best_index = probabilities.argmax()
    predicted_label = model.classes_[best_index]

    return {
        "predicted_root_cause": predicted_label,
        "confidence": round(float(probabilities[best_index]), 4),
        "class_probabilities": {
            label: round(float(probability), 4)
            for label, probability in zip(model.classes_, probabilities)
        },
    }


def evaluate_root_cause_model(df, random_state=42):
    training_frame = build_training_frame(df)
    if training_frame.empty or training_frame["root_cause_label"].nunique() < 2:
        return None

    label_counts = training_frame["root_cause_label"].value_counts()
    stratify = training_frame["root_cause_label"] if label_counts.min() >= 2 else None

    train_df, test_df = train_test_split(
        training_frame,
        test_size=0.3,
        random_state=random_state,
        stratify=stratify,
    )

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=random_state,
        class_weight="balanced",
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="is_sparse is deprecated.*", category=DeprecationWarning)
        model.fit(train_df[FEATURE_COLUMNS], train_df["root_cause_label"])
        predictions = model.predict(test_df[FEATURE_COLUMNS])
    labels = sorted(training_frame["root_cause_label"].unique())
    matrix = confusion_matrix(test_df["root_cause_label"], predictions, labels=labels)

    return {
        "accuracy": round(accuracy_score(test_df["root_cause_label"], predictions), 4),
        "macro_f1": round(f1_score(test_df["root_cause_label"], predictions, average="macro", zero_division=0), 4),
        "labels": labels,
        "confusion_matrix": matrix.tolist(),
    }
