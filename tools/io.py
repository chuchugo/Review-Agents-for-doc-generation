from __future__ import annotations

from pathlib import Path
from typing import List


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def collect_text_files(root: Path, *, suffix: str = ".txt") -> List[Path]:
    """
    Collect text files recursively under `root`.

    Notes:
    - Uses Path.rglob to avoid shelling out to `find`.
    - Caller can decide how to order results.
    """
    if not root.exists() or not root.is_dir():
        return []
    return sorted([p for p in root.rglob(f"*{suffix}") if p.is_file()])

