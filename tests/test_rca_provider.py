import json
import unittest
from urllib import error

from backend.app.rca.provider import (
    RcaProviderConfig,
    RcaProviderError,
    generate_rca_with_provider,
    _post_json,
)


class RcaProviderTest(unittest.TestCase):
    def setUp(self):
        self.context = {
            "severity": "P2 High",
            "severity_score": 7.5,
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
        self.provider_report = {
            "executive_summary": "Database saturation is degrading authentication.",
            "business_impact": "Users may see slow login and payment failures.",
            "technical_rca": "Connection pool saturation is the strongest signal.",
            "remediation_steps": ["Inspect database sessions.", "Scale connection pool."],
            "evidence": [{"service": "database", "metric": "connection_pool_usage"}],
        }

    def test_local_provider_uses_deterministic_report(self):
        report = generate_rca_with_provider(self.context)

        self.assertEqual(report["provider"], "local")
        self.assertEqual(report["model"], "deterministic")
        self.assertIn("database", report["technical_rca"])

    def test_openai_provider_posts_chat_completion_payload(self):
        calls = []

        def fake_post(url, payload, headers, timeout_seconds):
            calls.append((url, payload, headers, timeout_seconds))
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(self.provider_report),
                        }
                    }
                ]
            }

        config = RcaProviderConfig(
            provider="openai",
            model="test-model",
            base_url="https://example.test/v1",
            api_key="test-key",
        )
        report = generate_rca_with_provider(self.context, config, fake_post)

        self.assertEqual(report["provider"], "openai")
        self.assertEqual(report["model"], "test-model")
        self.assertEqual(report["executive_summary"], self.provider_report["executive_summary"])
        self.assertEqual(calls[0][0], "https://example.test/v1/chat/completions")
        self.assertEqual(calls[0][2]["Authorization"], "Bearer test-key")

    def test_ollama_provider_posts_chat_payload(self):
        calls = []

        def fake_post(url, payload, headers, timeout_seconds):
            calls.append((url, payload, headers, timeout_seconds))
            return {
                "message": {
                    "content": json.dumps(self.provider_report),
                }
            }

        config = RcaProviderConfig(
            provider="ollama",
            model="llama3.1",
            base_url="http://localhost:11434",
        )
        report = generate_rca_with_provider(self.context, config, fake_post)

        self.assertEqual(report["provider"], "ollama")
        self.assertEqual(report["model"], "llama3.1")
        self.assertEqual(report["technical_rca"], self.provider_report["technical_rca"])
        self.assertEqual(calls[0][0], "http://localhost:11434/api/chat")
        self.assertEqual(calls[0][1]["format"], "json")

    def test_openai_provider_requires_api_key(self):
        config = RcaProviderConfig(provider="openai", api_key="")

        with self.assertRaises(RcaProviderError):
            generate_rca_with_provider(self.context, config)

    def test_provider_rejects_non_json_content(self):
        def fake_post(url, payload, headers, timeout_seconds):
            return {"message": {"content": "not json"}}

        config = RcaProviderConfig(provider="ollama")

        with self.assertRaises(RcaProviderError):
            generate_rca_with_provider(self.context, config, fake_post)

    def test_http_errors_are_human_readable(self):
        class FakeHttpError(error.HTTPError):
            def read(self):
                return json.dumps(
                    {
                        "error": {
                            "message": "You exceeded your current quota.",
                            "code": "insufficient_quota",
                        }
                    }
                ).encode("utf-8")

        def fake_urlopen(request, timeout):
            raise FakeHttpError(
                request.full_url,
                429,
                "Too Many Requests",
                hdrs=None,
                fp=None,
            )

        import backend.app.rca.provider as provider

        previous_urlopen = provider.request.urlopen
        provider.request.urlopen = fake_urlopen
        try:
            with self.assertRaises(RcaProviderError) as exc:
                _post_json("https://example.test", {}, {}, 30)
        finally:
            provider.request.urlopen = previous_urlopen

        self.assertIn("You exceeded your current quota.", str(exc.exception))
        self.assertIn("insufficient_quota", str(exc.exception))
        self.assertNotIn('"error"', str(exc.exception))


if __name__ == "__main__":
    unittest.main()
