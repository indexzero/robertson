# Survival: does a byte-identical copy exist anywhere else?

Read this before every audit. It is the file half of every proof. The
question for each untracked, ignored, or copied file is the same: do these
exact bytes survive somewhere the operator is keeping? Filename alone proves
nothing. Same name is not same content.

## Twin hashing

A file survives when a file with the same repo-relative path in a kept
checkout has the same SHA-256. `scripts/audit-worktree.sh` does this for a
worktree against `--primary`, the retained checkout. It reports each file
with a `survival` value:

```txt
identical    a byte-identical twin exists at the same path. Proven safe.
dir_present  an ignored directory with a same-named twin. Evidence, not proof.
none         this is the only copy. A blocker until someone decides otherwise.
```

An untracked directory is never `dir_present`. `drafts/03/` existing in two
checkouts says nothing about the 19,713-byte draft inside one of them.

`--primary` must never resolve to the target itself. For a standalone clone,
`git worktree list` returns the clone as its own first entry, every file
becomes its own twin, and the audit reports `unsaved_local_files: 0`. On one
real clone that hid a 45 MB `e2e/captures/out` with no copy anywhere. Pass a
canonical clone explicitly, and treat a primary equal to the target as an
error.

## Three ways bytes exist upstream

A copied file can also survive as git content in a canonical repo, with no
twin on disk. Check in this order, cheapest first, and stop at the first hit.

1. Raw blob. `git hash-object --no-filters --stdin-paths` fed absolute paths,
   then `git -C <canon> cat-file --batch-check`. A line ending in `missing`
   means not found.
2. Converted blob. The canonical repo may rewrite line endings or run a clean
   filter, so the stored blob differs from the raw bytes. Hash again with
   `GIT_DIR=<canon>/.git GIT_WORK_TREE=<copy> git hash-object --stdin-paths`
   run from inside the copy, so the canonical attributes apply. Hashing from
   the wrong repo made identical fonts and a `.pptx` look unique.
3. LFS object. For a path with `filter: lfs`, git stores only a pointer. Take
   the file's SHA-256 and look for
   `<canon>/.git/lfs/objects/<aa>/<bb>/<sha256>`. On one copy this moved 717
   of 718 "unique" images back to saved. This checks the local store only; an
   object fetched on demand but not present locally still reads as unique.

`git hash-object --stdin-paths` resolves relative paths against the root of
the enclosing repo, not the shell's directory. Feed absolute paths, or set
`GIT_WORK_TREE`. Ignoring this hashed the wrong files and reported a copy
fully saved when it was not.

Content under a submodule path lives in the submodule's own repo. Check
`vendor/opentui-web/*` against the opentui-web clone, not the parent.

## Rebuildable material

`scripts/regenerable.txt` lists directory names and suffixes that a lockfile
or build rebuilds: `node_modules`, `dist`, `target`, `.build`, `coverage`,
`test-results`, `playwright-report`, `.turbo`, `.vite`, `node-compile-cache`,
`*.tsbuildinfo`. Count them once. Never enumerate them, never let them block.

`.cache` is not on that list. Reviewers keep notes there. In one run,
`.cache/review-cp4/commands.md` was cited by a result document and sat under
a directory an older list called regenerable.

A cited directory is judged by what is inside it after the rebuildable
entries are removed. A checkout cited for where tests ran is not blocked by
its `node_modules`.

## Credentials

`audit-worktree.sh` flags names matching accesskey, secret, credential,
token, `.env`, `.pem`, `.p12`, `id_rsa`, `.netrc` as `credential_candidates`.
A credential is always a blocker. Report the filename and its hash. Never
read it out, never grep for its value elsewhere, never paste it into chat.
Back it up or deliberately revoke it before anything containing it goes.

For every file that fails to survive, name the path and the byte count:
`RESEARCH.NOTES.md (6,699 bytes), no copy elsewhere`.
