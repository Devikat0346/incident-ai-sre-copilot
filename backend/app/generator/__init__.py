__all__ = [
    "DEFAULT_DATASET_SIZES",
    "EVENT_FIELDS",
    "METRIC_PROFILES",
    "generate_synthetic_events",
    "write_datasets",
]


def __getattr__(name):
    if name in __all__:
        from backend.app.generator import synthetic_events

        return getattr(synthetic_events, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
