from __future__ import annotations

import unittest

from skills.skill_registry import get_skill_runner


class TestFindingNormalization(unittest.TestCase):
    def setUp(self) -> None:
        self.normalize_findings = get_skill_runner("finding-normalization")

    def test_maps_raw_finding_via_legacy_context_fidelity_param(self) -> None:
        raw = {
            "findings": [
                {
                    "type": "source_mismatch",
                    "severity": "major",
                    "description": "Value differs",
                    "recommendation": "Fix table",
                    "location": "row 3",
                }
            ]
        }
        out = self.normalize_findings(
            section_title="Methods",
            section_text="...",
            context_fidelity_result=raw,
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["type"], "source_mismatch")
        self.assertEqual(out[0]["severity"], "major")
        self.assertIn("id", out[0])
        self.assertEqual(out[0]["location"]["section_title"], "Methods")

    def test_maps_raw_finding_via_numeric_consistency_param(self) -> None:
        """Unified skill output should be passed as numeric_consistency_result."""
        raw = {
            "findings": [
                {
                    "finding_type": "dose_mismatch",
                    "severity": "critical",
                    "description": "Dose wrong",
                    "recommendation": "Align with protocol",
                    "location": "paragraph 2",
                }
            ]
        }
        out = self.normalize_findings(
            section_title="Dosage",
            section_text="10 mg",
            numeric_consistency_result=raw,
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["type"], "dose_mismatch")
        self.assertEqual(out[0]["severity"], "critical")

    def test_empty_findings(self) -> None:
        out = self.normalize_findings(
            section_title="X",
            section_text="",
            context_fidelity_result={"findings": []},
        )
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()
