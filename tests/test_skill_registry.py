from __future__ import annotations

import unittest

from skills.skill_registry import get_skill_runner, run_skill


class TestSkillRegistry(unittest.TestCase):
    def test_legacy_context_fidelity_names_resolve_to_numeric_skill(self) -> None:
        numeric = get_skill_runner("numeric-consistency")
        self.assertEqual(numeric.__name__, "run_numeric_consistency")
        for name in ("context-fidelity-review", "context_fidelity_review"):
            fn = get_skill_runner(name)
            self.assertEqual(fn.__name__, "run_numeric_consistency")

    def test_numeric_consistency_output_contract(self) -> None:
        fn = get_skill_runner("numeric-consistency")
        out = fn(section_text="n=10", evidence_chunks=[])
        self.assertIn("numeric_checks", out)
        self.assertEqual(out["numeric_checks"], [])
        self.assertIn("summary", out)
        self.assertIn("meta", out)
        self.assertEqual(out["meta"].get("skill"), "numeric-consistency")
        self.assertFalse(out["meta"].get("evidence_chunks_provided"))
        self.assertIn("findings", out)
        self.assertIn("data_points", out)

    def test_unknown_skill_raises(self) -> None:
        with self.assertRaises(KeyError):
            get_skill_runner("no-such-skill")

    def test_run_skill_dispatch(self) -> None:
        out = run_skill("numeric-consistency", section_text="1+1", evidence_chunks=None)
        self.assertIn("summary", out)
        self.assertIn("meta", out)


if __name__ == "__main__":
    unittest.main()
