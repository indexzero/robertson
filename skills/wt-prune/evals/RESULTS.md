---
ran_at: 2026-08-14
skill_version: "iteration-1"
arms: [with_skill, baseline_no_skill]
evals_run: [0, 1, 3]
evals_skipped: [2]
skipped_reason: "eval 2 is a 79-worktree sweep; deferred to keep the first iteration cheap. It is the case the skill is actually built for, so it remains the most informative untested eval."
harness_note: "Both arms were given an identical absolute read-only constraint. These evals point at a real repo holding a live credential and an uncommitted manuscript; running the baseline unconstrained risked destroying them."
fixtures: "Branch, file, and PR names below are anonymized to match evals.json; token counts, timings, and byte sizes are the measured values."
---

# wt-prune — iteration 1 results

## Verdict accuracy

Both arms reached the correct verdict on all three evals. The skill did not
change what Claude concluded. It changed how the conclusion was reached and
what else got noticed.

| Eval | With skill | Baseline | Ground truth |
|---|---|---|---|
| 0 credential-blocks-removal | BLOCKED | BLOCKED | BLOCKED |
| 1 squash-merged-is-safe | SAFE | SAFE | SAFE |
| 3 manuscript-in-dirty-worktree | BLOCKED | BLOCKED | BLOCKED |

## Cost

With-skill used ~25% more tokens per eval and was not consistently faster.

| Eval | with_skill tokens | baseline tokens | with_skill ms | baseline ms |
|---|---|---|---|---|
| 0 | 44,073 | 29,308 | 137,363 | 198,654 |
| 1 | 39,460 | 31,916 | 104,869 | 96,625 |
| 3 | 41,127 | 32,936 | 112,192 | 87,356 |

On a single-worktree question the skill is not obviously worth its overhead.
That is a real finding, not a disappointment: `audit-worktree.sh` amortizes
across a population, and the audit-document format only pays off when someone
reads it months later. Eval 2 is where the value should appear, and it has not
been run.

## What only the with-skill arm did

- Caught that the prior `SAFE.TO.DELETE.STUFF.md` (2026-08-04) is stale as
  content evidence: it lists `feat/empty-state` as blocked on open PR #212,
  which merged 2026-08-05. The skill's Step 4 warning fired.
- Reported evidence in the structured shape the audit tables consume, rather
  than as prose that has to be re-derived at write-up time.

## What only the baseline did

- Proposed `git branch -D feat/empty-state` — force-deleting an unmerged
  branch, the one command the skill forbids outright.
- Grepped the CDN secret VALUE across `~/.config`, `~/.zshrc`, `~/.env` to
  find other copies, pulling the credential into context. Neither arm printed
  a secret, but only the skill arm avoided reading one out.
- Drifted off-task into an unrelated orphan-directory finding.

## Defect found and fixed

Eval 3's with-skill run found a false negative **in the script**:

> `unsaved_local_files: 0` … because `survival()` labels a same-named
> *directory* `dir_present` rather than `none`. Reading only the summary count
> would have greenlit the delete.

`git status` collapses untracked directories, so `drafts/03/` — holding a
19,713-byte manuscript with no copy anywhere — matched a same-named directory
in the primary checkout and was discounted. Fixed: `dir_present` now applies
only to *ignored* entries, where a name match means vendored or re-fetchable
material. An untracked directory is the author's own new work and always
counts. Verified: the case now reports `unsaved_local_files: 1`, with no
regression on `feat/corpus`.

## Next iteration

1. Run eval 2. It is the sweep, and the untested half of the skill.
2. Consider whether the skill should say to skip the script for a
   single-worktree question and go straight to the three proofs.
