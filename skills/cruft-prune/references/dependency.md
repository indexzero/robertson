# Dependency trees and build output

A dependency tree or build directory is rebuildable when a lockfile or build
script sits beside it. `node_modules/` next to `pnpm-lock.yaml`, `target/`
next to `Cargo.lock`, `.build/` next to `Package.resolved`, `dist/` next to
the source that produced it. That is the whole proof. Count the entries once,
report the total, and never enumerate them.

## The list

`scripts/regenerable.txt` is the one list every script reads. Directory
names: `node_modules`, `dist`, `dist-canvas`, `build`, `target`, `.build`,
`coverage`, `test-results`, `playwright-report`, `.playwright`, `.turbo`,
`.vite`, `.wrangler`, `.next`, `pnpm-store`, `.pnpm-store`,
`node-compile-cache`. Suffixes: `.tsbuildinfo`, `.last-run.json`.

Two things are deliberately absent. `.cache` holds reviewer notes and must
be judged. A `tmp/` or `temp/` directory is where tests put fixtures and
where agents put work; judge it.

## pnpm stores

A pnpm content-addressable store under `store*/` or `.pnpm-store/` holds
extracted package contents, each with a `package.json` and often a lockfile.
`tree-copies.py` must not take these for source copies. Their bytes come from
the registry and no repo blob check can place them. They are rebuildable by
`pnpm install`, and they go under this rule.

## Size

Dependency trees are most of the disk: in one scratch tree, 2108
`node_modules` directories held 78 of 180 GiB. `survey` reports this bucket
first.

## In an audit

A rebuildable entry is never a blocker and never a witness. `audit-worktree.sh`
reports the count as `filesystem.ignored_regenerable_entries`. A tree copy's
proof skips these directories entirely; the copy's `node_modules` is its own
candidate under this rule, and deleting the copy deletes both.

Hardlinked stores are safe to remove: a pnpm `node_modules` links into the
global store, and removing the link leaves the store intact.
