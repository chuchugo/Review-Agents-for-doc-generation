from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.paired_io import ReviewPair, discover_pairs_from_layout, load_pair_texts


class TestPairedIO(unittest.TestCase):
    def test_discovers_matching_stems(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "generated").mkdir()
            (root / "source").mkdir()
            (root / "generated" / "studyA.md").write_text("# Doc\n", encoding="utf-8")
            (root / "source" / "studyA.txt").write_text("Source N=100", encoding="utf-8")
            (root / "generated" / "orphan.md").write_text("x", encoding="utf-8")

            pairs = discover_pairs_from_layout(root)
            self.assertEqual(len(pairs), 1)
            self.assertIsInstance(pairs[0], ReviewPair)
            self.assertEqual(pairs[0].stem, "studyA")

            gen, src = load_pair_texts(pairs[0])
            self.assertIn("Doc", gen)
            self.assertIn("100", src)

    def test_missing_subdirs_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            pairs = discover_pairs_from_layout(Path(td))
            self.assertEqual(pairs, [])


if __name__ == "__main__":
    unittest.main()
