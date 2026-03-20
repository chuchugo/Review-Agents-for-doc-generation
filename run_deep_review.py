#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from agents.deep_reviewer_agent import DeepReviewInputs, run_deep_review
from tools.env import load_repo_dotenv
from tools.io import read_text_file


def main() -> int:
    load_repo_dotenv()
    parser = argparse.ArgumentParser(description="Run deep agent reviewer on a generated doc and source documents.")
    parser.add_argument("--generated-file", default="", help="Path to the generated draft document.")
    parser.add_argument("--generated", default="", help="Inline generated draft content (alternative to --generated-file).")
    parser.add_argument("--source-files", nargs="*", default=[], help="Optional list of authoritative source text files.")
    parser.add_argument("--workspace-root", default=os.getenv("WORKSPACE_ROOT", "./workspace"), help="Workspace root (optional).")
    parser.add_argument("--out", default="", help="Optional output JSON file path.")
    parser.add_argument("--model", default=os.getenv("OPENAI_REVIEW_MODEL", "gpt-4o"), help="OpenAI model name override (if used).")
    parser.add_argument("--strictness", default="standard", help="Numeric strictness mode for numeric-consistency.")
    parser.add_argument("--max-sections", type=int, default=0, help="Optional cap on the number of sections to review (0 = no cap).")
    parser.add_argument(
        "--enable-finding-normalization",
        action="store_true",
        help="Enable finding-normalization + rollup in the deep pipeline (disabled by default for minimal output).",
    )
    args = parser.parse_args()

    if not args.generated and not args.generated_file:
        print("Provide --generated or --generated-file.", flush=True)
        return 2

    generated_text = args.generated or read_text_file(Path(args.generated_file).resolve())
    ws_root = Path(args.workspace_root).resolve()

    source_paths: List[Path] = [Path(p).resolve() for p in (args.source_files or [])]
    source_texts: List[str] = []
    for p in source_paths:
        if p.exists() and p.is_file():
            source_texts.append(read_text_file(p))

    max_sections = args.max_sections if args.max_sections and args.max_sections > 0 else None

    inputs = DeepReviewInputs(
        generated_text=generated_text,
        source_texts=source_texts,
        model=args.model,
        strictness=args.strictness,
        max_sections=max_sections,
        enable_finding_normalization=bool(args.enable_finding_normalization),
    )

    result = run_deep_review(inputs)

    if args.out:
        out_path = Path(args.out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = ws_root / "waypoints" / f"review_findings_{ts}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)

    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

