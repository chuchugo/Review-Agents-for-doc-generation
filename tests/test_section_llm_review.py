"""
Tests for `run_context_fidelity_review` — the OpenAI call behind the numeric-consistency skill.

Stable offline: with no key / no SDK the implementation returns `_error` and empty lists.
"""

from __future__ import annotations

import unittest

from agents.reviewer_agent import run_context_fidelity_review
from skills.skill_registry import run_skill


class TestSectionLlmReview(unittest.TestCase):
    def test_returns_stable_keys(self) -> None:
        out = run_context_fidelity_review(
            section_text="The dose was 10 mg.",
            source_context=["Study drug: 10 mg IV."],
        )
        self.assertIsInstance(out, dict)
        self.assertIn("findings", out)
        self.assertIn("data_points", out)
        self.assertIn("content", out)
        self.assertTrue(
            "_error" in out or "_parse_error" in out or isinstance(out.get("findings"), list)
        )


class TestNumericConsistencySkillViaRegistry(unittest.TestCase):
    """Public entry point wraps the same LLM pass with `numeric_checks` / `summary` / `meta`."""

    def test_run_skill_includes_envelope(self) -> None:
        out = run_skill("numeric-consistency", section_text="n=10", evidence_chunks=["Table: n=10"])
        self.assertIn("findings", out)
        self.assertIn("data_points", out)
        self.assertIn("numeric_checks", out)
        self.assertIsInstance(out["numeric_checks"], list)
        self.assertIn("summary", out)
        self.assertEqual(out["summary"].get("strictness"), "standard")
        self.assertEqual(out["meta"].get("skill"), "numeric-consistency")
        self.assertTrue(out["meta"].get("evidence_chunks_provided"))


if __name__ == "__main__":
    unittest.main()
