---
status: "in progress, paused 2026-10-19"
branch: "skill/kabocha (wt worktree robertson-worktrees/skill-kabocha, base origin/main e40afd6)"
research: "kept privately, outside this repository: layout prior art, tooling seams, scale evidence, and 20 seed evals"
---

# kabocha TODO

## Done

- `commands/ready.md` (default), `commands/seal.md` (from ste-seal),
  `commands/squash.md` (from ste-squash).
- `evals/evals.json`: 28 evals, 7 near misses.
- `skills/ste-seal` and `skills/ste-squash` removed. `lpmq.kdl` holds
  kabocha at stage 2. The issue templates list kabocha.
- `SKILL.md`: router, tiers, invariants, reconcile step, must-not-happen list.
- `references/message-style.md`, `github.md`, `ledger.md`, `drafters.md`.
- `.vlurpfile` pins *The Elements of Documentation* at of-structure
  `d158c8c`. The fetched copy and its `.vlurp.jsonl` are in
  `references/of-structure/`. `vlurp verify` passes. The installed vlurp
  2.0.0 fails on single-file PURLs. vlurp 2.0.1 from source works.

## Next

1. Run iteration 1 (skill-creator): with-skill and without-skill arms on
   synthetic fixtures (gh-compatible PR JSON, commits, settings, a scratch
   `KABOCHA_LEDGER`). Build the fixtures named in `evals/evals.json`.
   Record results in `evals/RESULTS.md` with YAML frontmatter, as wt-prune
   does.
2. Optimize the description for triggering with the near misses
   (skill-creator `run_loop`).
3. Back-fill the ledger with the first real runs (the autocache stack and
   PR #11) once the event schema settles.
4. Test whether an explicit `--body-file` squash still gets the branch
   commits' `Co-authored-by` trailers appended (commands/squash.md).

## Decisions (owner, 2026-10-19)

- Name: kabocha. Scope: the last mile only.
- Invocation: "kabocha the PRs related to <topic> on <repo>". kabocha
  detects the tier.
- It never merges. It reports ready with the commands. The ledger records
  ready verdicts and the operator's merges, as evidence for a future
  version that merges.
- Merges are inferred from GitHub's description edit times and merge
  records, cross-referenced with kabocha's own `applied` events. The
  editor login is the shared account, so it cannot tell kabocha's edits
  from the operator's.
- `seal` and `squash` run only when the operator names them. When the
  prediction shows a defect that only `seal` corrects, kabocha reports it
  and names `seal`.
- Tier 50: one batch for each scope, one stack for each scope.
- Mixed scope: log it, never recommend a split.
- Drafter: a swappable seam. `claude` today, `wt step squash --dry-run`
  later.
- The skill cites Elements by rule number through the vlurped copy. It
  never pastes the text.

## Evidence from the autocache stack (#13, #12, #14 to #18, merged 2026-10-19T20:23Z)

- All seven subjects and descriptions landed as approved.
- GitHub appended `---------` and `Co-authored-by: Claude Fable 5.1` from
  the branch commits, one line for each email address. That moved
  `Assisted-by` out of the last paragraph, and git stopped parsing it in
  all seven commits.
- Three code lines over 72 columns (in #13, #14, and #16) were rewrapped
  and lost their indentation.
- A later single-PR merge (#11, 2026-10-19T20:56Z) confirmed the append and
  showed the name rule: two commits shared one email address with
  different names, and GitHub kept the name from the oldest commit.
- First reconcile result: 7 `merged-platform-changed`. These are the
  first ledger entries to back-fill once `ledger.md` is final.

## Open questions

- lpmq stage: placed at stage 2 ("Tried") until iteration 1 passes. Stage 3 is the owner's call.
- Should `examples` or an `agents/openai.yaml` (as sandwalk has) ship for
  Codex?
- Should the reconcile `open-stale` window stay at 14 days?
