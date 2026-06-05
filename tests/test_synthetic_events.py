import tempfile
import unittest
from pathlib import Path

from backend.app.generator.synthetic_events import (
    DEFAULT_DATASET_SIZES,
    EVENT_FIELDS,
    METRIC_PROFILES,
    generate_synthetic_events,
    write_datasets,
)


class SyntheticEventsTest(unittest.TestCase):
    def test_generated_events_match_schema_and_labels(self):
        events = generate_synthetic_events(event_count=250, seed=7)

        self.assertEqual(len(events), 250)
        self.assertEqual(set(events[0]), set(EVENT_FIELDS))
        self.assertTrue(any(event["known_anomaly"] for event in events))
        self.assertTrue(any(not event["known_anomaly"] for event in events))

        metrics = {event["metric"] for event in events}
        self.assertTrue(metrics.issubset(METRIC_PROFILES))

        anomaly = next(event for event in events if event["known_anomaly"])
        self.assertNotEqual(anomaly["root_cause_label"], "None")
        self.assertIsNotNone(anomaly["incident_id"])

    def test_write_datasets_creates_expected_files(self):
        with tempfile.TemporaryDirectory() as directory:
            files = write_datasets(output_dir=directory, sizes=(10, 20), seed=3)
            names = {path.name for path in files}

            self.assertEqual(names, {"synthetic_events.json", "synthetic_events_10.json", "synthetic_events_20.json"})
            for path in files:
                self.assertTrue(Path(path).exists())

    def test_default_sizes_are_roadmap_sizes(self):
        self.assertEqual(DEFAULT_DATASET_SIZES, (1000, 5000, 10000))


if __name__ == "__main__":
    unittest.main()