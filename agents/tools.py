from __future__ import annotations

import ast
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.io import read_text_file
from tools.section_splitter import split_markdown_sections

try:
    # Matches how `deep-langgraph-chat` registers tool schemas.
    from langchain_core.tools import tool as lc_tool  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    def lc_tool(fn):  # type: ignore
        return fn


@lc_tool
def calculator(expression: str) -> Dict[str, Any]:
    """
    Safe-ish arithmetic evaluator for simple expressions.

    This intentionally supports only numeric literals and arithmetic operators.
    """

    expression = (expression or "").strip()
    if not expression:
        raise ValueError("calculator: expression must be non-empty")

    allowed_binops = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b,
        ast.Pow: lambda a, b: a**b,
        ast.Mod: lambda a, b: a % b,
        ast.FloorDiv: lambda a, b: a // b,
    }
    allowed_unary = {ast.UAdd: lambda a: +a, ast.USub: lambda a: -a}

    def eval_node(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return eval_node(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_binops:
            return allowed_binops[type(node.op)](eval_node(node.left), eval_node(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_unary:
            return allowed_unary[type(node.op)](eval_node(node.operand))
        raise ValueError(f"calculator: unsupported expression node: {type(node).__name__}")

    tree = ast.parse(expression, mode="eval")
    return {"expression": expression, "value": eval_node(tree)}


@lc_tool
def run_cmd(command: str, *, timeout_seconds: int = 60) -> Dict[str, Any]:
    """
    Execute a shell command and return stdout/stderr.

    Note: callers should sanitize input; this tool is intentionally minimal.
    """
    if not (command or "").strip():
        raise ValueError("run_cmd: command must be non-empty")

    proc = subprocess.run(
        command,
        shell=True,
        cwd=os.getcwd(),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


@lc_tool
def convert_rtf_to_json(rtf_path: str) -> Dict[str, Any]:
    """
    Placeholder for future RTF -> JSON conversion.
    """
    raise NotImplementedError("convert_rtf_to_json is not implemented in this minimal package yet.")


@lc_tool
def extract_docx(docx_path: str) -> Dict[str, Any]:
    """
    Placeholder for future DOCX text extraction.
    """
    raise NotImplementedError("extract_docx is not implemented in this minimal package yet.")


def _load_default_source_context(workspace_root: Path) -> List[str]:
    candidates: List[Path] = [
        workspace_root / "input" / "source_context.txt",
        workspace_root / "input" / "source_context" / "source_context.txt",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return [read_text_file(c)]

    dir_c = workspace_root / "input" / "source_context"
    if dir_c.exists() and dir_c.is_dir():
        txts = sorted(dir_c.rglob("*.txt"))
        if txts:
            return [read_text_file(p) for p in txts if p.is_file()]

    dir_s = workspace_root / "input" / "source"
    if dir_s.exists() and dir_s.is_dir():
        txts = sorted(dir_s.rglob("*.txt"))
        return [read_text_file(p) for p in txts if p.is_file()]

    return []


@lc_tool
def run_regulatory_review(
    document_path: str,
    section_ids: Optional[str] = None,
    content: Optional[str] = None,
) -> str:
    """
 
    Signature:
    - document_path: workspace-relative path (e.g. "out/AB54321_CSR_Outline.md") OR filename-only.
    - section_ids: optional comma-separated selector:
      - "Section 3,Section 5" (recommended)
      - "1,3" (interpreted as section numbers)
      - free-text substrings matched against section titles
    - content: optional raw document content; if omitted, content is read from `document_path`.

    Returns:
    - JSON string with keys: documentPath, reviewedAt, sectionIds, findings, sections

    Minimal mode:
    - runs per-section numeric-consistency skill (unified source fidelity + numeric review)
    - does NOT run finding-normalization
    """
    from datetime import datetime, timezone
    import json
    import re

    workspace_root = Path(os.getenv("WORKSPACE_ROOT", "./workspace")).resolve()

    # Resolve document path under workspace.
    raw_doc = (document_path or "").strip()
    if not raw_doc:
        raise ValueError("document_path cannot be empty")

    ws_document = Path(raw_doc)
    if not ws_document.is_absolute():
        ws_document = workspace_root / raw_doc

    if content is None:
        generated_text = read_text_file(ws_document) if ws_document.exists() else ""
    else:
        generated_text = content

    sections = split_markdown_sections(generated_text)
    source_context = _load_default_source_context(workspace_root)

    # Resolve section_ids selector.
    wanted = set()
    tokens = [t.strip() for t in (section_ids or "").split(",") if t.strip()]
    if tokens:
        for t in tokens:
            m = re.match(r"^section\\s+(\\d+)$", t, flags=re.IGNORECASE)
            if m:
                idx = int(m.group(1)) - 1
                if 0 <= idx < len(sections):
                    wanted.add(idx)
                continue

            if t.isdigit():
                idx = int(t) - 1
                if 0 <= idx < len(sections):
                    wanted.add(idx)
                continue

            # Substring match on title.
            for i, s in enumerate(sections):
                title = (s.get("title") or "").lower()
                if t.lower() in title:
                    wanted.add(i)
    else:
        wanted = set(range(len(sections)))

    from skills.skill_registry import get_skill_runner

    run_numeric_consistency = get_skill_runner("numeric-consistency")

    reviewed_at = datetime.now(timezone.utc).isoformat()
    section_results: List[Dict[str, Any]] = []
    flattened_findings: List[Dict[str, Any]] = []

    for idx, s in enumerate(sections):
        if idx not in wanted:
            continue
        title = s.get("title") or f"Section {idx + 1}"
        text = s.get("text") or ""

        numeric_result = run_numeric_consistency(
            section_text=text,
            evidence_chunks=source_context,
            strictness=os.getenv("NUMERIC_STRICTNESS", "standard"),
            model=os.getenv("OPENAI_REVIEW_MODEL"),
        )

        section_results.append(
            {
                "section_index": idx,
                "section_title": title,
                "numeric_consistency": numeric_result,
            }
        )

        for f in numeric_result.get("findings", []) or []:
            if isinstance(f, dict):
                flattened_findings.append(f)

    # Best-effort persistence (so UI-like consumers can load it later).
    # Output file name is based on document_path.
    slug = re.sub(r"[^\\w\\-]", "_", raw_doc.replace("/", "_"))
    out_dir = workspace_root / "waypoints"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"review_findings_{slug}.json"

    payload = {
        "documentPath": raw_doc,
        "reviewedAt": reviewed_at,
        "sectionIds": section_ids,
        "sources": {
            "num_excerpts": len(source_context),
            "total_chars": sum(len(s) for s in source_context),
        },
        "findings": flattened_findings,
        "sections": section_results,
    }
    full_output = json.dumps(payload, indent=2, default=str)
    out_path.write_text(full_output, encoding="utf-8")

    # Match `deep-langgraph-chat` behavior: cap tool output size and return a summary.
    max_chars = 12_000
    if len(full_output) <= max_chars:
        return full_output

    findings = payload.get("findings", []) or []
    summary = {
        "documentPath": payload.get("documentPath", raw_doc),
        "reviewedAt": payload.get("reviewedAt"),
        "sectionIds": payload.get("sectionIds"),
        "findingsCount": len(findings),
        "findings": findings[:20],
        "_truncated": True,
        "_fullResultsFile": f"waypoints/review_findings_{slug}.json",
    }
    return json.dumps(summary, indent=2, default=str)

