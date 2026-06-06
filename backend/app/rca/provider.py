import json
import os
from dataclasses import dataclass
from typing import Callable
from urllib import error, request

from backend.app.rca.llm_generator import generate_llm_rca_report


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.1"

REQUIRED_REPORT_FIELDS = (
    "executive_summary",
    "business_impact",
    "technical_rca",
    "remediation_steps",
    "evidence",
)


class RcaProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class RcaProviderConfig:
    provider: str = "local"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    timeout_seconds: int = 30


def get_default_provider_config(provider: str) -> RcaProviderConfig:
    provider = (provider or "local").lower()

    if provider == "openai":
        return RcaProviderConfig(
            provider="openai",
            model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            base_url=os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL),
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    if provider == "ollama":
        return RcaProviderConfig(
            provider="ollama",
            model=os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
            base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
        )

    return RcaProviderConfig(provider="local")


def generate_rca_with_provider(
    context,
    config: RcaProviderConfig | None = None,
    http_post: Callable[[str, dict, dict, int], dict] | None = None,
):
    config = config or RcaProviderConfig()
    provider = (config.provider or "local").lower()

    if provider == "local":
        return _with_provider_metadata(generate_llm_rca_report(context), "local", "deterministic")

    if provider == "openai":
        return _generate_openai_compatible_rca(context, config, http_post or _post_json)

    if provider == "ollama":
        return _generate_ollama_rca(context, config, http_post or _post_json)

    raise RcaProviderError(f"Unsupported RCA provider: {config.provider}")


def _generate_openai_compatible_rca(context, config, http_post):
    if not config.api_key:
        raise RcaProviderError("OPENAI_API_KEY is required for the OpenAI-compatible RCA provider.")

    model = config.model or DEFAULT_OPENAI_MODEL
    base_url = (config.base_url or DEFAULT_OPENAI_BASE_URL).rstrip("/")
    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": _user_prompt(context)},
        ],
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }

    response = http_post(f"{base_url}/chat/completions", payload, headers, config.timeout_seconds)
    content = response["choices"][0]["message"]["content"]
    report = _parse_provider_report(content, context)
    return _with_provider_metadata(report, "openai", model)


def _generate_ollama_rca(context, config, http_post):
    model = config.model or DEFAULT_OLLAMA_MODEL
    base_url = (config.base_url or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": _user_prompt(context)},
        ],
    }
    headers = {"Content-Type": "application/json"}

    response = http_post(f"{base_url}/api/chat", payload, headers, config.timeout_seconds)
    content = response["message"]["content"]
    report = _parse_provider_report(content, context)
    return _with_provider_metadata(report, "ollama", model)


def _post_json(url, payload, headers, timeout_seconds):
    encoded_payload = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=encoded_payload, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        message = _extract_provider_error_message(body) or body
        raise RcaProviderError(f"RCA provider HTTP {exc.code}: {message}") from exc
    except error.URLError as exc:
        raise RcaProviderError(f"RCA provider connection failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RcaProviderError("RCA provider returned invalid JSON.") from exc


def _extract_provider_error_message(body):
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None

    provider_error = payload.get("error")
    if isinstance(provider_error, dict):
        message = provider_error.get("message")
        code = provider_error.get("code")
        if message and code:
            return f"{message} ({code})"
        return message or code

    if isinstance(provider_error, str):
        return provider_error

    return payload.get("message")


def _system_prompt():
    return (
        "You are an expert SRE incident commander. Generate concise, production-ready RCA content. "
        "Return only valid JSON with these keys: executive_summary, business_impact, technical_rca, "
        "remediation_steps, evidence. remediation_steps must be an array of strings."
    )


def _user_prompt(context):
    return (
        "Create an incident RCA from this context. Be specific, avoid speculation beyond the evidence, "
        "and use the dependency graph only to explain plausible propagation.\n\n"
        f"{json.dumps(context, default=str, indent=2)}"
    )


def _parse_provider_report(content, context):
    try:
        report = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RcaProviderError("RCA provider response was not valid JSON.") from exc

    fallback = generate_llm_rca_report(context)
    normalized = {}
    for field in REQUIRED_REPORT_FIELDS:
        normalized[field] = report.get(field, fallback.get(field))

    if isinstance(normalized["remediation_steps"], str):
        normalized["remediation_steps"] = [normalized["remediation_steps"]]
    if not isinstance(normalized["remediation_steps"], list):
        normalized["remediation_steps"] = fallback["remediation_steps"]

    if not isinstance(normalized["evidence"], list):
        normalized["evidence"] = fallback["evidence"]

    return normalized


def _with_provider_metadata(report, provider, model):
    enriched = dict(report)
    enriched["provider"] = provider
    enriched["model"] = model
    return enriched
