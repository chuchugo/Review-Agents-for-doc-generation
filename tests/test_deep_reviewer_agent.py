from __future__ import annotations

import unittest
from unittest.mock import patch

from agents.deep_reviewer_agent import DeepReviewInputs, run_deep_review
from skills.skill_registry import get_skill_runner


def _stub_numeric_runner():
    """Deterministic stand-in for the LLM-backed numeric-consistency skill (no API calls)."""

    def run(**kwargs):
        return {
            "content": "stub section review",
            "findings": [],
            "data_points": [],
            "numeric_checks": [],
            "summary": {"total_checks": 0, "strictness": kwargs.get("strictness", "standard")},
            "meta": {
                "skill": "numeric-consistency",
                "evidence_chunks_provided": bool(kwargs.get("evidence_chunks")),
            },
        }

    return run


def _patched_get_skill_runner(name: str):
    if name == "numeric-consistency":
        return _stub_numeric_runner()
    return get_skill_runner(name)


class TestDeepReviewerAgent(unittest.TestCase):
    """Deep pipeline: split markdown → numeric-consistency per section; optional finding-normalization."""

    def _sample_md(self) -> str:
        return "# Sec\n\nDose 10 mg daily.\n"

    @patch("agents.deep_reviewer_agent.get_skill_runner", side_effect=_patched_get_skill_runner)
    def test_minimal_output_shape_no_normalization(self, _mock: object) -> None:
        result = run_deep_review(
            DeepReviewInputs(
                generated_text=self._sample_md(),
                source_texts=["Protocol: dose 10 mg once daily."],
                enable_finding_normalization=False,
            )
        )
        self.assertIn("sections", result)
        self.assertIn("generated", result)
        self.assertIsInstance(result["generated"], str)
        self.assertEqual(result["generated"], self._sample_md())

        self.assertIn("sources", result)
        self.assertEqual(result["sources"]["num_excerpts"], 1)
        self.assertEqual(result["sources"]["texts"], ["Protocol: dose 10 mg once daily."])

        self.assertNotIn("rollup", result)
        self.assertEqual(len(result["sections"]), 1)
        sec = result["sections"][0]
        self.assertEqual(sec["section_index"], 0)
        self.assertEqual(sec["section_title"], "Sec")
        self.assertIn("numeric_consistency", sec)
        self.assertNotIn("context_fidelity_review", sec)
        self.assertNotIn("normalized_findings", sec)

        nc = sec["numeric_consistency"]
        self.assertEqual(nc["meta"]["skill"], "numeric-consistency")
        self.assertTrue(nc["meta"]["evidence_chunks_provided"])
        self.assertIn("numeric_checks", nc)
        self.assertIn("summary", nc)

    @patch("agents.deep_reviewer_agent.get_skill_runner", side_effect=_patched_get_skill_runner)
    def test_normalization_adds_fields(self, _mock: object) -> None:
        result = run_deep_review(
            DeepReviewInputs(
                generated_text=self._sample_md(),
                source_texts=[],
                enable_finding_normalization=True,
            )
        )
        self.assertIn("rollup", result)
        self.assertIn("normalized_finding_counts_by_severity", result["rollup"])
        self.assertIsInstance(result["rollup"]["normalized_finding_counts_by_severity"], dict)

        sec = result["sections"][0]
        self.assertIn("normalized_findings", sec)
        self.assertIsInstance(sec["normalized_findings"], list)

    @patch("agents.deep_reviewer_agent.get_skill_runner", side_effect=_patched_get_skill_runner)
    def test_multi_section_and_max_sections(self, _mock: object) -> None:
        md = "# A\n\none\n\n# B\n\ntwo\n"
        full = run_deep_review(
            DeepReviewInputs(
                generated_text=md,
                source_texts=[],
                enable_finding_normalization=False,
            )
        )
        self.assertEqual(len(full["sections"]), 2)
        capped = run_deep_review(
            DeepReviewInputs(
                generated_text=md,
                source_texts=[],
                max_sections=1,
                enable_finding_normalization=False,
            )
        )
        self.assertEqual(len(capped["sections"]), 1)
        self.assertEqual(capped["sections"][0]["section_title"], "A")


if __name__ == "__main__":
    unittest.main()
