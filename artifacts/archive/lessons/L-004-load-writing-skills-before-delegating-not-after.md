---
date_captured: 2026-09-23
type: lesson
status: active
subsystem: floodmap-frontend
source_blockers: []
tags: [lesson, subagents, technical-writing]
related: ["[[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]]", "[[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]"]
---

# Load technical-writing skills before delegating a document, not while reviewing it

## Rule

When dispatching a subagent to draft a technical document, put "invoke `pstack:technical-writing`
and `pstack:unslop` before writing" in the subagent's own instructions. Do not plan to run the
style pass on the finished output instead.

## Why

Two PRDs were drafted by parallel subagents without either being told to load
`pstack:technical-writing` or `pstack:unslop` first, despite the user's own global instructions
requiring both before writing a technical document. This was only caught because the user asked
"did you invoke pstack to write the PRD?" directly. Fixing it after the fact meant a second pass
over both already-written PRDs (16 semicolon-to-period fixes), rework that a correct subagent
prompt would have avoided entirely.

## How to apply

Any Agent dispatch whose task is "write a PRD / concept page / plan / lesson" needs the skill
invocation stated as a numbered step in the prompt, the same way the prompt states which template
and directory to use. Reviewing prose for style after a subagent hands it back is a safety net, not
a substitute for the subagent following the rule from its first sentence.

## Source blockers

- None. Surfaced from the user's direct question about this session's own PRD-writing process.

## Status history

- **2026-09-23, active.** Captured after re-running `pstack:technical-writing` and `pstack:unslop`
  against two already-drafted PRDs that were never told to load them.
