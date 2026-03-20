---
name: finding-normalization
description: Convert raw reviewer observations into the common finding schema used by the review runtime and UI.
---

# Finding Normalization

## When to use
Use this skill after a reviewer has identified issues but before the results are stored, merged, or displayed.

## When not to use
- Do not use to create new findings.
- Do not use to merge findings across different agents.

## Inputs
- raw reviewer observations
- agent id
- optional severity defaults

## Outputs
- findings conforming to `contracts/finding.schema.json`

## Procedure
1. Assign stable finding ids.
2. Map issue text to a finding type.
3. Normalize severity and blocking flags.
4. Preserve evidence and recommendation fields.
5. Return schema-compliant findings.

