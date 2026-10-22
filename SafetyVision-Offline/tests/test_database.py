import tempfile
import unittest
from pathlib import Path
from safetyvision.database import EventStore


class EventStoreTests(unittest.TestCase):
    def test_persists_and_returns_events_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = EventStore(root / "events.db", root / "images")
            store.add({"timestamp":"2026-10-22T12:00:00+03:30", "camera_name":"cam1",
                       "issue":"mask", "confidence":0.8, "image_path":"a.jpg"})
            store.add({"timestamp":"2026-10-22T12:01:00+03:30", "camera_name":"cam2",
                       "issue":"helmet", "confidence":0.9, "image_path":"b.jpg"})
            self.assertEqual(store.count(), 2)
            rows = store.recent(10)
            self.assertEqual(rows[0]["camera_name"], "cam2")
            self.assertEqual(rows[1]["camera_name"], "cam1")


if __name__ == "__main__":
    unittest.main()
