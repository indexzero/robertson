#!/usr/bin/env python3
"""Find the stray git repos under a directory and decide which are safe to delete.

  git-orphans.py plan <dir> --canon <clone>... [--keep <path>]... [--witness <file>]
  git-orphans.py execute <plan.tsv>

plan is read-only. It writes plan.tsv (and plan.tsv.meta.json) and prints a
report. execute re-verifies every DELETE row against its fingerprint, asks the
operator to type a phrase, then runs rm -rf. The skill never runs execute; the
operator does.

A target is the outermost repo dir, or the whole mkdtemp dir (wt-new-XXXXXX
and the like) for test fixtures, so their fake remote.git goes with them. A
target is DELETE only if every repo inside it is one of:

  pushed    has a remote outside <dir>, no stash, no modified tracked files,
            and no branch, tag, or HEAD commit missing from its remote-tracking refs
  upstream  local-only, but every commit is reachable from a ref in a --canon clone
  snapshot  local-only with fewer than --snapshot-max commits (reviewer copies,
            test fixtures). This is a policy, not a proof.

and no witness path inside it is one git cannot restore: a cited path must be
tracked and unmodified in a pushed or upstream repo. For a cited dir, the
regenerable contents listed in regenerable.txt are ignored. Anything else is
KEEP, with a reason. --keep paths are never targets.
"""
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("prunelib", f"{HERE}/prunelib.py")
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

MKDTEMP = re.compile(r"^(wt-new|text-lint|linux-goldens|mutation|fixture|tmp)-[A-Za-z0-9]{6}$")
SAFE = ("pushed", "upstream", "snapshot")
REGEN_DIRS, REGEN_GLOBS = L.load_regenerable()


def find_repos(top):
    """(path, 'work'|'bare') for every repo at or under top. Never follows symlinks."""
    out = []
    for dirpath, dirnames, filenames in os.walk(top):
        if L.is_bare(dirpath):
            out.append((dirpath, "bare"))
            dirnames[:] = []
            continue
        if ".git" in dirnames or ".git" in filenames:
            out.append((dirpath, "work"))
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git")]
    return sorted(out)


def state(repo, kind):
    """The facts the fingerprint covers. None if git cannot read the repo."""
    head = L.git(repo, "rev-parse", "-q", "--verify", "HEAD^{commit}")
    refs = L.git(repo, "for-each-ref", "--format=%(objectname) %(refname)")
    if refs is None:
        return None
    s = {"head": (head or "").strip(), "refs": refs, "stash": 0, "status": ""}
    if kind == "work":
        stash = L.git(repo, "stash", "list")
        status = L.git(repo, "status", "--porcelain=v1", "--ignored", "--ignore-submodules=all")
        if stash is None or status is None:
            return None
        s["stash"] = len(stash.splitlines())
        s["status"] = status
    return s


def fingerprint(target, repos, states):
    return L.digest([(os.path.relpath(r, target), k, states[r]) for r, k in repos])


def is_local_url(u):
    return "://" not in u and not re.match(r"^[\w.-]+@[\w.-]+:", u)


def classify(repo, kind, s, root, canon, snapshot_max):
    """Return (class, note). class is pushed, upstream, snapshot, or unsafe."""
    if s is None:
        return "unsafe", "git cannot read this repo"
    remotes = L.git(repo, "remote", "-v") or ""
    # "origin <url> (fetch)", plus " [blob:none]" on partial clones.
    urls = sorted({p[1] for p in map(str.split, remotes.splitlines()) if p[2:3] == ["(fetch)"]})
    external = [u for u in urls
                if not (is_local_url(u) and L.under(os.path.normpath(os.path.join(repo, u)), root))]
    modified = sum(1 for l in s["status"].splitlines() if not l.startswith(("??", "!!")))
    if external:
        if s["stash"]:
            return "unsafe", f"{s['stash']} stash entries"
        if modified:
            return "unsafe", f"{modified} modified tracked files"
        args = ["rev-list", "--count", "--branches", "--tags"]
        args += (["HEAD"] if s["head"] else []) + ["--not", "--remotes"]
        ahead = int((L.git(repo, *args) or "1").strip() or 1)
        if ahead:
            return "unsafe", f"{ahead} commits not on its remote"
        tips = {l.split()[0] for l in s["refs"].splitlines() if " refs/heads/" in l}
        tips |= {s["head"]} - {""}
        if not canon:
            return "pushed", "no canonical clone to cross-check"
        if tips - set().union(*(L.reachable(c) for c in canon)):
            return "pushed", "tip is on its remote but not reachable in any canonical clone"
        return "pushed", ""
    commits = set((L.git(repo, "rev-list", "--all", "--reflog") or "").split())
    have = set().union(*(L.reachable(c) for c in canon)) if canon else set()
    if commits and commits <= have:
        return "upstream", ""
    if len(commits) < snapshot_max:
        return "snapshot", ""
    return "unsafe", f"{len(commits - have)} of {len(commits)} local-only commits not reachable in any canonical clone"


def unrecoverable(cited, target, repos, cls):
    """Cited paths strictly inside target that git cannot give back."""
    bad = []
    roots = {r for r, _ in repos}
    for c in sorted(p for p in cited if p.startswith(target + "/") and p not in roots):
        owner = max((r for r, k in repos if k == "work" and c.startswith(r + "/")), key=len, default=None)
        if owner is None or cls[owner] not in ("pushed", "upstream"):
            bad.append(c)
            continue
        out = L.git(owner, "status", "--porcelain", "--ignored", "--untracked-files=all",
                    "--", os.path.relpath(c, owner))
        if out is None:
            bad.append(c)
            continue
        lines = out.splitlines()
        if os.path.isdir(c):
            lines = [l for l in lines if not (REGEN_DIRS & set(l[3:].strip('"').split("/"))
                                              or L.is_regenerable_file(l[3:].strip('"').split("/")[-1], REGEN_GLOBS))]
        if lines:
            bad.append(c)
    return bad


def plan(a):
    root, canon, keeps = a.dir, a.canon, a.keep
    cited = L.load_witness(a.witness)
    out = a.out or f"{HERE}/plan.tsv"
    repos = [rk for rk in find_repos(root) if rk[0] != root]
    print(f"repos: {sum(k == 'work' for _, k in repos)} work, {sum(k == 'bare' for _, k in repos)} bare",
          file=sys.stderr)

    units = {}
    for r, _ in repos:
        parts = os.path.relpath(r, root).split("/")
        idx = [i for i, p in enumerate(parts) if MKDTEMP.match(p)]
        units[r] = os.path.join(root, *parts[: idx[-1] + 1]) if idx else r
    targets = []
    for u in sorted(set(units.values()), key=len):
        if not any(u.startswith(t + "/") for t in targets):
            targets.append(u)
    inside = {t: [(r, k) for r, k in repos if L.under(r, t)] for t in targets}

    print("inspecting repos...", file=sys.stderr)
    states, cls, notes = {}, {}, {}
    for i, (r, k) in enumerate(repos):
        states[r] = state(r, k)
        cls[r], notes[r] = classify(r, k, states[r], root, canon, a.snapshot_max)
        if i % 200 == 199:
            print(f"  {i + 1}/{len(repos)}", file=sys.stderr)

    rows = {}
    for t in targets:
        rs = inside[t]
        reason = L.guard(t, root, keeps)
        if reason is None:
            bad = [f"{os.path.relpath(r, t) or '.'}: {notes[r]}" for r, _ in rs if cls[r] not in SAFE]
            if bad:
                reason = "unsafe repo: " + "; ".join(bad)
        if reason is None:
            lost = unrecoverable(cited, t, rs, cls)
            if lost:
                reason = f"{len(lost)} cited files git cannot restore, e.g. {os.path.relpath(lost[0], t)}"
        tally = {}
        for r, _ in rs:
            tally[cls[r]] = tally.get(cls[r], 0) + 1
        info = sorted({notes[r] for r, _ in rs if notes[r] and cls[r] in SAFE})
        rows[t] = {"action": "KEEP" if reason else "DELETE", "reason": reason or "; ".join(info),
                   "classes": ",".join(f"{c}x{n}" for c, n in sorted(tally.items())),
                   "fp": fingerprint(t, rs, states) if all(states[r] for r, _ in rs) else "-"}

    # A kept worktree needs its admin dir. Keep any target that holds one.
    changed = True
    while changed:
        changed = False
        for t, row in rows.items():
            if row["action"] != "KEEP":
                continue
            for r, k in inside[t]:
                if k != "work" or not os.path.isfile(f"{r}/.git"):
                    continue
                gd = open(f"{r}/.git").read().split("gitdir:", 1)[-1].strip()
                gd = os.path.normpath(os.path.join(r, gd))
                for t2, row2 in rows.items():
                    if row2["action"] == "DELETE" and L.under(gd, t2):
                        row2.update(action="KEEP", reason=f"holds git metadata for kept {os.path.relpath(r, root)}")
                        changed = True

    print("measuring sizes...", file=sys.stderr)
    for t in targets:
        rows[t]["bytes"] = L.du(t)

    with open(out, "w", errors="surrogateescape") as f:
        f.write("action\ttarget\tbytes\trepos\tclasses\tfingerprint\treason\n")
        for t in targets:
            r = rows[t]
            f.write(f"{r['action']}\t{os.path.relpath(t, root)}\t{r['bytes']}\t{len(inside[t])}\t"
                    f"{r['classes']}\t{r['fp']}\t{r['reason']}\n")
    with open(f"{out}.meta.json", "w") as f:
        json.dump({"root": root, "canon": canon, "keep": keeps, "witness": a.witness}, f, indent=1)

    for action in ("DELETE", "KEEP"):
        ts = [t for t in targets if rows[t]["action"] == action]
        tally = {}
        for t in ts:
            for r, _ in inside[t]:
                tally[cls[r]] = tally.get(cls[r], 0) + 1
        print(f"\n{action}: {len(ts)} dirs, {sum(len(inside[t]) for t in ts)} repos, "
              f"{L.gib(sum(rows[t]['bytes'] for t in ts))}  ({', '.join(f'{c} {n}' for c, n in sorted(tally.items()))})")
    print("\nKEEP, with reasons:")
    for t in targets:
        if rows[t]["action"] == "KEEP":
            print(f"  {os.path.relpath(t, root)}\n      {rows[t]['reason']}")
    warn = [t for t in targets if rows[t]["action"] == "DELETE" and rows[t]["reason"]]
    if warn:
        print("\nDELETE, with notes:")
        for t in warn:
            print(f"  {os.path.relpath(t, root)}\n      {rows[t]['reason']}")
    print(f"\nWrote {out}. Review it, then the operator runs:\n  python3 -I {__file__} execute {out}")


def execute(plan_path):
    meta = json.load(open(f"{plan_path}.meta.json"))
    root, keeps = meta["root"], meta["keep"]
    todo = [(f"{root}/{t}", int(b), fp) for a, t, b, _, _, fp, _ in L.read_plan(plan_path) if a == "DELETE"]
    print(f"re-verifying {len(todo)} DELETE rows...", file=sys.stderr)
    ready, skipped = [], []
    for t, b, fp in todo:
        reason = L.guard(t, root, keeps) if os.path.lexists(t) else "gone already"
        if reason is None:
            rs = find_repos(t)
            states = {r: state(r, k) for r, k in rs}
            if not all(states.values()) or fingerprint(t, rs, states) != fp:
                reason = "changed since plan"
        (skipped if reason else ready).append((t, b, reason))
    L.confirm_and_delete(ready, skipped, root, "dirs")


if __name__ == "__main__":
    a = L.parser("git-orphans.py", __doc__).parse_args()
    if a.cmd == "plan":
        plan(L.resolve_args(a))
    else:
        execute(os.path.abspath(a.plan))
