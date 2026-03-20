#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _load_source_context(workspace_root: Path, *, source_files: List[str] | None) -> List[str]:
    if source_files:
        ctx: List[str] = []
        for sf in source_files:
            p = Path(sf)
            if p.exists() and p.is_file():
                ctx.append(_read_text_file(p))
        return ctx

    candidates: List[Path] = [
        workspace_root / "input" / "source_context.txt",
        workspace_root / "input" / "source_context" / "source_context.txt",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return [_read_text_file(c)]

    dir_c = workspace_root / "input" / "source_context"
    if dir_c.exists() and dir_c.is_dir():
        txts = sorted(dir_c.glob("**/*.txt"))
        return [_read_text_file(p) for p in txts if p.is_file()]

    dir_s = workspace_root / "input" / "source"
    if dir_s.exists() and dir_s.is_dir():
        txts = sorted(dir_s.glob("**/*.txt"))
        return [_read_text_file(p) for p in txts if p.is_file()]

    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Run numeric-consistency skill (single-section, unified review).")
    parser.add_argument("doc_path", help="Path/identifier for traceability (does not need to exist).")
    parser.add_argument("--content", required=True, help="Generated section content to review.")
    parser.add_argument(
        "--workspace-root",
        default=os.getenv("WORKSPACE_ROOT", "./workspace"),
        help="Workspace root containing input/ and where outputs may be written.",
    )
    parser.add_argument(
        "--source-file",
        action="append",
        default=[],
        help="Optional: supply one or more authoritative source text files.",
    )
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(_repo_root() / ".env")
    except ImportError:
        pass

    sys.path.insert(0, str(_repo_root()))

    ws_root = Path(args.workspace_root).resolve()
    source_context = _load_source_context(ws_root, source_files=args.source_file or None)

    from skills.skill_registry import run_skill

    result = run_skill(
        "numeric-consistency",
        section_text=args.content,
        evidence_chunks=source_context,
    )

    payload = {
        "doc_path": args.doc_path,
        "generated": {
            "section_text_len": len(args.content or ""),
        },
        "source_context": {
            "num_excerpts": len(source_context),
            "source_total_chars": sum(len(s) for s in source_context),
        },
        "numeric_consistency": result,
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "workspace_root": str(ws_root),
            "openai_api_key_present": bool(os.getenv("OPENAI_API_KEY")),
        },
    }

    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
