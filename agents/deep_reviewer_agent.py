from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from skills.skill_registry import get_skill_runner
from tools.section_splitter import split_markdown_sections


@dataclass
class DeepReviewInputs:
    generated_text: str
    source_texts: List[str]
    model: Optional[str] = None
    strictness: str = "standard"
    max_sections: Optional[int] = None
    enable_finding_normalization: bool = False


def run_deep_review(inputs: DeepReviewInputs) -> Dict[str, Any]:
    """
    Split generated markdown into sections and run the numeric-consistency skill per section.

    When ``enable_finding_normalization`` is True, maps findings through the finding-normalization
    skill and adds a ``rollup`` with severity counts.
    """
    sections_raw = split_markdown_sections(
        inputs.generated_text or "",
        max_sections=inputs.max_sections,
    )

    run_numeric = get_skill_runner("numeric-consistency")
    model = inputs.model or os.getenv("OPENAI_REVIEW_MODEL")

    section_rows: List[Dict[str, Any]] = []
    for idx, s in enumerate(sections_raw):
        title = s.get("title") or f"Section {idx + 1}"
        text = s.get("text") or ""

        numeric_result = run_numeric(
            section_text=text,
            evidence_chunks=list(inputs.source_texts or []),
            strictness=inputs.strictness,
            model=model,
        )

        row: Dict[str, Any] = {
            "section_index": idx,
            "section_title": title,
            "numeric_consistency": numeric_result,
        }

        if inputs.enable_finding_normalization:
            normalize = get_skill_runner("finding-normalization")
            normalized = normalize(
                section_title=title,
                section_text=text,
                numeric_consistency_result=numeric_result,
            )
            row["normalized_findings"] = normalized

        section_rows.append(row)

    out: Dict[str, Any] = {
        "generated": inputs.generated_text,
        "sources": {
            "texts": list(inputs.source_texts or []),
            "num_excerpts": len(inputs.source_texts or []),
        },
        "sections": section_rows,
    }

    if inputs.enable_finding_normalization:
        counts: Dict[str, int] = {}
        for sec in section_rows:
            for f in sec.get("normalized_findings") or []:
                if not isinstance(f, dict):
                    continue
                sev = str(f.get("severity") or "informational").lower()
                counts[sev] = counts.get(sev, 0) + 1
        out["rollup"] = {"normalized_finding_counts_by_severity": counts}

    return out
