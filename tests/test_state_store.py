import json
import tempfile
import unittest
from pathlib import Path

from stockmonitor.services.state_store import StateStore


class StateStoreTests(unittest.TestCase):
    def test_save_and_load_offsets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            store = StateStore(path)

            store.save_offsets(40, -15)

            self.assertEqual(store.load_offsets(), (40, -15))
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["horizontal_offset"], 40)
            self.assertEqual(data["vertical_offset"], -15)

    def test_load_offsets_returns_none_for_invalid_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            path.write_text(
                json.dumps(
                    {
                        "horizontal_offset": "abc",
                        "vertical_offset": 10,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            store = StateStore(path)

            self.assertIsNone(store.load_offsets())


if __name__ == "__main__":
    unittest.main()
