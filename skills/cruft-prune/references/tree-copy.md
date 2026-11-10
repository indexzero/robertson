# Tree copies

A tree copy looks like a checkout and has no `.git`: a `cp -r` of a source
tree that a reviewer ran tests in, a `head-copy`, a `base-copy`, a
`mutation-1`. It usually has a `node_modules` inside because the tests needed
one. Git cannot speak for it, so the proof it owes is file by file: every
file's bytes already exist upstream. What fails that test is a file to
rescue, not a reason to keep the copy.

## Spotting one

`scripts/tree-copies.py plan <dir> --canon <dir>... [--keep <path>]...
[--witness <file>]` treats as a copy any directory holding `package.json`
plus `pnpm-lock.yaml` or `pnpm-workspace.yaml`, or `Cargo.toml` plus
`Cargo.lock`, with no `.git` in itself or any ancestor below the scanned
root, and not inside a repo. Outermost only. A directory named
`rescued` is skipped; it is rescue output.

A pnpm content-addressable store looks like a copy and is not. Its
`v10/tmp/_tmp_*` directories hold extracted package contents with a
`package.json` and a lockfile. Their bytes come from the npm registry, not
from any repo, so no blob check can place them. Hand paths under `store*/`
or `.pnpm-store/` to the dependency rule instead.

## The proof

For every regular file outside the rebuildable dirs in
`scripts/regenerable.txt`, the file is saved when any of these holds. The
script checks them in this order because each is dearer than the last.

1. Raw blob. `git hash-object --no-filters --stdin-paths` over absolute
   paths, then `cat-file --batch-check` in each canonical store.
2. Converted blob. The canonical repo's `.gitattributes` may normalize line
   endings or run a filter, so the stored blob differs from the raw bytes.
   Rehash the misses with `GIT_DIR=<canon>/.git GIT_WORK_TREE=<copy>` from
   inside the copy, which applies the canonical attributes to the copy's
   paths.
3. LFS object. For the remaining misses, SHA-256 the file and look for
   `<canon>/.git/lfs/objects/<aa>/<bb>/<sha>`. charlie.dev stores every
   image as a pointer; 717 of one copy's 718 misses were in the LFS store.
4. Rescue twin. A byte-identical file at `rescued/<target>/<relative path>`
   beside the plan, left by an earlier `rescue`.

Files under a submodule path are checked against the submodule's own repo as
well, named in `--canon`. `vendor/opentui-web/*` lives in the opentui-web
clone, not the parent.

`survival.md` has the two hashing mistakes this order exists to avoid.

A path listed in `--witness` counts as saved only through the raw blob, the
LFS object, or a rescue twin. Not through the converted blob.

## What the proof finds

On four copies in one review directory:

```txt
base-copy    2241 files   1 unique   render/washe/src/shell/kernel-review-probes.test.ts
head-copy    3074 files   2 unique   the same probe, vendor/opentui-web/CLAUDE.md
mutation-1    431 files   2 unique   render/washe/src/shell/paste.ts, apple-touch-icon.png
mutation-2    431 files   2 unique   render/washe/src/shell/wash/index.ts, apple-touch-icon.png
```

The unique files are the reviewer's work: the mutated source and the probe
test. Across 595 copies, 367 were held by three files or fewer, 3.2 MiB in
total, mostly an edited `package.json` or lockfile.

## Rescue

`tree-copies.py rescue copies-plan.tsv` copies every unique file of every
KEEP row to `rescued/<target>/<relative path>`, one directory beside the
plan file, never inside a copy, never overwriting. Re-run `plan`; a copy
whose unique files all have twins becomes DELETE. The `rescued` directory
is what remains when the copies are gone, and it packs as one unit.

## The record

The plan file has `action, target, bytes, files, unique, fingerprint,
reason`. `copies-unique.tsv` lists every unique file as `target, file,
bytes`; read it before rescue. The fingerprint is a SHA-256 over the sorted
`(path, size, mtime_ns)` of every file outside the rebuildable dirs, and
execute skips a copy whose fingerprint changed.
