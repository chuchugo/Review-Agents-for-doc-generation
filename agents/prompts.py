"""Prompt templates and tool descriptions for the reviewer deep agent."""

from __future__ import annotations

import os
from typing import List

# --- OpenAI section review (numeric-consistency / run_context_fidelity_review) ---

SECTION_REVIEW_MAX_SECTION_CHARS = 10_000
SECTION_REVIEW_MAX_SOURCE_CHARS = 25_000

SECTION_REVIEW_USER_HEADER = (
    "=== SECTION TO REVIEW (ONLY REPORT FINDINGS FROM THIS TEXT) ===\n"
)

SECTION_REVIEW_CONTENT_TRUNCATION_NOTE = "\n\n[Content truncated - {total_chars} total characters]"

SOURCE_DOCUMENTS_HEADER = "=== AUTHORITATIVE SOURCE DOCUMENT(S) - COMPARE AGAINST THIS ===\n"

SOURCE_DOCUMENTS_INTRO = (
    "The following is the source document that the generated document should match. "
    "Focus on numerical datapoints and their traceability to this source.\n\n"
)

SOURCE_TEXT_JOINER = "\n\n---\n\n"

SOURCE_REFERENCE_TRUNCATION_NOTE = "\n\n[Reference truncated - {total_chars} total characters]"

REVIEW_INSTRUCTIONS_WITH_SOURCE = """\n\n=== REVIEW INSTRUCTIONS ===
**SOURCE COMPARISON REQUIRED**: Compare the section under review against the source above. \
Flag every mismatch: wrong numbers (dose, dates, percentages), different wording, missing facts, \
added claims not in source, contradictions. For each mismatch include source_value and reviewed_value in the finding.
Return your analysis in JSON with content, data_points (if applicable), findings, severity, confidence."""

REVIEW_INSTRUCTIONS_NO_SOURCE = (
    "No authoritative source document was provided. "
    "Perform internal consistency and guideline-based review of the section only. "
    "Return JSON with content, findings, severity, confidence."
)

OPENAI_PACKAGE_MISSING_MESSAGE = (
    "Missing dependency: `openai` python package is not installed. "
    "Install it in the runtime environment (e.g. `pip install openai`)."
)

OPENAI_API_KEY_REQUIRED_MESSAGE = (
    "OPENAI_API_KEY is required to run section review (numeric-consistency / context fidelity pass)."
)

SECTION_REVIEW_PARSE_ERROR_MESSAGE = "Could not extract JSON from model output."


def section_review_system_prompt_paths(repo_root: str) -> List[str]:
    """Absolute paths to try for the section-review system prompt (markdown on disk)."""
    return [
        os.path.join(
            repo_root,
            "skills",
            "numeric-consistency",
            "prompts",
            "context_fidelity_system.md",
        ),
        os.path.join(repo_root, "skills", "numeric-consistency", "context_fidelity_system.md"),
    ]


def build_section_review_user_prompt(
    *,
    section_text: str,
    source_context: List[str],
    max_section_chars: int = SECTION_REVIEW_MAX_SECTION_CHARS,
    max_source_chars: int = SECTION_REVIEW_MAX_SOURCE_CHARS,
) -> str:
    """User message for a single-section LLM review (source-backed or internal-only)."""
    raw_section = section_text or ""
    doc_snippet = (raw_section or "(empty)")[:max_section_chars]
    if len(raw_section) > max_section_chars:
        doc_snippet += SECTION_REVIEW_CONTENT_TRUNCATION_NOTE.format(total_chars=len(raw_section))

    user = SECTION_REVIEW_USER_HEADER + doc_snippet + "\n\n"

    sources_text = SOURCE_TEXT_JOINER.join(source_context) if source_context else ""
    if sources_text:
        user += SOURCE_DOCUMENTS_HEADER + SOURCE_DOCUMENTS_INTRO
        if len(sources_text) <= max_source_chars:
            user += sources_text
        else:
            user += sources_text[:max_source_chars] + SOURCE_REFERENCE_TRUNCATION_NOTE.format(
                total_chars=len(sources_text)
            )
        user += REVIEW_INSTRUCTIONS_WITH_SOURCE
    else:
        user += REVIEW_INSTRUCTIONS_NO_SOURCE

    return user


REVIEW_WORKFLOW_INSTRUCTIONS = """# Regulatory Review Workflow

Follow this workflow for document review and datapoint traceability requests:

1. **Plan**: For multi-file or large reviews, use `write_todos` to break work into clear steps (extract → locate source context → run review → summarize).
2. **Confirm inputs**:
   - Generated document: workspace-relative path (e.g. `out/AB54321_CSR_Outline.md`).
   - Authoritative source text: expected under `input/source_context.txt`, `input/source_context/source_context.txt`, or `input/source/**/*.txt` (the regulatory review tool loads these automatically).
3. **Extract text when needed**: For `.docx` inputs, use `extract_docx` with a **non-empty** workspace-relative path. Do **not** use `run_cmd` with ad-hoc Python one-liners against `Document(...)`—empty or bad paths fail with `PackageNotFoundError`.
4. **Run the review**: Call `run_regulatory_review` with `document_path` and optional `section_ids` (comma-separated), e.g. `"Section 3"` or `"Section 1,Section 2"`. This runs the **numeric-consistency** skill once per section (unified source fidelity + numeric datapoint review).
5. **Interpret results**: Tool output is JSON (`documentPath`, `reviewedAt`, `sectionIds`, `findings`, `sections`). If the response is truncated, open the referenced file under `waypoints/review_findings_<slug>.json` for the full payload.
6. **Respond**: Give a short, actionable summary—prioritize critical/major findings, cite section titles, and point to exact fix guidance from findings.

## Source and scope
- When source files are present, findings should reflect **traceability** to those excerpts (numbers, dates, dosing, stats).
- When no source is available, reviews still run but focus on internal consistency and structured numeric checks.

## Skills for section review
Workspace **skills** live under `skills/` (your agent is configured with access to `/skills/`). The review playbook is a single skill:
- **`skills/numeric-consistency/SKILL.md`** — Unified **numeric-consistency** skill: source/context fidelity, numeric datapoint traceability, and structured `check_type` guidance (percent vs counts, totals, arms, CI, p-values, units, table vs narrative, etc.). Legacy names `context-fidelity-review` / `context_fidelity_review` still resolve to this same skill in the registry.
- **End-to-end pass**: **`run_regulatory_review`** invokes that skill per section; read the SKILL when you need rules, severities, or manual spot-checks with **`calculator`**.

## Optional helpers
- **calculator**: Verify simple arithmetic (percent vs counts, sums) when validating a finding; keep expressions to numeric literals and basic operators.
- **run_cmd**: Use sparingly for workspace-local scripting or utilities; prefer dedicated tools for DOCX and review.
- **convert_rtf_to_json**: Not implemented in this workspace; do not rely on it until available.

## Document authoring (separate from review)
If the user asks to create or modify a Word document, follow the docx skill at `skills/docx/SKILL.md` (path relative to workspace root; no leading slash).
"""

REVIEW_TOOLS_CATALOG = """## Available tools (review agent)

1. **extract_docx** — Extract text from a `.docx` at a workspace-relative path (required non-empty path).
2. **run_regulatory_review** — Run per-section **numeric-consistency** skill (source fidelity + numeric checks in one pass); optional `section_ids` filter; optional inline `content` instead of reading from disk. See `skills/numeric-consistency/SKILL.md`.
3. **calculator** — Safe evaluation of simple numeric expressions (literals + arithmetic).
4. **run_cmd** — Shell command with captured stdout/stderr (use with care; stay within workspace policies).
5. **convert_rtf_to_json** — Placeholder; not implemented in this package yet.
"""

DEEP_AGENT_BASE_INSTRUCTIONS = """You are a Deep Agent built on LangGraph.

Goals:
- Be accurate and safe.
- Prefer short, actionable answers.
- When helpful, break complex tasks into a todo list and execute step-by-step.

Workspace rules:
- Only read/write within the configured workspace root.
"""

DEFAULT_SYSTEM_PROMPT = (
    DEEP_AGENT_BASE_INSTRUCTIONS.strip()
    + "\n\n"
    + REVIEW_WORKFLOW_INSTRUCTIONS.strip()
    + "\n\n"
    + REVIEW_TOOLS_CATALOG.strip()
)

TASK_DESCRIPTION_PREFIX = """Delegate a task to a specialized sub-agent with isolated context. Available agents for delegation are:
{other_agents}
"""

SUBAGENT_DELEGATION_INSTRUCTIONS = """# Sub-Agent Review Coordination

Use sub-agents only when the workspace is configured with review sub-agents (e.g. one agent per section family or per source document). Default deployment uses a single orchestrator.

## Delegation strategy
- **Default**: One orchestrator run with `run_regulatory_review` over the full document or selected `section_ids` is usually enough.
- **Parallelize** when sections are large and independent: assign disjoint `section_ids` batches to sub-agents so each returns JSON findings for merge.
- **Avoid churn**: Do not split a single section across sub-agents unless explicitly required.

## Limits
- Use at most {max_concurrent_review_units} parallel sub-agents per iteration when parallelizing.
- Cap delegation rounds at {max_reviewer_iterations}; stop early when findings stabilize or the user’s questions are answered.
"""

CONTEXT_FIDELITY_SYSTEM_FALLBACK = (
    "You are an expert Regulatory Context Fidelity Reviewer. "
    "Compare the section under review against the authoritative source. "
    "Return JSON with `content`, `data_points` (optional) and `findings`, "
    "including `recommendation` for each finding."
)
