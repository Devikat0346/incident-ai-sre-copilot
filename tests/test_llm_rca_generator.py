import unittest

import pandas as pd

from backend.app.rca.llm_generator import build_rca_context, generate_llm_rca_report


class LlmRcaGeneratorTest(unittest.TestCase):
    def test_build_rca_context_extracts_cluster_and_graph_fields(self):
        events = pd.DataFrame(
            [
                {
                    "timestamp": "2026-06-04T10:00:00",
                    "service": "database",
                    "metric": "connection_pool_usage",
                    "value": 95,
                    "ml_anomaly_score": 0.45,
                    "message": "database saturation",
                },
                {
                    "timestamp": "2026-06-04T10:02:00",
                    "service": "auth-service",
                    "metric": "latency_ms",
                    "value": 1800,
                    "ml_anomaly_score": 0.25,
                    "message": "auth latency",
                },
            ]
        )
        graph_analysis = {
            "probable_root_service": "database",
            "blast_radius": ["auth-service", "payment-service"],
            "propagation_paths": [["database", "auth-service"]],
        }

        context = build_rca_context(events, graph_analysis, "P2 High", 7.2)

        self.assertEqual(context["probable_root_service"], "database")
        self.assertEqual(context["affected_services"], ["auth-service", "database"])
        self.assertEqual(len(context["evidence"]), 2)

    def test_generate_llm_rca_report_returns_required_sections(self):
        context = {
            "severity": "P2 High",
            "severity_score": 7.2,
            "probable_root_service": "database",
            "affected_services": ["database", "auth-service"],
            "blast_radius": ["auth-service", "payment-service"],
            "propagation_paths": [["database", "auth-service"]],
            "evidence": [
                {
                    "timestamp": "2026-06-04T10:00:00",
                    "service": "database",
                    "metric": "connection_pool_usage",
                    "value": 95,
                    "ml_anomaly_score": 0.45,
                    "message": "database saturation",
                }
            ],
        }

        report = generate_llm_rca_report(context)

        self.assertIn("executive_summary", report)
        self.assertIn("business_impact", report)
        self.assertIn("technical_rca", report)
        self.assertIn("remediation_steps", report)
        self.assertIn("database", report["technical_rca"])

    def test_generate_llm_rca_report_handles_empty_context(self):
        report = generate_llm_rca_report(build_rca_context(pd.DataFrame(), {}))

        self.assertEqual(report["remediation_steps"], [])
        self.assertIn("No active incident", report["executive_summary"])


if __name__ == "__main__":
    unittest.main()
