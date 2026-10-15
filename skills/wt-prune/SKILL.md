---
name: wt-prune
description: Audit every git worktree for whether it is safe to delete, proving content equivalence with the default branch and inventorying leftover untracked/ignored files that exist nowhere else. Writes a dated SAFE.TO.DELETE.STUFF.<date>.md whose runnable block the operator executes themselves. Read-only — this skill never removes a worktree, a branch, or a ref. Invoked explicitly as /wt-prune.
argument-hint: "[branch-or-path ...]"
disable-model-invocation: true
allowed-tools: Bash(wt list *) Bash(git worktree list *) Bash(git status *) Bash(git cherry *) Bash(git log *) Bash(git diff *) Bash(git merge-base *) Bash(git ls-remote *) Bash(git branch *) Bash(gh pr view *) Bash(gh pr list *) Bash(ls *) Bash(cmp *) Bash(shasum *)
---

# /wt-prune — prove which worktrees are safe to delete, and write it down

**This skill deletes nothing.** It produces one document. The runnable block in
that document is the product, and the operator runs it — after reading the
reasons, which is the entire point. Never run `wt remove`, `git worktree
remove`, `git branch -d/-D`, or `git fetch --prune` from this skill, even when
the evidence is overwhelming and even if asked mid-run. If the user wants a
removal performed, that is a separate decision made outside this skill.

An imperative prune script (here `wtprune`, a wrapper that removes branches
`wt list` marks `⊂`, meaning ancestors of the default branch) already handles
the easy case. Without `wt`, `git branch --merged origin/main` finds the same
set. Clean, integrated, nothing to lose.

This skill is the other case, the one an imperative script cannot decide:

- **Squash-merged branches.** The content is in main; the commit is not an
  ancestor. `⊂` never fires, so `wtprune` skips them forever.
- **Leftover slop.** Review notes, research archives, plan docs, credentials,
  captures — untracked or ignored bytes that exist in exactly one place on
  disk. `git status` says "dirty"; only reading the files says "irreplaceable".

A worktree is safe only when both are settled. Dirty is not evidence of value,
and clean is not evidence of safety.

## Arguments

Any arguments are branch names or worktree paths: audit only those. Given none,
audit every worktree except the never-touch list.

## Live state (injected before you start)

!`wt list 2>/dev/null || git worktree list`

Default branch and its tip:

!`git fetch origin --quiet 2>/dev/null; git log -1 --format='%h %s' origin/HEAD 2>/dev/null || git log -1 --format='%h %s' origin/main`

## Step 0: Never-touch list

Exclude before you audit anything:

1. The primary checkout (`is_main`).
2. The worktree the shell is currently in (`is_current`).
3. Any worktree the user named as off-limits.

## Step 1: Collect evidence

Run `scripts/audit-worktree.sh <worktree-path>` for each worktree. It emits one
JSON object per worktree and takes about a second. Doing this by hand is a
dozen git invocations per worktree; on a repo with 80 worktrees that is the
difference between a minute and an afternoon.

```bash
for p in $(wt list --format json | jq -r '.[] | select(.is_main|not) | select(.is_current|not) | .path'); do
  .claude/skills/wt-prune/scripts/audit-worktree.sh "$p"
done | jq -s . > /tmp/wt-audit.json
```

Without `wt`, feed `git worktree list --porcelain | awk '/^worktree /{print $2}'`
instead and drop the primary and current paths by hand.

The script decides nothing. It answers the mechanical questions; you make the
call. Read `signals` first to sort the population, then read the detail on
anything that is not obviously settled.

## Step 2: Judge the content

`signals.content_proven` is true when any of three proofs held:

1. **Ancestor** — the branch is reachable from the base. This is `wtprune`'s
   `⊂`.
2. **Patch-equivalent** — `cherry.branch_only == 0` with equivalents upstream.
3. **Squash-merged** — a MERGED PR whose `merge_commit` is reachable from the
   base. This is the case `wtprune` structurally cannot see, and it is common:
   `cherry.branch_only` will be non-zero *and the branch is still safe*,
   because squashing rewrites the commits.

Two things override a true `content_proven`:

- `signals.open_pr` — live review work outranks any equivalence proof.
- `signals.unmerged_local_edits` — modified or added tracked files are in no
  commit, so no commit proof covers them. Read the diff. Deletions are listed
  separately and are usually noise: a file the base still has is not lost when
  the directory goes.

When all three proofs fail but you suspect a rebase or cherry-pick, fall back
to `git diff <branch> origin/main -- <path>` per touched file, and say in the
audit that this is what you relied on.

## Step 3: Judge the filesystem

`signals.unsaved_local_files` counts files with no surviving copy. Zero means
the directory holds nothing irreplaceable. Non-zero means read the detail:

- `untracked[]` — each carries `survival`. `identical` means a byte-identical
  twin exists in the primary checkout. `none` means this is the only copy, and
  it blocks removal until someone decides otherwise.
- `ignored_unique[]` — ignored files with no twin. Research output, captures,
  fonts, generated snapshot sets.
- `ignored_propagated_identical[]` — hash-matched copies a worktree hook
  planted (for example, a repo that copies a `NOTES.*.md` into every new
  worktree). Not a blocker; mention once and move on.
- `ignored_regenerable_entries` — a count of dependency and build trees. Never
  a blocker, never worth enumerating.
- `credential_candidates[]` — always a blocker. Back it up or deliberately
  revoke it first. Report the filename only; the script hashes these files and
  never reads them out, and neither should you.
- `signals.suspicious_bootstrap_dirs[]` — an *ignored* directory whose name
  matches one in the primary checkout but whose size does not. Same name is not
  same content: a `.tmp/` holding a draft set is not the `.tmp/` next door.
  Untracked directories are never treated as surviving, whatever their name.

## Step 4: Classify

- **SAFE** — a named content proof, and nothing that fails to survive.
- **BLOCKED** — a concrete preservation witness: branch-only content absent
  from the base, or local bytes with no surviving copy. Name the file, the
  identifier, or the prose. "It's dirty" is not a witness.

Uncertainty resolves to BLOCKED. The cost of keeping a worktree is disk; the
cost of deleting one is unrecoverable.

**A previous audit is not evidence of merge status.** An older
`SAFE.TO.DELETE.STUFF.*.md` is durable for what it says about *files* — bytes
do not merge themselves — but its content verdicts rot within days as PRs land.
In one real case a worktree the prior audit called blocked-on-open-PR had
merged the very next day. Re-derive every content verdict; reuse the filesystem
findings as a cross-check on what the script found, not as a substitute for
looking.

## Step 5: Write the audit

Write `SAFE.TO.DELETE.STUFF.<YYYY-MM-DD>.md` at the repo root, dated for today.
The date is in the name so audits accumulate instead of overwriting each other
— an audit is a record of what was true on a day, and the old ones stay useful
for the filesystem findings long after their merge verdicts expire. If a file
for today already exists, suffix it (`.2`, `.3`) rather than clobbering.

Header metadata belongs in YAML frontmatter, not in bold-label lines:

```markdown
---
audited_at: 2026-08-16
base_ref: origin/main
base_sha: 9a14a08a
worktrees_audited: 79
safe: 6
blocked: 30
method: "audit-worktree.sh evidence; content re-derived, filesystem cross-checked"
---

# Worktree deletion audit
```

Then, in order:

1. **The runnable block.** This is what the operator executes, so it has to
   stand alone: one `wt remove <branch> --force` per SAFE worktree, then the
   `git fetch --prune <remote>` lines for every remote the repo has (check
   `git remote`; a repo with more than one remote drifts between them).
   Nothing else in the block —
   it should survive being pasted whole, without edits.
2. **"Why these worktrees are safe"** — one row per SAFE worktree, with a
   **Content proof** column and a **Filesystem proof** column.
3. **"Definitively not safe to delete"** — one row per BLOCKED worktree: where
   the unique content lives, and what exactly would be lost, with file names
   and byte sizes. This table is the reason the document exists; someone reads
   it months later to decide whether a directory still matters.
4. **A short caveats section**, because the operator runs the block later and
   the audit ages: which entries needed `--force` and what dirt that discards;
   that a worktree clean at audit time can hold new files an hour later, so
   re-running `audit-worktree.sh` on anything long-deferred is cheap insurance;
   and that any remote branch already auto-deleted on merge needs no action.

Name the never-touch exclusions explicitly, so a reader knows they were
considered rather than missed.

### What a good row looks like

**Content proof, squash-merged:**
> Its five commits show as branch-only under `git cherry` because PR #212 was
> squashed; that PR is MERGED as `3f9c2a1d`, which is reachable from
> `origin/main`, and `src/shell/empty-state.ts` is present there.

**Filesystem proof, clean:**
> Only regenerable trees (15 entries) and two hash-identical propagated
> `NOTES.*.md` copies. `vendor/` and `data/*/raw/` match the primary checkout
> in size and are re-fetchable bootstrap material.

**A blocking row:**
> `feat/density-model` — the branch tip is on `origin/main`, but
> `RESEARCH.NOTES.md` (6,699 bytes) is the only write-up of an unfinished
> analysis. No copy elsewhere.

Notice what each one does: it names the artifact and the number. "Has untracked
files" tells a future reader nothing and forces the whole audit to be redone.

## Step 6: Hand it over

Report where the document is and the headline counts. Show the SAFE branches
inline so the decision is visible without opening the file, and say plainly
that nothing has been removed and the block is theirs to run.

If a blocked worktree holds something that ought to be rescued — a manuscript,
a credential, a design note — say so here rather than burying it in a table
row. That is the finding most likely to be acted on today.

## The failure this skill exists to prevent

Someone runs `wt remove -f` across a list of branch names that look merged, and
a 74 MB research archive, a manuscript, and a live credential go with them. The
branches really were merged. That was never the question.
