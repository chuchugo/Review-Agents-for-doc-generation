## deep-agent-reviewer

## Quick Start (Minimal Design)

Minimal deep agent reviewer runs section-based review via the unified **numeric-consistency** skill (source fidelity + numeric checks) and emits structured JSON.

### API key (`.env`)
Copy `.env.example` to `.env` in the repo root and set `OPENAI_API_KEY`. `run_review.py` and `run_deep_review.py` load `.env` automatically via `python-dotenv`. `.env` is gitignored.

### Run (deep pipeline)
```sh
python3 run_deep_review.py \
  --generated-file path/to/generated.md \
  --source-files path/to/source1.txt path/to/source2.txt \
  --workspace-root ./workspace \
  --out ./workspace/waypoints/out.json
```

By default, the deep pipeline is minimal and does not run `finding-normalization`.
It outputs per-section `numeric_consistency` only (one skill pass per section).

To include `normalized_findings` + rollup, run with:
`--enable-finding-normalization`

### Run (single section)
```sh
python3 run_review.py \
  --doc "..." \
  --workspace-root ./memories \
  --out ./memories/out.json
```

See `memories/README.md` for the demo workspace layout (`input/source_context.txt`).

### Offline mode
If the Python `openai` package is missing (or `OPENAI_API_KEY` is not set), the review step returns JSON with an `_error` field instead of crashing.

### Finding normalization contract
`finding-normalization` (and `contracts/finding.schema.json`) is extra surface area you can remove now and reintroduce later when you add more skills and need consistent finding IDs/types/severity mapping.

## Project Structure (Minimal)
- `agents/reviewer_agent.py`: LLM section reviewer (`run_context_fidelity_review`, used by the numeric-consistency skill) + optional `deepagents` wrapper (`build_agent`)
- `agents/deep_reviewer_agent.py`: deep pipeline orchestrator (splits -> reviews -> optional normalization)
- `agents/tools.py`: tool functions exposed to a DeepAgent/LangGraph-style runtime
- `run_review.py`: single-section runner (thin wrapper)
- `run_deep_review.py`: deep pipeline runner (writes `waypoints/review_findings_<timestamp>.json` or `--out`)
- `skills/numeric-consistency/`: unified skill (source/context fidelity + numeric traceability); `SKILL.md`, `prompts/context_fidelity_system.md`, `agent.py`, `scripts/run_review.py`
- `skills/finding-normalization/`: finding-normalization skill + mapper (disabled by default)
- `tools/section_splitter.py`: markdown heading-based section splitter
- `contracts/finding.schema.json`: output contract used only when finding-normalization is enabled

## Workflow (How a Review Starts)
1. Run `run_deep_review.py` with `--generated-file` (or `--generated`) and optional `--source-files`.
2. The deep pipeline splits the generated markdown into sections.
3. For each section it runs:
   - `numeric-consistency` (single skill: former context fidelity + numeric checks in one pass)
   - optionally `finding-normalization` (only with `--enable-finding-normalization`)
4. It writes one JSON file with `sections[]` and (optionally) `normalized_findings` + rollup.

Standalone numeric-consistency skill package designed to be used:

- as a CLI (see entrypoint below) for direct section review vs provided source context, and
- as a callable skill/tool from other Deep Agents workspaces (for example, `deep-langgraph-chat`).

This folder is intended to be moved as a self-contained sibling next to `deep-langgraph-chat/` and `Reviewer_Agent/`.

## Layout (revised)

- `agents/` contains the OpenAI prompt loader + `run_context_fidelity_review` (invoked by the numeric-consistency skill).
- `skills/` contains the skill contracts (`SKILL.md`) and the runnable script:
  - `skills/numeric-consistency/scripts/run_review.py`

## Workspace IO

The runner reads from and writes to the `WORKSPACE_ROOT` path provided by the caller environment.
In `deep-langgraph-chat`, that means it will read `input/` and write `waypoints/review_findings_*.json`.

1) Architecture design (deep agent reviewer)
The working “deep agent reviewer” in this repo is organized into a small pipeline plus pluggable skills:

Entrypoints

run_review.py: runs a single numeric-consistency section review (thin wrapper)
run_deep_review.py: runs the full section-based deep review pipeline and writes JSON output
Pipeline orchestrator

agents/deep_reviewer_agent.py
splits the generated document into sections
runs the numeric-consistency skill per section (unified LLM review; `numeric_checks[]` reserved for future programmatic rules)
runs finding-normalization per section only when `--enable-finding-normalization` is set (disabled by default for minimal output)
Skill execution / OpenAI-skill adaptability layer

skills/skill_registry.py: runs skills by name through a consistent interface
skills/openai_skill_adapter.py: provides OpenAI tool/function schema stubs for each skill (so you can later plug this into OpenAI tool-calling without changing the pipeline logic)
Skills (contract-driven)

skills/numeric-consistency/
SKILL.md (unified contract)
prompts/context_fidelity_system.md (system prompt for the LLM pass)
agent.py (calls `run_context_fidelity_review`, adds `numeric_checks` / `summary` / `meta`)
scripts/run_review.py (standalone runner)
skills/finding-normalization/
SKILL.md (contract already existed)
agent.py (runtime mapping into contracts/finding.schema.json)
Core prompt + reviewer implementation

agents/reviewer_agent.py
loads the system prompt from `skills/numeric-consistency/prompts/` (with legacy fallbacks)
if openai/OPENAI_API_KEY is missing, it returns structured JSON with _error instead of crashing (so the system “works” offline)
Input/Output scaffolding

tools/section_splitter.py: markdown heading-based section splitter
contracts/finding.schema.json: contract used for normalized findings (extra surface area for minimal output)
Deep output is written to waypoints/review_findings_<timestamp>.json (or your --out path)
2) Review workflow (how to start a review)
Prepare inputs

Generated draft: a .txt or markdown file (the “generated” content)
Authoritative source(s): one or more .txt files (optional for now, but supported)
Run the deep pipeline

Offline (will still produce JSON; LLM sections will contain _error):
python3 run_deep_review.py --generated-file path/to/generated.md --source-files path/to/source1.txt path/to/source2.txt --workspace-root ./workspace
With OpenAI (real context fidelity + mismatch extraction):
export OPENAI_API_KEY=...
python3 run_deep_review.py --generated-file ... --source-files ... --workspace-root ./workspace
Find the output

Default output location:
./workspace/waypoints/review_findings_<timestamp>.json
The JSON contains:
sections[] with `numeric_consistency` per section.
`normalized_findings` and `rollup.normalized_finding_counts_by_severity` appear only when `--enable-finding-normalization` is set.
3) “OpenAI skills adaptable” changes
Skills now have a consistent runtime boundary:
each skill has an agent.py executor (or a runner for standalone execution)
skills/skill_registry.py dispatches by skill name
OpenAI compatibility scaffolding is in place:
skills/openai_skill_adapter.py returns tool/function schemas you can pass into OpenAI tool-calling later
The pipeline no longer hardcodes direct imports for every skill; it calls skills through the registry, making it easy to add/replace skills without reworking the orchestrator.
4) Space for input/output (what to pass, what you get)
Inputs
Deep reviewer CLI:

--generated-file or --generated (inline)
--source-files (optional list)
You can later extend this to read from WORKSPACE_ROOT/input/generated/* and WORKSPACE_ROOT/input/source/* without changing the review core.
Numeric-consistency standalone runner (what `run_review.py` delegates to):

reads --content (the section text)
optionally reads sources from:
input/source_context.txt
or input/source_context/source_context.txt
or input/source_context/**/*.txt
or input/source/**/*.txt
Outputs
run_deep_review.py writes one JSON file to:
waypoints/review_findings_<timestamp>.json (or --out)
Output shape includes:
sections[]
normalized_findings[] mapped toward `contracts/finding.schema.json` (only when `--enable-finding-normalization` is set)
If you tell me what your “final” UI expects (finding fields, severity mapping, and how you want evidence/locations represented), I can tighten the normalization mapping and extend programmatic `numeric_checks[]` beyond the LLM pass.# Review-Agents-for-doc-generation
