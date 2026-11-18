# Worktrees

A worktree is removed together with its branch, so the proof it owes is that
the branch's content already lives in the default branch. Pushed is not
enough here. An imperative tool handles the easy case: `wt list` marks a
branch that is an ancestor of the default branch with `⊂`, and
`git branch --merged origin/main` finds the same set. This file is for the
cases that tool cannot decide.

## One worktree

A question about a single worktree needs no script. Run the three proofs
below by hand, check the files with `git status --porcelain --ignored`, and
answer in prose. The script pays for itself across a population.

## Never-touch list

Exclude before anything else: the primary checkout, the worktree the shell
is in, and anything the user named. Say so in the audit.

## Collect evidence

```bash
for p in $(wt list --format json | jq -r '.[] | select(.is_main|not) | select(.is_current|not) | .path'); do
  scripts/audit-worktree.sh "$p" --primary <primary checkout>
done | jq -s . > wt-audit.json
```

Without `wt`, feed `git worktree list --porcelain | awk '/^worktree /{print $2}'`
and drop the primary and current paths by hand. Always pass `--primary`; see
`survival.md` for why the default is unsafe on a standalone clone.

The script emits one JSON object per worktree and decides nothing. Read
`signals` first to sort the population, then the detail on anything not
settled.

## Three content proofs

`signals.content_proven` is true when one of these held:

1. Ancestor. `content.ancestor` is true: HEAD is reachable from the base.
2. Patch-equivalent. `content.cherry.branch_only` is 0 and
   `content.cherry.equivalent_upstream` is above 0. Every commit has an
   equivalent upstream under `git cherry`.
3. Squash-merged. `content.pr.state` is MERGED and `content.pr.merge_reachable`
   is true. The branch's commits are not ancestors, `branch_only` is above 0,
   and the branch is still safe because squashing rewrote them. This is the
   case the imperative tool structurally cannot see, and it is common.

Two things override a true `content_proven`:

- `signals.open_pr`. Live review work outranks any equivalence proof.
- `signals.unmerged_local_edits`. Files in `content.uncommitted_tracked.modified`
  or `.added` are in no commit, so no commit proof covers them. Read the
  diff. `.deleted` is listed separately and is usually noise: a file the base
  still has is not lost when this directory goes.

When all three fail but a rebase or cherry-pick is suspected, fall back to
`git diff <branch> origin/main -- <path>` per touched file, and say in the
audit that this is what the verdict rests on.

## The filesystem half

`signals.unsaved_local_files` counts files with no surviving copy. Zero means
nothing irreplaceable. Above zero, read the detail:

- `filesystem.untracked[]`, each with `survival` and `bytes`.
- `filesystem.ignored_unique[]`: ignored files with no twin. Research output,
  captures, generated snapshot sets.
- `filesystem.ignored_propagated_identical[]`: hash-matched copies a worktree
  hook planted. Mention once, move on.
- `filesystem.ignored_regenerable_entries`: a count. Never a blocker.
- `filesystem.credential_candidates[]`: always a blocker, by name only.
- `signals.suspicious_bootstrap_dirs[]`: an ignored directory whose twin has
  the same name but a size ratio outside 0.9 to 1.1. Look before calling it
  bootstrap material.

## Classify

SAFE needs a named content proof and nothing that fails to survive. KEEP
needs a concrete witness: branch-only content absent from the base, or local
bytes with no surviving copy, named with a size. "It's dirty" is not a
witness. Uncertainty resolves to KEEP.

A previous audit's content verdicts are stale evidence: one worktree recorded
as blocked on open PR #212 had merged the next day. Reuse its file findings
as a cross-check and re-derive every merge verdict.
