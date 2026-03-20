"""Load repo-root `.env` into the process environment (optional `python-dotenv`)."""

from __future__ import annotations

from pathlib import Path


def load_repo_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env")
