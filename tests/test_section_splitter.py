from __future__ import annotations

import unittest

from tools.section_splitter import split_markdown_sections


class TestSplitMarkdownSections(unittest.TestCase):
    def test_empty_returns_placeholder(self) -> None:
        out = split_markdown_sections("   \n  ")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["title"], "Empty document")

    def test_no_headings_full_document(self) -> None:
        text = "Plain paragraph.\nNo headings here."
        out = split_markdown_sections(text)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["title"], "Full document")
        self.assertEqual(out[0]["text"], text)

    def test_multiple_headings(self) -> None:
        text = "# Title\n\nintro\n\n## Methods\n\nWe used 10 mg.\n\n## Results\n\np=0.04\n"
        out = split_markdown_sections(text)
        self.assertGreaterEqual(len(out), 2)
        titles = [s["title"] for s in out]
        self.assertIn("Methods", titles)
        self.assertIn("Results", titles)

    def test_max_sections_caps(self) -> None:
        text = "# A\na\n# B\nb\n# C\nc\n"
        out = split_markdown_sections(text, max_sections=1)
        self.assertEqual(len(out), 1)


if __name__ == "__main__":
    unittest.main()
