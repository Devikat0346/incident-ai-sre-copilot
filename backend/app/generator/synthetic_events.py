import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path


DEFAULT_DATASET_SIZES = (1000, 5000, 10000)

EVENT_FIELDS = (
    "timestamp",
    "service",
    "metric",
    "value",
    "severity",
    "environment",
    "region",
    "deployment_version",
    "known_anomaly",
    "root_cause_label",
    "incident_id",
    "message",
)

SERVICES = (
    "api-gateway",
    "auth-service",
    "payment-service",
    "database",
    "notification-service",
    "checkout-service",
    "inventory-service",
    "queue-worker",
)

ENVIRONMENTS = ("prod", "staging")
REGIONS = ("us-east-1", "us-west-2", "eu-west-1")
DEPLOYMENT_VERSIONS = ("v1.8.2", "v1.8.3", "v1.9.0", "v1.9.1")

METRIC_PROFILES = {
    "latency_ms": {"baseline": 320, "stddev": 95, "minimum": 35, "maximum": 3000, "threshold": 1000},
    "error_rate": {"baseline": 1.1, "stddev": 0.9, "minimum": 0, "maximum": 40, "threshold": 5},
    "cpu_usage": {"baseline": 48, "stddev": 14, "minimum": 5, "maximum": 99, "threshold": 85},
    "memory_usage": {"baseline": 58, "stddev": 13, "minimum": 10, "maximum": 99, "threshold": 90},
    "connection_pool_usage": {"baseline": 45, "stddev": 15, "minimum": 5, "maximum": 99, "threshold": 80},
    "queue_depth": {"baseline": 42, "stddev": 30, "minimum": 0, "maximum": 650, "threshold": 250},
    "5xx_rate": {"baseline": 0.8, "stddev": 0.8, "minimum": 0, "maximum": 45, "threshold": 5},
}

ROOT_CAUSE_PATTERNS = {
    "Database Saturation": {
        "primary_service": "database",
        "impacted_services": ("auth-service", "payment-service", "api-gateway"),
        "metrics": ("connection_pool_usage", "latency_ms", "cpu_usage"),
    },
    "Deployment Regression": {
        "primary_service": "checkout-service",
        "impacted_services": ("api-gateway", "payment-service"),
        "metrics": ("latency_ms", "error_rate", "5xx_rate"),
    },
    "Network Failure": {
        "primary_service": "api-gateway",
        "impacted_services": ("auth-service", "payment-service", "notification-service"),
        "metrics": ("latency_ms", "5xx_rate", "error_rate"),
    },
    "Memory Pressure": {
        "primary_service": "queue-worker",
        "impacted_services": ("notification-service", "checkout-service"),
        "metrics": ("memory_usage", "cpu_usage", "queue_depth"),
    },
    "Queue Backlog": {
        "primary_service": "queue-worker",
        "impacted_services": ("checkout-service", "notification-service"),
        "metrics": ("queue_depth", "latency_ms", "error_rate"),
    },
    "Auth Failure": {
        "primary_service": "auth-service",
        "impacted_services": ("payment-service", "api-gateway"),
        "metrics": ("error_rate", "latency_ms", "5xx_rate"),
    },
}


def _bounded_normal(profile, rng):
    value = rng.gauss(profile["baseline"], profile["stddev"])
    healthy_max = min(profile["maximum"], profile["threshold"] * 0.92)
    value = max(profile["minimum"], min(healthy_max, value))
    return round(value, 2)


def _anomalous_value(profile, rng):
    threshold = profile["threshold"]
    lower = min(profile["maximum"], threshold * rng.uniform(1.08, 1.35))
    upper = min(profile["maximum"], threshold * rng.uniform(1.45, 2.25))
    return round(rng.uniform(lower, max(lower, upper)), 2)


def _severity(value, threshold):
    ratio = value / threshold
    if ratio >= 1.75:
        return "critical"
    if ratio >= 1.2:
        return "high"
    if ratio >= 0.85:
        return "medium"
    return "low"


def _incident_windows(event_count, rng, anomaly_rate):
    incident_count = max(3, int(event_count * anomaly_rate / 7))
    windows = []

    for incident_number in range(1, incident_count + 1):
        duration = rng.randint(5, 12)
        start_index = rng.randint(0, max(0, event_count - duration - 1))
        windows.append(
            {
                "incident_id": f"INC-SYN-{incident_number:04d}",
                "root_cause_label": rng.choice(tuple(ROOT_CAUSE_PATTERNS)),
                "start": start_index,
                "end": start_index + duration,
            }
        )

    return sorted(windows, key=lambda item: item["start"])


def _active_incident(index, windows):
    for window in windows:
        if window["start"] <= index <= window["end"]:
            return window
    return None


def _choose_service_and_metric(incident, rng):
    if incident is None:
        return rng.choice(SERVICES), rng.choice(tuple(METRIC_PROFILES))

    pattern = ROOT_CAUSE_PATTERNS[incident["root_cause_label"]]
    services = (pattern["primary_service"], *pattern["impacted_services"])
    return rng.choice(services), rng.choice(pattern["metrics"])


def _event_message(service, metric, known_anomaly, root_cause_label):
    if known_anomaly:
        return f"{service} {metric} elevated during {root_cause_label}"
    return f"{service} {metric} remains within expected operating range"


def generate_synthetic_events(event_count=1000, seed=42, start_time=None, anomaly_rate=0.08):
    rng = random.Random(seed)
    start = start_time or datetime(2026, 6, 4, 10, 0, 0)
    windows = _incident_windows(event_count, rng, anomaly_rate)
    events = []

    for index in range(event_count):
        incident = _active_incident(index, windows)
        service, metric = _choose_service_and_metric(incident, rng)
        profile = METRIC_PROFILES[metric]

        known_anomaly = incident is not None and rng.random() < 0.78
        root_cause_label = incident["root_cause_label"] if known_anomaly else "None"
        incident_id = incident["incident_id"] if known_anomaly else None
        value = _anomalous_value(profile, rng) if known_anomaly else _bounded_normal(profile, rng)

        events.append(
            {
                "timestamp": (start + timedelta(minutes=index)).isoformat(),
                "service": service,
                "metric": metric,
                "value": value,
                "severity": _severity(value, profile["threshold"]),
                "environment": rng.choices(ENVIRONMENTS, weights=(0.88, 0.12), k=1)[0],
                "region": rng.choice(REGIONS),
                "deployment_version": rng.choice(DEPLOYMENT_VERSIONS),
                "known_anomaly": known_anomaly,
                "root_cause_label": root_cause_label,
                "incident_id": incident_id,
                "message": _event_message(service, metric, known_anomaly, root_cause_label),
            }
        )

    return events


def write_datasets(output_dir="data", sizes=DEFAULT_DATASET_SIZES, seed=42):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    written_files = []

    for size in sizes:
        events = generate_synthetic_events(event_count=size, seed=seed + size)
        dataset_path = output_path / f"synthetic_events_{size}.json"
        dataset_path.write_text(json.dumps(events, indent=2), encoding="utf-8")
        written_files.append(dataset_path)

        if size == sizes[0]:
            default_path = output_path / "synthetic_events.json"
            default_path.write_text(json.dumps(events, indent=2), encoding="utf-8")
            written_files.append(default_path)

    return written_files


def main():
    parser = argparse.ArgumentParser(description="Generate realistic synthetic observability events.")
    parser.add_argument("--output-dir", default="data")
    parser.add_argument("--sizes", nargs="+", type=int, default=list(DEFAULT_DATASET_SIZES))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    for path in write_datasets(args.output_dir, tuple(args.sizes), args.seed):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
