import unittest

import pandas as pd

from backend.app.anomaly.ml_detector import detect_ml_anomalies, evaluate_ml_detector
from backend.app.generator.synthetic_events import generate_synthetic_events


class MlDetectorTest(unittest.TestCase):
    def test_detect_ml_anomalies_adds_expected_columns(self):
        df = pd.DataFrame(generate_synthetic_events(event_count=300, seed=11))
        result = detect_ml_anomalies(df, contamination=0.08, random_state=11)

        self.assertIn("ml_prediction", result)
        self.assertIn("ml_is_anomaly", result)
        self.assertIn("ml_anomaly_score", result)
        self.assertEqual(len(result), len(df))
        self.assertTrue(result["ml_is_anomaly"].any())

    def test_detector_handles_legacy_sample_shape(self):
        df = pd.DataFrame(
            [
                {"service": "database", "metric": "latency_ms", "value": 1500},
                {"service": "auth-service", "metric": "error_rate", "value": 1},
            ]
        )

        result = detect_ml_anomalies(df, contamination=0.5, random_state=3)

        self.assertIn("ml_is_anomaly", result)
        self.assertEqual(len(result), 2)

    def test_evaluate_ml_detector_returns_metrics_when_labels_exist(self):
        df = pd.DataFrame(generate_synthetic_events(event_count=300, seed=13))
        result = detect_ml_anomalies(df, contamination=0.08, random_state=13)
        metrics = evaluate_ml_detector(result)

        self.assertIsNotNone(metrics)
        self.assertIn("precision", metrics)
        self.assertIn("recall", metrics)
        self.assertIn("f1", metrics)
        self.assertIn("confusion_matrix", metrics)

    def test_evaluate_ml_detector_returns_none_without_labels(self):
        df = pd.DataFrame([{"service": "database", "metric": "latency_ms", "value": 1500}])
        result = detect_ml_anomalies(df, contamination=0.5)

        self.assertIsNone(evaluate_ml_detector(result))


if __name__ == "__main__":
    unittest.main()
