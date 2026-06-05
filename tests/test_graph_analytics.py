import unittest

import pandas as pd

from backend.app.graph.analytics import (
    analyze_incident_cluster,
    get_blast_radius,
    get_failure_propagation_paths,
    infer_probable_root_cause,
    rank_service_risk,
)
from backend.app.graph.dependency_graph import build_service_graph


class GraphAnalyticsTest(unittest.TestCase):
    def setUp(self):
        self.graph = build_service_graph()

    def test_database_has_upstream_blast_radius(self):
        blast_radius = get_blast_radius("database", self.graph)

        self.assertIn("auth-service", blast_radius)
        self.assertIn("payment-service", blast_radius)
        self.assertIn("api-gateway", blast_radius)

    def test_failure_propagation_path_reverses_dependency_direction(self):
        paths = get_failure_propagation_paths(
            "database",
            ["auth-service", "payment-service", "api-gateway"],
            self.graph,
        )

        self.assertIn(["database", "auth-service"], paths)
        self.assertIn(["database", "auth-service", "payment-service"], paths)

    def test_service_risk_ranking_contains_graph_metrics(self):
        ranking = rank_service_risk(self.graph)

        self.assertFalse(ranking.empty)
        self.assertIn("risk_score", ranking)
        self.assertIn("betweenness_centrality", ranking)
        self.assertGreater(ranking.iloc[0]["blast_radius_count"], 0)

    def test_infer_probable_root_cause_uses_graph_and_time(self):
        cluster = pd.DataFrame(
            [
                {"timestamp": "2026-06-04T10:00:00", "service": "database"},
                {"timestamp": "2026-06-04T10:02:00", "service": "auth-service"},
                {"timestamp": "2026-06-04T10:04:00", "service": "payment-service"},
                {"timestamp": "2026-06-04T10:05:00", "service": "api-gateway"},
            ]
        )

        root_cause = infer_probable_root_cause(cluster, self.graph)

        self.assertEqual(root_cause["service"], "database")
        self.assertEqual(root_cause["affected_coverage"], 1.0)

    def test_analyze_incident_cluster_returns_propagation_context(self):
        cluster = pd.DataFrame(
            [
                {"timestamp": "2026-06-04T10:00:00", "service": "database"},
                {"timestamp": "2026-06-04T10:02:00", "service": "auth-service"},
                {"timestamp": "2026-06-04T10:04:00", "service": "payment-service"},
            ]
        )

        analysis = analyze_incident_cluster(cluster, self.graph)

        self.assertEqual(analysis["probable_root_service"], "database")
        self.assertTrue(analysis["propagation_paths"])


if __name__ == "__main__":
    unittest.main()
