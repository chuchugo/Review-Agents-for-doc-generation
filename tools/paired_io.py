from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

# Text-like extensions for generated vs source documents
_GENERATED_SUFFIXES = {".md", ".txt", ".markdown"}
_SOURCE_SUFFIXES = {".txt", ".md", ".json", ".rtf"}


@dataclass(frozen=True)
class ReviewPair:
    """One generated document paired with its authoritative source (same logical name)."""

    stem: str
    generated_path: Path
    source_path: Path


def _default_memories_input(repo_root: Path) -> Path:
    return repo_root / "memories" / "input"


def discover_pairs_from_layout(
    input_root: Path,
    *,
    generated_subdir: str = "generated",
    source_subdir: str = "source",
) -> List[ReviewPair]:
    """
    Discover paired files under::

        <input_root>/generated/<stem>.<ext>
        <input_root>/source/<stem>.<ext>

    Only pairs where both files exist (same ``stem``, any allowed extension) are returned.
    If multiple extensions exist for the same stem, the first match per side wins
    (prefer ``.md`` then ``.txt`` for generated; ``.txt`` first for source).
    """
    gen_dir = input_root / generated_subdir
    src_dir = input_root / source_subdir
    if not gen_dir.is_dir() or not src_dir.is_dir():
        return []

    def stems_in(directory: Path, allowed: set[str]) -> dict[str, Path]:
        out: dict[str, Path] = {}
        for p in sorted(directory.iterdir()):
            if not p.is_file() or p.suffix.lower() not in allowed:
                continue
            stem = p.stem
            if stem not in out:
                out[stem] = p
        return out

    gen_map = stems_in(gen_dir, _GENERATED_SUFFIXES)
    src_map = stems_in(src_dir, _SOURCE_SUFFIXES)

    pairs: List[ReviewPair] = []
    for stem in sorted(set(gen_map) & set(src_map)):
        pairs.append(
            ReviewPair(
                stem=stem,
                generated_path=gen_map[stem],
                source_path=src_map[stem],
            )
        )
    return pairs


def load_pair_texts(pair: ReviewPair, *, encoding: str = "utf-8") -> Tuple[str, str]:
    """Read (generated_text, source_text) for a pair."""
    gen = pair.generated_path.read_text(encoding=encoding, errors="replace")
    src = pair.source_path.read_text(encoding=encoding, errors="replace")
    return gen, src


def iter_review_pairs(repo_root: Optional[Path] = None) -> Iterator[ReviewPair]:
    """
    Convenience: iterate pairs from ``<repo_root>/memories/input`` using the
    default ``generated/`` + ``source/`` layout.
    """
    root = repo_root or Path(__file__).resolve().parents[1]
    for p in discover_pairs_from_layout(_default_memories_input(root)):
        yield p
