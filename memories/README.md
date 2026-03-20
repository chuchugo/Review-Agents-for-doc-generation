# `memories/` — local demo workspace

Treat this directory like a small **`WORKSPACE_ROOT`**: put authoritative source text under `input/` so `run_review.py` can load it the same way as `./workspace`.

## Layout

- `input/source_context.txt` — sample protocol excerpt (synthetic; safe to commit).

## Run a single-section review

From the repo root:

```bash
python3 run_review.py \
  --workspace-root ./memories \
  --doc $'## Methods\n\nThe study drug was given at 10 mg once daily. N=100.\n'
```

## Practice note

Using a repo folder for demo I/O is fine. The name **`memories`** here means “local context you keep next to the project,” not LangGraph checkpoint memory.

- For **synthetic** samples (like this file), committing `memories/` is OK.
- For **real** study or sponsor data, either do not commit those files (add paths under `memories/` to `.gitignore`) or use a workspace **outside** the repo.
