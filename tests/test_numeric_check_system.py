"""
Tests for the numeric-consistency / section-review stack:

- User prompt construction (`agents.prompts`)
- Skill output envelope (`skills.numeric-consistency.agent`)
- `run_context_fidelity_review` behavior with mocked OpenAI (no network)
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agents.prompts import (
    REVIEW_INSTRUCTIONS_NO_SOURCE,
    SECTION_REVIEW_PARSE_ERROR_MESSAGE,
    SECTION_REVIEW_USER_HEADER,
    build_section_review_user_prompt,
    section_review_system_prompt_paths,
)
from agents.reviewer_agent import run_context_fidelity_review
from skills.skill_registry import get_skill_runner


def _numeric_skill_module():
    """Skill agent binds `run_context_fidelity_review` at import time; patch it on this module."""
    run_numeric = get_skill_runner("numeric-consistency")
    return sys.modules[run_numeric.__module__]


class TestBuildSectionReviewUserPrompt(unittest.TestCase):
    def test_empty_section_uses_placeholder(self) -> None:
        u = build_section_review_user_prompt(section_text="", source_context=[])
        self.assertIn("(empty)", u)
        self.assertIn(SECTION_REVIEW_USER_HEADER, u)
        self.assertIn(REVIEW_INSTRUCTIONS_NO_SOURCE, u)

    def test_with_source_includes_authoritative_block_and_comparison_instructions(self) -> None:
        u = build_section_review_user_prompt(
            section_text="Dose 10 mg daily.",
            source_context=["Protocol: 10 mg QD."],
        )
        self.assertIn("=== AUTHORITATIVE SOURCE DOCUMENT(S)", u)
        self.assertIn("Protocol: 10 mg QD.", u)
        self.assertIn("SOURCE COMPARISON REQUIRED", u)
        self.assertIn("Dose 10 mg daily.", u)

    def test_multiple_sources_joined(self) -> None:
        u = build_section_review_user_prompt(
            section_text="x",
            source_context=["A", "B"],
        )
        self.assertIn("A", u)
        self.assertIn("B", u)
        self.assertIn("---", u)

    def test_long_section_truncated(self) -> None:
        long_text = "a" * 50
        u = build_section_review_user_prompt(
            section_text=long_text,
            source_context=[],
            max_section_chars=20,
        )
        self.assertIn("a" * 20, u)
        self.assertIn("[Content truncated - 50 total characters]", u)

    def test_long_source_truncated(self) -> None:
        src = "s" * 100
        u = build_section_review_user_prompt(
            section_text="ok",
            source_context=[src],
            max_source_chars=30,
        )
        # Only first 30 chars of source material plus truncation note
        self.assertIn("s" * 30, u)
        self.assertNotIn("s" * 31, u.split("[Reference truncated")[0])
        self.assertIn("[Reference truncated - 100 total characters]", u)


class TestSectionReviewSystemPromptPaths(unittest.TestCase):
    def test_paths_target_numeric_consistency_skill_layout(self) -> None:
        root = str(Path(__file__).resolve().parents[1])
        paths = section_review_system_prompt_paths(root)
        self.assertGreaterEqual(len(paths), 2)
        self.assertTrue(any(p.endswith(os.path.join("prompts", "context_fidelity_system.md")) for p in paths))
        self.assertTrue(any(p.endswith("context_fidelity_system.md") for p in paths))

    def test_primary_prompt_file_exists_in_repo(self) -> None:
        root = str(Path(__file__).resolve().parents[1])
        primary = section_review_system_prompt_paths(root)[0]
        self.assertTrue(Path(primary).is_file(), f"missing system prompt at {primary}")


class TestNumericConsistencySkillEnvelope(unittest.TestCase):
    def test_wraps_review_with_summary_meta_and_numeric_checks(self) -> None:
        fake_review = {
            "content": "done",
            "findings": [{"id": "1"}],
            "data_points": [{"value": 10}],
            "severity": "minor",
        }
        run_numeric = get_skill_runner("numeric-consistency")
        with patch.object(
            _numeric_skill_module(),
            "run_context_fidelity_review",
            return_value=fake_review,
        ):
            out = run_numeric(
                section_text="body",
                evidence_chunks=["evidence"],
                strictness="strict",
                document_type="CSR",
                product_type="mAb",
                lifecycle_stage="Phase3",
            )
        self.assertEqual(out["content"], "done")
        self.assertEqual(out["findings"], [{"id": "1"}])
        self.assertEqual(out["numeric_checks"], [])
        self.assertEqual(out["summary"]["total_checks"], 0)
        self.assertEqual(out["summary"]["strictness"], "strict")
        self.assertEqual(out["meta"]["skill"], "numeric-consistency")
        self.assertTrue(out["meta"]["evidence_chunks_provided"])
        self.assertEqual(out["meta"]["document_type"], "CSR")
        self.assertEqual(out["meta"]["product_type"], "mAb")
        self.assertEqual(out["meta"]["lifecycle_stage"], "Phase3")

    def test_merges_existing_meta_from_llm_payload(self) -> None:
        run_numeric = get_skill_runner("numeric-consistency")
        with patch.object(
            _numeric_skill_module(),
            "run_context_fidelity_review",
            return_value={"findings": [], "data_points": [], "meta": {"trace": "x"}},
        ):
            out = run_numeric(section_text="z", evidence_chunks=None)
        self.assertEqual(out["meta"]["trace"], "x")
        self.assertEqual(out["meta"]["skill"], "numeric-consistency")


class TestRunContextFidelityReviewMockedOpenAI(unittest.TestCase):
    """Valid JSON and parse failures without calling the real API."""

    def setUp(self) -> None:
        self._patch_openai_class = patch("agents.reviewer_agent.OpenAI")
        self.mock_openai_cls = self._patch_openai_class.start()
        self.addCleanup(self._patch_openai_class.stop)

    def _make_completion(self, content: str) -> MagicMock:
        msg = MagicMock()
        msg.content = content
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    def test_parses_model_json_and_normalizes_keys(self) -> None:
        payload = {"content": "ok", "findings": [{"type": "x"}], "extra": 1}
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._make_completion(json.dumps(payload))
        self.mock_openai_cls.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False):
            out = run_context_fidelity_review(section_text="s", source_context=[])

        self.assertEqual(out["content"], "ok")
        self.assertEqual(len(out["findings"]), 1)
        self.assertEqual(out["data_points"], [])
        self.assertEqual(out.get("extra"), 1)
        mock_client.chat.completions.create.assert_called_once()
        call_kw = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(len(call_kw["messages"]), 2)
        self.assertEqual(call_kw["messages"][0]["role"], "system")
        self.assertEqual(call_kw["messages"][1]["role"], "user")

    def test_partial_json_gets_defaulted_lists(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._make_completion('{"content": "only"}')
        self.mock_openai_cls.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False):
            out = run_context_fidelity_review(section_text="s", source_context=[])

        self.assertEqual(out["content"], "only")
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["data_points"], [])

    def test_non_json_model_output_yields_parse_error_shape(self) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._make_completion("Sorry, here is prose only.")
        self.mock_openai_cls.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False):
            out = run_context_fidelity_review(section_text="s", source_context=[])

        self.assertEqual(out["_parse_error"], SECTION_REVIEW_PARSE_ERROR_MESSAGE)
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["data_points"], [])

    def test_json_embedded_in_fenced_block_still_extracted(self) -> None:
        body = 'Here you go:\n```json\n{"content": "c", "findings": []}\n```'
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._make_completion(body)
        self.mock_openai_cls.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False):
            out = run_context_fidelity_review(section_text="s", source_context=[])

        self.assertEqual(out["content"], "c")


class TestDeepAgentSystemPromptMentionsNumericSkill(unittest.TestCase):
    def test_default_system_prompt_references_numeric_consistency(self) -> None:
        from agents.prompts import DEFAULT_SYSTEM_PROMPT

        self.assertIn("numeric-consistency", DEFAULT_SYSTEM_PROMPT.lower())
        self.assertIn("run_regulatory_review", DEFAULT_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
