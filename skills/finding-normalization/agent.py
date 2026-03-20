from __future__ import annotations

from typing import Any, Dict, List


def _severity_normalize(value: Any, default: str = "informational") -> str:
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"critical", "major", "minor", "informational"}:
            return v
    return default


def normalize_findings(
    *,
    section_title: str,
    section_text: str,
    context_fidelity_result: Dict[str, Any] | None = None,
    numeric_consistency_result: Dict[str, Any] | None = None,
    agent_id: str = "deep-agent-reviewer",
    severity_defaults: Dict[str, str] | None = None,
) -> List[Dict[str, Any]]:
    """
    Minimal finding normalizer.

    - Maps `findings` from upstream review payloads into `contracts/finding.schema.json` shape (best-effort).
    - `context_fidelity_result` may be omitted when using the unified numeric-consistency skill; pass the same
      dict as `numeric_consistency_result` (or only `context_fidelity_result`) so findings are still normalized.
    """
    severity_defaults = severity_defaults or {}
    default_sev = severity_defaults.get(agent_id, "informational")

    if (
        context_fidelity_result
        and numeric_consistency_result
        and context_fidelity_result is not numeric_consistency_result
    ):
        raw_findings = (context_fidelity_result.get("findings", []) or []) + (
            numeric_consistency_result.get("findings", []) or []
        )
    else:
        raw_findings = (context_fidelity_result or numeric_consistency_result or {}).get("findings", []) or []
    normalized: List[Dict[str, Any]] = []

    # Map context-fidelity findings -> contract schema.
    for i, f in enumerate(raw_findings):
        f_type = f.get("finding_type") or f.get("type") or "inconsistency"
        recommendation = f.get("recommendation") or f.get("fix") or "Update to align with the authoritative source."
        description = f.get("description") or f.get("evidence") or "Finding requires review."

        location = f.get("location")
        text_quote = None
        section_title_used = section_title or "Unknown section"
        if isinstance(location, str) and location.strip():
            text_quote = location.strip()[:500]
        elif isinstance(location, dict):
            # Best-effort support for richer location objects.
            text_quote = (
                location.get("text_quote")
                or location.get("quote")
                or location.get("excerpt")
            )

        normalized.append(
            {
                "id": f.get("id") or f"{agent_id}-{section_title_used}-{i}",
                "type": str(f_type),
                "severity": _severity_normalize(f.get("severity"), default=default_sev),
                "blocking": bool(f.get("blocking", f.get("is_blocking", False))),
                "summary": str(description)[:220],
                "description": str(description),
                "recommendation": str(recommendation),
                "location": {
                    "section_title": section_title_used,
                    "text_quote": text_quote,
                },
                "evidence": f.get("evidence") or [],
                "raw": f,
            }
        )

    return normalized

