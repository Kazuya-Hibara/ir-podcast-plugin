"""Unit tests for nbl_pipeline._extract_id (3 envelope shapes).

Run from repo root: `.venv/bin/python3 -m unittest scripts.test_nbl_pipeline`
"""
import unittest

from scripts.nbl_pipeline import _extract_id


class ExtractIdTest(unittest.TestCase):
    def test_nested(self) -> None:
        # `notebooklm source add --json`
        self.assertEqual(_extract_id('{"source":{"id":"s1"}}', "source"), "s1")

    def test_top_level_id(self) -> None:
        # `notebooklm create --json`
        self.assertEqual(_extract_id('{"id":"n1","title":"x"}', "notebook"), "n1")

    def test_flat_snake_task_id(self) -> None:
        # `notebooklm generate audio --json` (v0.3.4 surface)
        self.assertEqual(
            _extract_id('{"task_id":"t1","status":"pending"}', "task", "artifact", "audio"),
            "t1",
        )

    def test_unknown_shape_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            _extract_id('{"unexpected":"shape"}', "notebook")


if __name__ == "__main__":
    unittest.main()
