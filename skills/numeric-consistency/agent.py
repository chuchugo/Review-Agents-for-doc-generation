from __future__ import annotations

from typing import Any, Dict, List

from agents.reviewer_agent import run_context_fidelity_review


def run_numeric_consistency(
    *,
    section_text: str,
    evidence_chunks: List[str] | None = None,
    document_type: str | None = None,
    product_type: str | None = None,
    lifecycle_stage: str | None = None,
    strictness: str = "standard",
    model: str | None = None,
) -> Dict[str, Any]:
    """
    Numeric consistency skill — single entry point for section review.

    Performs source/context fidelity and numeric datapoint reconciliation via the same
    LLM pass (formerly a separate “context fidelity” skill). Structured numeric_checks[]
    may be filled later for programmatic rules; findings and data_points carry the review today.
    """
    review = run_context_fidelity_review(
        section_text=section_text,
        source_context=evidence_chunks or [],
        model=model,
    )
    numeric_checks: List[Dict[str, Any]] = list(review.get("numeric_checks") or [])
    out: Dict[str, Any] = {
        **review,
        "numeric_checks": numeric_checks,
        "summary": {
            "total_checks": len(numeric_checks),
            "strictness": strictness,
        },
        "meta": {
            **(review.get("meta") if isinstance(review.get("meta"), dict) else {}),
            "skill": "numeric-consistency",
            "document_type": document_type,
            "product_type": product_type,
            "lifecycle_stage": lifecycle_stage,
            "evidence_chunks_provided": bool(evidence_chunks),
        },
    }
    return out
