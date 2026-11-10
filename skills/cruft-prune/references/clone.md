# Stray clones

A stray clone is a repo no worktree list knows about: a `.git` directory or
file under a scratch tree, a bare `remote.git` a test created, a copy of a
checkout a reviewer made with `git init` to diff against. Deleting one
removes a directory, never a branch in another repo. So the proof it owes is
weaker than a worktree's: every commit exists somewhere else, and is
reachable there.

## Finding them

`scripts/git-orphans.py plan <dir> --canon <dir>... [--keep <path>]...
[--witness <file>] [--snapshot-max N]` walks `<dir>` without following
symlinks and without entering `node_modules`. A repo is a directory holding
`.git`, or a `*.git` directory with `HEAD`, `objects/`, and `refs/`. It keeps
descending through a working tree, so a vendored clone inside a copy is found
too.

Each repo maps to one target. Normally that is its own directory, with nested
repos folded into the outermost. A repo under a `mkdtemp` directory such as
`wt-new-PXEAJW/`, `text-lint-04OnMx/`, or `linux-goldens-0CvcN5/` makes the
whole temp directory the target, so the fake `remote.git` beside the clone
goes with it. Paths in `--keep` are never targets, and nothing equal to,
inside, or containing one is either.

## Three classes, one policy

Every repo inside a target must be one of these for the target to be DELETE.

Pushed. It has a remote outside the scanned tree, no stash, no modified
tracked files, and `git rev-list --branches --tags HEAD --not --remotes` is
empty. Parse `git remote -v` by fields: a partial clone prints
`origin <url> (fetch) [blob:none]`, and a check for a line ending in
`(fetch)` reads it as having no remote at all. One such clone was classed as
a local snapshot before the fix.

Upstream. It has no real remote, but every commit from
`git rev-list --all --reflog` is in a canonical clone named by `--canon`.
Present as an object is not enough. `cat-file --batch-check` succeeds for an
unreachable object that the next garbage collection removes, so the check
must confirm the commit is reachable from a ref there, with
`git merge-base --is-ancestor <sha> <ref>` or `git branch --contains`.

Snapshot. It has no real remote and fewer than `--snapshot-max` commits,
default 50. These are reviewer copies and test fixtures with commits called
`base`, `probe`, `fixture`, by authors called `x`, `r`, `Fixture Original
Author`. This class is a policy, not a proof. Nothing verifies that the
commits are worthless; the operator accepts that a local-only repo this small
inside a scratch tree is a snapshot. Say so in the audit. Real histories in
one scratch tree had 338 and 823 commits; a fixture had 20.

Anything else is `unsafe`, and the target is KEEP with the reason: stash
entries, modified tracked files, commits not on the remote, local-only
history not found upstream.

## Witnesses inside the directory

A clean repo can still hold the only copy of something. `git status` hides
ignored files, and reviewers put notes in ignored places: on one run,
`.cache/review-cp4/commands.md` and probe tests like `d105-probe.test.ts`
written into copies. The `--witness` file lists paths a tracked document
cites. A cited path inside a target blocks it unless the path is tracked and
unmodified in a pushed or upstream repo. For a cited directory, entries under
rebuildable names are ignored first; `.cache` is not rebuildable.

A linked worktree's `.git` file points at an admin directory elsewhere.
Deleting the directory that holds another kept worktree's admin data breaks
it, so such a target is KEEP.

## The record

The plan file has `action, target, bytes, repos, classes, fingerprint,
reason`. `classes` tallies the repos inside, as in `pushedx1,snapshotx1`.
`reason` on a DELETE row carries notes such as "no local canonical clone to
cross-check". The report prints every KEEP with its reason and every DELETE
that has a note.

Guards at execute: the target is a real directory with no symlink in its
path, strictly inside the scanned tree, not in `--keep`, and its fingerprint
still matches.
