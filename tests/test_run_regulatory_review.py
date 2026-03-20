from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from agents.tools import run_regulatory_review


def _exec_regulatory_review(document_path: str, *, section_ids=None, content=None) -> str:
    tool = run_regulatory_review
    if hasattr(tool, "invoke"):
        return tool.invoke(
            {"document_path": document_path, "section_ids": section_ids, "content": content}
        )
    return tool(document_path, section_ids=section_ids, content=content)


class TestRunRegulatoryReviewTool(unittest.TestCase):
    def setUp(self) -> None:
        self._old_ws = os.environ.get("WORKSPACE_ROOT")

    def tearDown(self) -> None:
        if self._old_ws is None:
            os.environ.pop("WORKSPACE_ROOT", None)
        else:
            os.environ["WORKSPACE_ROOT"] = self._old_ws

    def test_writes_waypoints_and_returns_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            os.environ["WORKSPACE_ROOT"] = str(ws)
            (ws / "out").mkdir(parents=True)
            doc = ws / "out" / "trial.md"
            doc.write_text("# Methods\nDose 10 mg.\n", encoding="utf-8")

            raw = _exec_regulatory_review("out/trial.md", section_ids=None, content=None)
            data = json.loads(raw)
            self.assertEqual(data.get("documentPath"), "out/trial.md")
            self.assertIn("reviewedAt", data)
            self.assertIn("sections", data)

            self.assertIn("sources", data)
            self.assertIn("num_excerpts", data["sources"])
            self.assertIn("total_chars", data["sources"])

            self.assertIn("findings", data)
            self.assertIsInstance(data["findings"], list)

            sec0 = (data.get("sections") or [{}])[0]
            self.assertIn("numeric_consistency", sec0)
            self.assertNotIn("context_fidelity_review", sec0)

            self.assertTrue((ws / "waypoints").is_dir())
            json_files = list((ws / "waypoints").glob("review_findings_*.json"))
            self.assertEqual(len(json_files), 1)


if __name__ == "__main__":
    unittest.main()
