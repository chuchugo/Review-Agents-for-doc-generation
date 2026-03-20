# Tests — what we cover

## 1. Unit tests

- **Section splitter** — markdown headings, empty doc, `max_sections`.
- **Skill registry** — `numeric-consistency` contract (`summary`, `meta`, `numeric_checks`); legacy names alias to the same runner; unknown skills raise `KeyError`.
- **Numeric check system** (`test_numeric_check_system.py`) — user prompt templates, system prompt paths, skill envelope (mocked LLM dependency), Deep Agent `DEFAULT_SYSTEM_PROMPT`.
- **Section LLM review** (`test_section_llm_review.py`) — `run_context_fidelity_review` stable keys; `run_skill("numeric-consistency", …)` public envelope.
- **Finding normalization** — `context_fidelity_result` (legacy) and `numeric_consistency_result` (current unified skill).
- **Paired I/O** — discovers `generated/` + `source/` pairs by stem.

## 2. Integration tests (deterministic where possible)

- **Deep pipeline** (`test_deep_reviewer_agent.py`) — `run_deep_review()` with **stubbed** numeric-consistency (no OpenAI): `generated` string, `sources.texts` / `num_excerpts`, `sections[].numeric_consistency`, optional `rollup.normalized_finding_counts_by_severity`.
- **`run_regulatory_review` tool** — temp `WORKSPACE_ROOT`, `sources` + `findings` in JSON payload, `waypoints/review_findings_*.json`.

## 3. Contract / shape tests

- Deep review: only `numeric_consistency` per section (no `context_fidelity_review`).
- Regulatory tool JSON: top-level `sources` (`num_excerpts`, `total_chars`), flattened `findings`.

## Run

From repo root:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Optional (if installed):

```bash
pytest tests/ -v
```
