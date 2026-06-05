import unittest

import pandas as pd

from backend.app.anomaly.detector import detect_anomalies
from backend.app.anomaly.ml_detector import detect_ml_anomalies
from backend.app.clustering.incident_clusterer import cluster_incidents, summarize_clusters
from backend.app.generator.synthetic_events import generate_synthetic_events


class IncidentClustererTest(unittest.TestCase):
    def test_cluster_incidents_adds_cluster_column_for_ml_anomalies(self):
        df = pd.DataFrame(generate_synthetic_events(event_count=500, seed=21))
        df = detect_ml_anomalies(detect_anomalies(df), random_state=21)

        result = cluster_incidents(df)

        self.assertIn("incident_cluster_id", result)
        self.assertTrue(result["incident_cluster_id"].notna().any())

    def test_summarize_clusters_returns_alert_counts(self):
        df = pd.DataFrame(generate_synthetic_events(event_count=500, seed=22))
        df = detect_ml_anomalies(detect_anomalies(df), random_state=22)
        result = cluster_incidents(df)
        summary = summarize_clusters(result)

        self.assertFalse(summary.empty)
        self.assertIn("alert_count", summary)
        self.assertGreater(summary["alert_count"].sum(), 0)

    def test_cluster_incidents_falls_back_to_threshold_anomalies(self):
        df = pd.DataFrame(
            [
                {"timestamp": "2026-06-04T10:00:00", "service": "database", "metric": "latency_ms", "value": 1500, "is_anomaly": True},
                {"timestamp": "2026-06-04T10:02:00", "service": "auth-service", "metric": "latency_ms", "value": 1400, "is_anomaly": True},
                {"timestamp": "2026-06-04T10:30:00", "service": "api-gateway", "metric": "5xx_rate", "value": 1, "is_anomaly": False},
            ]
        )

        result = cluster_incidents(df, anomaly_column="missing_ml_column")

        self.assertEqual(result["incident_cluster_id"].notna().sum(), 2)

    def test_summarize_clusters_handles_no_clusters(self):
        summary = summarize_clusters(pd.DataFrame([{"service": "database"}]))

        self.assertTrue(summary.empty)

    def test_summarize_clusters_handles_missing_root_cause_label(self):
        df = pd.DataFrame(
            [
                {
                    "timestamp": "2026-06-04T10:00:00",
                    "service": "database",
                    "incident_cluster_id": "cluster_1",
                },
                {
                    "timestamp": "2026-06-04T10:02:00",
                    "service": "auth-service",
                    "incident_cluster_id": "cluster_1",
                },
            ]
        )

        summary = summarize_clusters(df)

        self.assertEqual(summary.iloc[0]["root_cause_labels"], "Unknown")
        self.assertEqual(summary.iloc[0]["alert_count"], 2)


if __name__ == "__main__":
    unittest.main()
