# The audit document and the paste block

The audit is one file at the repo root: `SAFE.TO.DELETE.STUFF.<YYYY-MM-DD>.md`,
dated for today. Audits accumulate instead of overwriting: old file findings
stay true, old merge verdicts expire within days. If today's file exists,
suffix `.2`, `.3`.

## Frontmatter

Header metadata is YAML, never bold-label lines.

```yaml
---
audited_at: 2026-11-07
base_ref: origin/main
base_sha: 9a14a08a
populations: [worktree, clone, tree-copy]
candidates: 1042
safe: 1019
keep: 23
excluded: ["primary checkout", "current worktree ../wt-a", "sslop/D-036/rehearsals"]
method: "scripts/git-orphans.py plan; content re-derived, file findings cross-checked"
---
```

## The paste block

It comes first, and it must survive being pasted whole with no edits. One
line per SAFE target, then the `git fetch --prune <remote>` lines for every
remote the repo has. Nothing else inside the block.

Every line re-checks before it removes. Worktrees use `wt remove <branch>
--force` guarded by the same fingerprint check the scripts use. Clones and
copies use the script's own execute step, which reads the plan file, recomputes
each fingerprint, skips any target that changed, prints the count and the
size, and waits for the operator to type `delete <N>` before the first
`rm -rf`.

```bash
python3 -I scripts/git-orphans.py execute plan.tsv
python3 -I scripts/tree-copies.py execute copies-plan.tsv
git fetch --prune origin
```

The fingerprint for a repo covers HEAD, every ref, the stash count, and the
full `git status` including ignored entries. For a copy it covers the sorted
list of every file's path, size, and mtime outside the rebuildable dirs. A
block run a week later refuses whatever changed. It does not see new files
inside an ignored directory, since status collapses those to one line; say so
in the caveats.

## Plan files

Scripts write a tab-separated plan the execute step reads back. Columns:

```txt
git-orphans.py   action  target  bytes  repos  classes  fingerprint  reason
tree-copies.py   action  target  bytes  files  unique   fingerprint  reason
```

`action` is DELETE or KEEP. `reason` on a KEEP row names the witness. A
`<plan>.meta.json` sidecar records the scan root, canonical clones, keeps,
and witness file so `execute` and `rescue` reuse them. `tree-copies.py` also
writes `<plan>-unique.tsv`, one row per unique file: target, path, bytes.
Read it before `rescue`.

## The tables

After the block, in this order:

1. Why these are safe. One row per SAFE target, with a content proof column
   and a file proof column. A good content row: "five commits show as
   branch-only under `git cherry` because PR #212 was squashed; it is MERGED
   as `3f9c2a1d`, reachable from `origin/main`." A good file row: "only
   regenerable trees (15 entries) and two hash-identical propagated
   `NOTES.*.md` copies."
2. Definitively not safe. One row per KEEP target: where the unique content
   is and what would be lost, with file names and byte sizes. This table is
   why the document exists.
3. Caveats. Which entries need `--force` and what dirt that discards. That a
   target clean today can hold new files tomorrow, so a long-deferred target
   should be re-audited. That remote branches auto-deleted on merge need no
   action.

Name every exclusion so a reader knows it was considered, not missed.

## Handing over

Report the file's path and the headline counts. Show the SAFE list inline.
Say plainly that nothing has been removed and the block is the operator's to
run. If a KEEP holds something that should be rescued today, a credential, a
manuscript, a design note, say so first instead of leaving it in a table row.
