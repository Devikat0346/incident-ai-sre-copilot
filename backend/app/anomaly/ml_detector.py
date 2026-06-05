import warnings

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


warnings.filterwarnings("ignore", message="is_sparse is deprecated.*", category=DeprecationWarning)

CATEGORICAL_FEATURES = ["service", "metric", "environment", "region", "deployment_version"]
NUMERIC_FEATURES = ["value", "metric_value_ratio", "metric_robust_zscore"]
FEATURE_COLUMNS = [*CATEGORICAL_FEATURES, *NUMERIC_FEATURES]


def _prepare_features(df):
    features = df.copy()

    for column in CATEGORICAL_FEATURES:
        if column not in features:
            features[column] = "unknown"
        features[column] = features[column].fillna("unknown").astype(str)

    features["value"] = pd.to_numeric(features["value"], errors="coerce").fillna(0)

    metric_groups = features.groupby("metric")["value"]
    metric_median = metric_groups.transform("median")
    metric_mad = metric_groups.transform(lambda values: (values - values.median()).abs().median())
    metric_mad = metric_mad.replace(0, 1)

    features["metric_value_ratio"] = features["value"] / metric_median.replace(0, 1)
    features["metric_robust_zscore"] = (features["value"] - metric_median) / metric_mad

    return features[FEATURE_COLUMNS]


def build_ml_detector(contamination=0.08, random_state=42):
    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
        ]
    )

    model = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_estimators=200,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )


def detect_ml_anomalies(df, contamination=0.08, random_state=42):
    if df.empty:
        result = df.copy()
        result["ml_prediction"] = []
        result["ml_is_anomaly"] = []
        result["ml_anomaly_score"] = []
        return result

    result = df.copy()
    features = _prepare_features(result)
    detector = build_ml_detector(contamination=contamination, random_state=random_state)

    ml_prediction = detector.fit_predict(features)
    ml_score = -detector.decision_function(features)

    result["ml_prediction"] = ml_prediction
    result["ml_is_anomaly"] = ml_prediction == -1
    result["ml_anomaly_score"] = ml_score.round(6)

    return result


def evaluate_ml_detector(df, label_column="known_anomaly", prediction_column="ml_is_anomaly"):
    if label_column not in df or prediction_column not in df:
        return None

    evaluation_df = df[[label_column, prediction_column]].dropna()
    if evaluation_df.empty:
        return None

    y_true = evaluation_df[label_column].astype(bool)
    y_pred = evaluation_df[prediction_column].astype(bool)
    matrix = confusion_matrix(y_true, y_pred, labels=[False, True])

    return {
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_true, y_pred, zero_division=0), 4),
        "confusion_matrix": {
            "true_negative": int(matrix[0][0]),
            "false_positive": int(matrix[0][1]),
            "false_negative": int(matrix[1][0]),
            "true_positive": int(matrix[1][1]),
        },
    }
