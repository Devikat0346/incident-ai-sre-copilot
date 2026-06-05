import unittest

import pandas as pd

from backend.app.anomaly.detector import detect_anomalies
from backend.app.anomaly.ml_detector import detect_ml_anomalies
from backend.app.clustering.incident_clusterer import cluster_incidents, summarize_clusters
from backend.app.generator.synthetic_events import generate_synthetic_events
from backend.app.prediction.root_cause_predictor import (
    build_cluster_feature_frame,
    build_training_frame,
    evaluate_root_cause_model,
    predict_root_cause,
    train_root_cause_model,
)


class RootCausePredictorTest(unittest.TestCase):
    def test_build_training_frame_uses_labeled_incidents(self):
        df = pd.DataFrame(generate_synthetic_events(event_count=1000, seed=31))
        frame = build_training_frame(df)

        self.assertFalse(frame.empty)
        self.assertIn("root_cause_label", frame)
        self.assertIn("latency_ms", frame)
        self.assertGreater(frame["root_cause_label"].nunique(), 1)

    def test_train_root_cause_model_returns_classifier(self):
        df = pd.DataFrame(generate_synthetic_events(event_count=1000, seed=32))
        model = train_root_cause_model(df)

        self.assertIsNotNone(model)
        self.assertGreater(len(model.classes_), 1)

    def test_predict_root_cause_returns_prediction_for_cluster(self):
        df = pd.DataFrame(generate_synthetic_events(event_count=1000, seed=33))
        df = cluster_incidents(detect_ml_anomalies(detect_anomalies(df), random_state=33))
        cluster_id = summarize_clusters(df).iloc[0]["incident_cluster_id"]
        cluster_events = df[df["incident_cluster_id"] == cluster_id]

        prediction = predict_root_cause(cluster_events, df, random_state=33)

        self.assertIsNotNone(prediction)
        self.assertIn("predicted_root_cause", prediction)
        self.assertIn("confidence", prediction)

    def test_evaluate_root_cause_model_returns_metrics(self):
        df = pd.DataFrame(generate_synthetic_events(event_count=1000, seed=34))
        metrics = evaluate_root_cause_model(df, random_state=34)

        self.assertIsNotNone(metrics)
        self.assertIn("accuracy", metrics)
        self.assertIn("macro_f1", metrics)
        self.assertIn("confusion_matrix", metrics)

    def test_cluster_feature_frame_handles_empty_cluster(self):
        frame = build_cluster_feature_frame(pd.DataFrame())

        self.assertTrue(frame.empty)


if __name__ == "__main__":
    unittest.main()
