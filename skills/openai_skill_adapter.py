from __future__ import annotations

from typing import Any, Dict


def numeric_consistency_tool_schema() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "numeric_consistency",
            "description": (
                "Unified section review: source/context fidelity, numeric datapoint traceability, and structured "
                "number checks. Pass evidence_chunks for authoritative excerpts; omit for internal-consistency-only review."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "section_text": {"type": "string"},
                    "evidence_chunks": {"type": "array", "items": {"type": "string"}},
                    "strictness": {"type": "string", "enum": ["standard", "strict", "lenient"]},
                    "model": {"type": "string"},
                },
                "required": ["section_text"],
                "additionalProperties": False,
            },
        },
    }


def finding_normalization_tool_schema() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "finding_normalization",
            "description": "Normalize upstream findings into contracts/finding.schema.json shape.",
            "parameters": {
                "type": "object",
                "properties": {
                    "section_title": {"type": "string"},
                    "section_text": {"type": "string"},
                    "context_fidelity_result": {"type": "object"},
                    "numeric_consistency_result": {"type": "object"},
                    "agent_id": {"type": "string"},
                },
                "required": ["section_title", "section_text"],
                "additionalProperties": True,
            },
        },
    }


def tool_schemas_for_openai() -> Dict[str, Dict[str, Any]]:
    return {
        "numeric_consistency": numeric_consistency_tool_schema(),
        "finding_normalization": finding_normalization_tool_schema(),
    }

