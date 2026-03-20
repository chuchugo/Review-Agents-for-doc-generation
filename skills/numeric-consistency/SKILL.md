---
name: numeric-consistency
description: Unified regulatory section review — source/context fidelity, numeric datapoint traceability, and structured number-mismatch checks (single skill).
---

# Numeric consistency skill

## Purpose
One skill covers what was previously split between “context fidelity” and “numeric consistency”:

- **Source and narrative fidelity**: Compare the generated section to authoritative excerpts when provided; flag wrong numbers, wording drift, missing or unsupported claims, and contradictions.
- **Numeric reconciliation**: Enumerate and trace numerical datapoints (doses, n/N, percentages, stats, time windows, units) to source or internal consistency rules.
- **Structured number checks**: Use `check_type` values (percent vs counts, totals, arm consistency, CI range, p-values, rounding, units, table vs narrative, derived metrics) in findings and `data_points` where applicable.

When no source is provided, the same pass performs **internal consistency** and guideline-oriented review of the section only.

## When to use
- Any regulatory or clinical document section that must align with protocol, CSR tables, TFLs, or other evidence excerpts.
- Whenever you need both **qualitative/source fidelity** and **numeric traceability** in one structured JSON result.

## Inputs (executor)
- **section_text** — Section under review (plain or lightly formatted text).
- **evidence_chunks** — Optional list of authoritative source strings (same role as former `source_context`).
- **document_type**, **product_type**, **lifecycle_stage** — Optional context for future rule tuning.
- **strictness** — `standard` | `strict` | `lenient` (passed through to skill metadata; LLM tolerances follow the system prompt).
- **model** — Optional OpenAI model override.

## Outputs
Returns a single JSON object combining the review payload with numeric-skill scaffolding:

- **content**, **data_points**, **findings**, **severity**, **confidence** — Primary review result (same shape as the legacy context-fidelity reviewer).
- **numeric_checks** — Reserved for explicit programmatic checks; may be empty when all signals are expressed in `findings` / `data_points`.
- **summary** — e.g. `total_checks`, `strictness`.
- **meta** — Skill name, flags, optional `_error` / `_parse_error` from the model layer.

## Procedure
1. Load system prompt from `skills/numeric-consistency/prompts/context_fidelity_system.md` (via `run_context_fidelity_review` in code).
2. Compare section to `evidence_chunks` when present; otherwise run internal-consistency review.
3. Emit findings with recommendations; include `check_type` on numeric-related rows when possible.
4. Return unified payload above.

## Validation
- Findings must stay scoped to the provided section text only.
- Every finding should include an actionable **recommendation** when possible.

## Aliases
Callers may still request `context-fidelity-review` or `context_fidelity_review` in `skill_registry` — they resolve to this same skill for backward compatibility.
