# Memories — input (paired generated + source)

Place **paired** documents here for batch or scripted reviews. The default layout is:

```
memories/input/
  generated/   # draft / CSR section / model output
    studyA.md
    studyB.md
  source/      # authoritative source for that draft (same base name)
    studyA.txt
    studyB.txt
```

**Pairing rule:** same **stem** (filename without extension), e.g. `studyA.md` ↔ `studyA.txt`.

Supported extensions:

- **generated/** — `.md`, `.txt`, `.markdown`
- **source/** — `.txt`, `.md`, `.json`, `.rtf`

The helper `tools.paired_io.discover_pairs_from_layout()` returns `ReviewPair` objects for each matching stem.

## Output

Review JSON is written under `memories/output/` when you use runners that target that path, or under `WORKSPACE_ROOT/waypoints/` for CLI defaults—see repo `README.md`.
