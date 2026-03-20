#!/usr/bin/env python3
"""
Thin CLI wrapper for the numeric-consistency skill (single-section review).

Usage examples:

  export OPENAI_API_KEY=...   # required for a real model review
  python run_review.py --doc "..." --workspace-root ./workspace
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from tools.env import load_repo_dotenv


def main() -> int:
    load_repo_dotenv()
    parser = argparse.ArgumentParser(description="Run deep-agent-reviewer against a draft and sources.")
    parser.add_argument("--doc", default="", help="Draft document content (inline).")
    parser.add_argument("--doc-file", default="", help="Path to draft document file.")
    parser.add_argument("--workspace-root", default="", help="Workspace root containing input/ and waypoints/ (default: $WORKSPACE_ROOT or ./workspace).")
    parser.add_argument("--out", default="", help="Optional path to write JSON result.")
    parser.add_argument(
        "--require-openai",
        action="store_true",
        help="If set, the command will fail when OPENAI_API_KEY is missing (default: allow offline execution).",
    )
    args = parser.parse_args()

    if args.require_openai and not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY in the environment.", file=sys.stderr)
        return 1

    project_root = Path(__file__).parent.resolve()
    if args.workspace_root:
        ws_root = Path(args.workspace_root).resolve()
    else:
        ws_root = Path(os.getenv("WORKSPACE_ROOT", "./workspace")).resolve()
    os.environ.setdefault("WORKSPACE_ROOT", str(ws_root))

    script_path = project_root / "skills" / "numeric-consistency" / "scripts" / "run_review.py"
    if not script_path.exists():
        print(f"Review script not found at {script_path}", file=sys.stderr)
        return 1

    # This wrapper is intentionally minimal: the runner reads sources from WORKSPACE_ROOT/input/.
    # We pass the draft content via --content and use a synthetic document_path for traceability.
    draft_content = args.doc
    if args.doc_file:
        p = Path(args.doc_file).resolve()
        draft_content = p.read_text(encoding="utf-8", errors="replace")

    if not draft_content:
        print("Provide --doc or --doc-file with draft content.", file=sys.stderr)
        return 1

    synthetic_doc_path = "out/numeric_consistency_draft.txt"

    cmd = ["python3", str(script_path), synthetic_doc_path, "--content", draft_content]

    env = os.environ.copy()
    proc = subprocess.run(
        cmd,
        cwd=str(ws_root),
        env=env,
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        print(proc.stderr or "Review failed", file=sys.stderr)
        return proc.returncode

    output = proc.stdout or "{}"

    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        parsed = {"raw": output}

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(json.dumps(parsed, indent=2, default=str), encoding="utf-8")
    else:
        print(json.dumps(parsed, indent=2, default=str))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

