from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

try:
    from openai import OpenAI  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    OpenAI = None  # type: ignore

try:
    # Optional dependency: only needed if you want the LangGraph/DeepAgents wrapper.
    from deepagents import create_deep_agent  # type: ignore
    from deepagents.backends.filesystem import FilesystemBackend  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    create_deep_agent = None  # type: ignore
    FilesystemBackend = None  # type: ignore

from .prompts import (
    CONTEXT_FIDELITY_SYSTEM_FALLBACK,
    DEFAULT_SYSTEM_PROMPT,
    OPENAI_API_KEY_REQUIRED_MESSAGE,
    OPENAI_PACKAGE_MISSING_MESSAGE,
    SECTION_REVIEW_PARSE_ERROR_MESSAGE,
    build_section_review_user_prompt,
    section_review_system_prompt_paths,
)
from .tools import calculator, convert_rtf_to_json, extract_docx, run_cmd, run_regulatory_review


@lru_cache(maxsize=1)
def _load_system_prompt() -> str:
    here = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(here, os.pardir))
    for p in section_review_system_prompt_paths(repo_root):
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            continue

    return CONTEXT_FIDELITY_SYSTEM_FALLBACK


def _openai_client() -> OpenAI:
    if OpenAI is None:
        raise RuntimeError(OPENAI_PACKAGE_MISSING_MESSAGE)
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(OPENAI_API_KEY_REQUIRED_MESSAGE)
    return OpenAI(api_key=key)


def _extract_json_blob(text: str) -> Dict[str, Any] | None:
    json_match = re.search(r"\{[\s\S]*\}", text)
    if not json_match:
        return None
    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError:
        return None


def run_context_fidelity_review(
    *,
    section_text: str,
    source_context: List[str] | None = None,
    model: str | None = None,
) -> Dict[str, Any]:
    """
    Runs the section LLM review for a single slice of text (used by the numeric-consistency skill).

    System and user prompts are defined in `agents.prompts` and `skills/numeric-consistency/prompts/`.

    Returns parsed JSON-like dict with optional `data_points` and `findings`.
    """
    source_context = source_context or []
    system = _load_system_prompt()
    user = build_section_review_user_prompt(section_text=section_text, source_context=source_context)

    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model=model or os.environ.get("OPENAI_REVIEW_MODEL", "gpt-4o"),
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.1,
            max_tokens=4096,
        )

        text = (resp.choices[0].message.content or "").strip()
        parsed = _extract_json_blob(text)

        if not parsed:
            # Keep output shape stable for the caller; they can decide how to surface errors.
            return {
                "content": text[:1000],
                "findings": [],
                "data_points": [],
                "_parse_error": SECTION_REVIEW_PARSE_ERROR_MESSAGE,
            }

        # Normalize expected keys
        parsed.setdefault("content", "")
        parsed.setdefault("findings", [])
        parsed.setdefault("data_points", [])
        return parsed
    except Exception as e:
        # Make the pipeline runnable even without `openai` installed or without API key.
        return {
            "content": "",
            "findings": [],
            "data_points": [],
            "_error": str(e),
        }


def build_agent(*, checkpointer: Any):
    """
    Create a Deep Agent (a compiled LangGraph) using the DeepAgents wrapper.

    This is an integration layer; the minimal pipeline in this repo does not require it.
    """
    if create_deep_agent is None or FilesystemBackend is None:
        raise RuntimeError(
            "deepagents is not installed. Install it (and its dependencies) to use build_agent(), "
            "or call run_context_fidelity_review/run_deep_review.py directly for the minimal pipeline."
        )

    workspace_root = Path(os.getenv("WORKSPACE_ROOT", "./workspace")).resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)

    model = os.getenv("MODEL", "openai:gpt-4o-mini")

    backend = FilesystemBackend(root_dir=str(workspace_root), virtual_mode=True)

    agent = create_deep_agent(
        name="deep-langgraph-chat",
        model=model,
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        tools=[calculator, convert_rtf_to_json, extract_docx, run_cmd, run_regulatory_review],
        subagents=[],
        backend=backend,
        skills=["/skills/"],
        memory=["/AGENTS.md"],
        checkpointer=checkpointer,
    )

    return agent

