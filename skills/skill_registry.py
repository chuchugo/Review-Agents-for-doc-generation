from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable, Dict


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _import_from_path(module_name: str, file_path: Path):
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not import {module_name} from {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def _load_numeric_consistency_runner():
    agent_path = _repo_root() / "skills" / "numeric-consistency" / "agent.py"
    mod = _import_from_path("numeric_consistency_agent_registry", agent_path)
    return getattr(mod, "run_numeric_consistency")


def _load_finding_normalizer_runner():
    agent_path = _repo_root() / "skills" / "finding-normalization" / "agent.py"
    mod = _import_from_path("finding_normalization_agent_registry", agent_path)
    return getattr(mod, "normalize_findings")


def get_skill_runner(skill_name: str) -> Callable[..., Any]:
    """
    Central dispatch point for all skill executors.
    """
    skill_name = (skill_name or "").strip().lower()
    if skill_name in {
        "numeric_consistency",
        "numeric-consistency",
        "context_fidelity_review",
        "context-fidelity-review",
        "context fidelity review",
    }:
        return _load_numeric_consistency_runner()

    if skill_name in {"finding_normalization", "finding-normalization", "finding normalization"}:
        return _load_finding_normalizer_runner()

    raise KeyError(f"Unknown skill: {skill_name}")


def run_skill(skill_name: str, **inputs) -> Dict[str, Any]:
    """
    Run a named skill with keyword inputs.
    """
    runner = get_skill_runner(skill_name)
    return runner(**inputs)  # type: ignore[return-value]

