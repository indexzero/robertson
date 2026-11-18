---
date: 2026-11-07
scope: single-PR prepare
status: passed
---

# Validation

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/kabpr/evals -p 'test_*.py' -v`
passes 22 isolated tests. They cover all four selectors, qualified URLs,
fork identity, ambiguity, missing context, approval binding, resumption,
concurrent edits, readback, incomplete source lists, and merge blockers.
All writes go to temporary state or fake GitHub objects.

An independent agent also used the skill with a real temporary fork
checkout and a fake `gh` executable. It exercised inspection, drafting,
simulated approval, application, interruption/resume, an outside-checkout
request, and a changed head. Both successful PATCHes changed only title
and body. Backups and issue-closing references survived. No blocking
behavioral defect was found. A stale numbered-rule reference was removed.

A live read-only inspection of an open robertson PR from outside a
checkout succeeded. No live PR, branch, or repository setting was changed
by validation. This verifies CLI/API reads, not live write or merge behavior.

The skill-creator validator passes for `kabpr` and the `kabocha`
compatibility entry point. Local Markdown links resolve except for the
intentionally lazy-fetched Elements book, whose pinned lineage is retained.

The broader cases in `evals.json` remain behavioral specifications;
this run does not claim the stack, seal, or squash suite passed.
