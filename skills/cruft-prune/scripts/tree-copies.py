#!/usr/bin/env python3
"""Find source-tree copies that have no .git and decide which are safe to delete,
once every file in them is proven to exist somewhere canonical.

  tree-copies.py plan <dir> --canon <clone>... [--keep <path>]... [--witness <file>]
  tree-copies.py rescue <copies-plan.tsv>    copy each KEEP row's unique files to rescued/ beside the plan
  tree-copies.py execute <copies-plan.tsv>   re-verify fingerprints, ask, then rm -rf

plan is read-only. It writes copies-plan.tsv, copies-plan-unique.tsv, and a
.meta.json beside them. The skill never runs rescue or execute; the operator does.

A copy is a dir holding package.json plus pnpm-lock.yaml or pnpm-workspace.yaml,
or Cargo.toml plus Cargo.lock, with no .git in itself or any ancestor below
<dir>. Outermost only. pnpm store dirs (store*, .pnpm-store, pnpm-store, v10)
hold package contents, not a source tree, and are never copies. A copy is
DELETE when every regular file outside the regenerable dirs is saved, meaning
one of:

  1. its bytes, converted by the first --canon repo's attributes, are a blob
     in a --canon repo
  2. its raw bytes are a blob in a --canon repo
  3. its sha256 is an object in a --canon repo's LFS store
  4. a byte-identical twin sits in rescued/<target>/ beside the plan (left by rescue)

A witness (cited) file counts as saved only via 2, 3, or 4. Anything else is
KEEP, with the unique files listed in <plan>-unique.tsv. --keep paths are
never targets.
"""
import filecmp
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("prunelib", f"{HERE}/prunelib.py")
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

REGEN_DIRS, REGEN_GLOBS = L.load_regenerable()
MARKERS = [("package.json", "pnpm-lock.yaml"), ("package.json", "pnpm-workspace.yaml"),
           ("Cargo.toml", "Cargo.lock")]
PNPM_STORE = re.compile(r"^(store\d*|\.?pnpm-store|v\d+)$")


def is_copy(names):
    return any(a in names and b in names for a, b in MARKERS)


def find_copies(root):
    """Outermost .git-less source-tree copies under root. Never follows symlinks."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        names = set(dirnames) | set(filenames)
        if dirpath != root and (".git" in names or L.is_bare(dirpath)):
            dirnames[:] = []
            continue
        if dirpath != root and os.path.basename(dirpath) != "rescued" and is_copy(names):
            out.append(dirpath)
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", "rescued")
                       and not PNPM_STORE.match(d)]
    return out


def files_of(copy):
    """(relpath, size, mtime_ns) for every regular file outside the regenerable dirs."""
    out = []
    for dirpath, dirnames, filenames in os.walk(copy):
        dirnames[:] = [d for d in dirnames if d not in REGEN_DIRS]
        for n in filenames:
            if L.is_regenerable_file(n, REGEN_GLOBS):
                continue
            p = f"{dirpath}/{n}"
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            out.append((os.path.relpath(p, copy), st.st_size, st.st_mtime_ns))
    return sorted(out)


def fingerprint(files):
    return L.digest(files)


def hash_paths(paths, cwd, env, no_filters):
    """git hash-object --stdin-paths. Returns a list parallel to paths, or None on failure."""
    if not paths:
        return []
    args = ["git", "hash-object", "--stdin-paths"] + (["--no-filters"] if no_filters else [])
    r = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, errors="surrogateescape",
                       input="".join(p + "\n" for p in paths))
    out = r.stdout.split()
    return out if r.returncode == 0 and len(out) == len(paths) else None


def present(store, shas):
    """Set of shas the store has as objects."""
    shas = sorted(set(shas))
    if not shas:
        return set()
    out = L.git(store, "cat-file", "--batch-check", stdin="\n".join(shas) + "\n") or ""
    return {l.split()[0] for l in out.splitlines() if not l.endswith(" missing")}


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def prove(copy, files, stores, cited, rescue_dir):
    """Return the list of unique (rel, size) among files. Order of checks: raw, converted, LFS, rescue."""
    rels = [f[0] for f in files]
    size = dict((f[0], f[1]) for f in files)
    saved = set()

    # 2. raw bytes. Absolute paths: stdin paths are otherwise resolved against the enclosing repo root.
    raw = hash_paths([f"{copy}/{r}" for r in rels], HERE, L.ENV, no_filters=True)
    if raw is not None:
        have = set()
        for s in stores:
            have |= present(s, raw)
        saved |= {r for r, h in zip(rels, raw) if h in have}

    # 1. converted by the first canonical repo's attributes. Not enough on its own for a cited file.
    todo = [r for r in rels if r not in saved]
    gd = L.gitdir(stores[0])
    if todo and gd:
        env = {**L.ENV, "GIT_DIR": gd, "GIT_WORK_TREE": copy}
        conv = hash_paths(todo, copy, env, no_filters=False)
        if conv is not None:
            have = set()
            for s in stores:
                have |= present(s, conv)
            saved |= {r for r, h in zip(todo, conv) if h in have and f"{copy}/{r}" not in cited}

    # 3. LFS object by sha256, in any store's LFS dir.
    lfs_dirs = [f"{g}/lfs/objects" for g in map(L.gitdir, stores) if g and os.path.isdir(f"{g}/lfs/objects")]
    unique = []
    for r in rels:
        if r in saved:
            continue
        if lfs_dirs:
            d = sha256_of(f"{copy}/{r}")
            if any(os.path.isfile(f"{l}/{d[:2]}/{d[2:4]}/{d}") for l in lfs_dirs):
                continue
        # 4. a byte-identical twin left by rescue
        twin = f"{rescue_dir}/{r}"
        if os.path.isfile(twin) and filecmp.cmp(f"{copy}/{r}", twin, shallow=False):
            continue
        unique.append((r, size[r]))
    return unique


def plan(a):
    root, stores, keeps = a.dir, a.canon, a.keep
    cited = L.load_witness(a.witness)
    out = a.out or f"{HERE}/copies-plan.tsv"
    rescued = os.path.join(os.path.dirname(os.path.abspath(out)), "rescued")
    uniq_out = re.sub(r"\.tsv$", "", out) + "-unique.tsv" if out.endswith(".tsv") else out + "-unique.tsv"
    copies = sorted(find_copies(root))
    print(f"copies: {len(copies)}", file=sys.stderr)

    rows, uniq_rows = {}, []
    for i, c in enumerate(copies, 1):
        files = files_of(c)
        reason = L.guard(c, root, keeps)
        unique = []
        if reason is None and not stores:
            reason = "no canonical clone given (--canon)"
        if reason is None:
            unique = prove(c, files, stores, cited, f"{rescued}/{os.path.relpath(c, root)}")
            if unique:
                reason = (f"{len(unique)} unique files, {L.gib(sum(s for _, s in unique))}, "
                          f"e.g. {', '.join(r for r, _ in unique[:3])}")
        rows[c] = {"action": "KEEP" if reason else "DELETE", "reason": reason or "",
                   "files": len(files), "unique": len(unique), "fp": fingerprint(files)}
        uniq_rows += [(c, r, s) for r, s in unique]
        print(f"  {i}/{len(copies)} {os.path.relpath(c, root)}: {rows[c]['action']} "
              f"({len(files)} files, {len(unique)} unique)", file=sys.stderr)

    print("measuring sizes...", file=sys.stderr)
    for c in copies:
        rows[c]["bytes"] = L.du(c)

    with open(out, "w", errors="surrogateescape") as f:
        f.write("action\ttarget\tbytes\tfiles\tunique\tfingerprint\treason\n")
        for c in copies:
            r = rows[c]
            f.write(f"{r['action']}\t{os.path.relpath(c, root)}\t{r['bytes']}\t{r['files']}\t"
                    f"{r['unique']}\t{r['fp']}\t{r['reason']}\n")
    with open(uniq_out, "w", errors="surrogateescape") as f:
        f.write("target\tfile\tbytes\n")
        for c, r, s in uniq_rows:
            f.write(f"{os.path.relpath(c, root)}\t{r}\t{s}\n")
    with open(f"{out}.meta.json", "w") as f:
        json.dump({"root": root, "canon": stores, "keep": keeps, "witness": a.witness, "unique": uniq_out, "rescued": rescued}, f, indent=1)

    for action in ("DELETE", "KEEP"):
        cs = [c for c in copies if rows[c]["action"] == action]
        print(f"\n{action}: {len(cs)} copies, {L.gib(sum(rows[c]['bytes'] for c in cs))}, "
              f"{sum(rows[c]['files'] for c in cs)} files checked")
    print("\nKEEP, with reasons:")
    for c in copies:
        if rows[c]["action"] == "KEEP":
            print(f"  {os.path.relpath(c, root)}\n      {rows[c]['reason']}")
    print(f"\nWrote {out} and {uniq_out}. Then the operator runs:\n"
          f"  python3 -I {__file__} rescue {out}   (optional: save unique files beside each copy)\n"
          f"  python3 -I {__file__} execute {out}")


def rescue(plan_path):
    meta = json.load(open(f"{plan_path}.meta.json"))
    root = meta["root"]
    keeps = {t for a, t, *_ in L.read_plan(plan_path) if a == "KEEP"}
    uniq = L.read_plan(meta["unique"])
    copied = skipped = 0
    for t, rel, _ in uniq:
        if t not in keeps:
            continue
        src, dst = f"{root}/{t}/{rel}", f"{meta['rescued']}/{t}/{rel}"
        if os.path.lexists(dst):
            skipped += 1
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
    print(f"rescued {copied} files, {skipped} already present. Re-run plan: copies whose unique "
          f"files all have a twin under rescued/ become DELETE.")


def execute(plan_path):
    meta = json.load(open(f"{plan_path}.meta.json"))
    root, keeps = meta["root"], meta["keep"]
    todo = [(f"{root}/{t}", int(b), fp) for a, t, b, _, _, fp, _ in L.read_plan(plan_path) if a == "DELETE"]
    print(f"re-verifying {len(todo)} DELETE rows...", file=sys.stderr)
    ready, skipped = [], []
    for t, b, fp in todo:
        reason = L.guard(t, root, keeps) if os.path.lexists(t) else "gone already"
        if reason is None and fingerprint(files_of(t)) != fp:
            reason = "changed since plan"
        (skipped if reason else ready).append((t, b, reason))
    L.confirm_and_delete(ready, skipped, root, "copies")


if __name__ == "__main__":
    a = L.parser("tree-copies.py", __doc__, rescue=True).parse_args()
    if a.cmd == "plan":
        plan(L.resolve_args(a))
    elif a.cmd == "rescue":
        rescue(os.path.abspath(a.plan))
    else:
        execute(os.path.abspath(a.plan))
