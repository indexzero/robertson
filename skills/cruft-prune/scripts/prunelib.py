"""Shared pieces for git-orphans.py and tree-copies.py.

Nothing here deletes. The scripts import this file by path, because they run
under python3 -I, which keeps the script directory off sys.path.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

# Read-only git: no fsmonitor hook from a repo's config, no index refresh
# writes from status, no credential prompts.
GIT = ["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false"]
ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}


def git(repo, *args, stdin=None):
    r = subprocess.run(GIT + ["-C", repo, *args], input=stdin, capture_output=True,
                       text=True, errors="surrogateescape", env=ENV)
    return r.stdout if r.returncode == 0 else None


def under(path, parent):
    return path == parent or path.startswith(parent + "/")


def is_bare(d):
    b = os.path.basename(d)
    return (b.endswith(".git") and b != ".git" and os.path.isfile(f"{d}/HEAD")
            and os.path.isdir(f"{d}/objects") and os.path.isdir(f"{d}/refs"))


def is_repo(p):
    return os.path.exists(f"{p}/.git") or is_bare(p)


def gitdir(store):
    out = git(store, "rev-parse", "--absolute-git-dir")
    return out.strip() if out else None


def load_regenerable():
    """Dir names and file globs from regenerable.txt. Returns (dirs, globs)."""
    dirs, globs = set(), []
    with open(f"{HERE}/regenerable.txt") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if any(c in line for c in "*?["):
                globs.append(line)
            else:
                dirs.add(line)
    return dirs, globs


def is_regenerable_file(name, globs):
    return any(fnmatch.fnmatch(name, g) for g in globs)


def load_witness(path):
    """Absolute paths that count as cited. One per line, blank lines ignored."""
    if not path:
        return set()
    with open(path, errors="surrogateescape") as f:
        return {os.path.normpath(l.rstrip("\n")) for l in f if l.strip()}


_reachable = {}


def reachable(store):
    """Every commit reachable from any ref in the store. Cached per store."""
    if store not in _reachable:
        out = git(store, "rev-list", "--all") or ""
        _reachable[store] = set(out.split())
    return _reachable[store]


def du(path):
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for n in filenames + [d for d in dirnames if os.path.islink(f"{dirpath}/{d}")]:
            try:
                total += os.lstat(f"{dirpath}/{n}").st_blocks * 512
            except OSError:
                pass
    return total


def gib(b):
    return f"{b / 2**30:.2f} GiB"


def guard(target, root, keeps):
    """Path checks that must hold before anything is deleted. Returns a reason or None."""
    if not os.path.isdir(target) or os.path.islink(target):
        return "not a real directory"
    if os.path.realpath(target) != target:
        return "path goes through a symlink"
    if not target.startswith(root + "/"):
        return "not strictly inside the scanned dir"
    if any(under(target, k) or under(k, target) for k in keeps):
        return "owner exception: --keep path"
    return None


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8", "surrogateescape")).hexdigest()[:16]


def read_plan(path):
    return [l.rstrip("\n").split("\t") for l in open(path, errors="surrogateescape")][1:]


def confirm_and_delete(ready, skipped, root, noun):
    """Print the summary, require the typed phrase, then rm -rf each target."""
    for t, _, reason in skipped:
        print(f"SKIP {os.path.relpath(t, root)}: {reason}")
    print(f"\nReady to delete {len(ready)} {noun}, {gib(sum(b for _, b, _ in ready))}. "
          f"{len(skipped)} skipped. This is permanent.")
    try:
        answer = input(f"Type 'delete {len(ready)}' to continue: ").strip() if ready else ""
    except EOFError:
        answer = ""
    if answer != f"delete {len(ready)}":
        print("Nothing deleted.")
        return
    failed = 0
    for t, _, _ in ready:
        r = subprocess.run(["rm", "-rf", "--", t], capture_output=True, text=True)
        if r.returncode:
            failed += 1
            print(f"FAILED {os.path.relpath(t, root)}: {r.stderr.strip()[:200]}")
        else:
            print(f"deleted {os.path.relpath(t, root)}")
    print(f"\nDone. {len(ready) - failed} deleted, {failed} failed, {len(skipped)} skipped.")


def parser(prog, doc, rescue=False):
    p = argparse.ArgumentParser(prog=prog, description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    plan = sub.add_parser("plan", help="read-only: write the plan file and print a report")
    plan.add_argument("dir", help="directory to scan; targets are strictly inside it")
    plan.add_argument("--canon", action="append", default=[], metavar="DIR",
                      help="canonical clone whose refs and LFS store prove content; repeatable")
    plan.add_argument("--keep", action="append", default=[], metavar="PATH",
                      help="never target this path or anything inside or around it; repeatable")
    plan.add_argument("--witness", metavar="FILE", help="file of absolute paths that count as cited")
    plan.add_argument("--snapshot-max", type=int, default=50, metavar="N",
                      help="local-only repos with fewer commits than N are snapshots (default 50)")
    plan.add_argument("--out", metavar="PLAN.TSV", help="where to write the plan (default beside the script)")
    ex = sub.add_parser("execute", help="re-verify each DELETE row, ask, then rm -rf")
    ex.add_argument("plan", metavar="PLAN.TSV")
    if rescue:
        rs = sub.add_parser("rescue", help="copy each KEEP row's unique files to rescued/ beside the plan")
        rs.add_argument("plan", metavar="PLAN.TSV")
    return p


def resolve_args(a):
    a.dir = os.path.realpath(a.dir)
    a.canon = [os.path.realpath(c) for c in a.canon if is_repo(os.path.realpath(c))]
    a.keep = [os.path.realpath(k) for k in a.keep]
    return a
