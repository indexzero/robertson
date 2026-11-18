#!/usr/bin/env python3
"""Report where the bytes under a directory are. No verdicts.

  survey.py <dir> [--top N]

Every regular file is counted once, in the first category that matches:

  node_modules  under a node_modules dir
  git           inside a .git dir or a bare *.git repo
  fixture       under a mkdtemp-style dir (name-XXXXXX with a six-char suffix)
  build         under a regenerable dir from regenerable.txt, or a regenerable file
  worktree      a file inside a nested repo's working tree
  evidence      everything else: logs, notes, probes, copies with no .git

Prints bytes and file counts per category, then the largest directories two
levels below <dir> for the evidence category. Read-only. Symlinks are not followed.
"""
import argparse
import importlib.util
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("prunelib", f"{HERE}/prunelib.py")
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

REGEN_DIRS, REGEN_GLOBS = L.load_regenerable()
FIXTURE = re.compile(r"^[A-Za-z0-9._-]+-[A-Za-z0-9]{6}$")
CATS = ["node_modules", "git", "fixture", "build", "worktree", "evidence"]


def survey(top):
    summary = defaultdict(lambda: [0, 0])
    by_dir = defaultdict(int)
    stack = [(top, None, False)]
    while stack:
        d, cat, in_wt = stack.pop()
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        names = {e.name for e in entries}
        here_wt = in_wt or (".git" in names and d != top)
        for e in entries:
            try:
                if e.is_symlink():
                    continue
                if e.is_dir(follow_symlinks=False):
                    c = cat
                    if c is None:
                        if e.name == "node_modules":
                            c = "node_modules"
                        elif e.name == ".git" or L.is_bare(e.path):
                            c = "git"
                        elif FIXTURE.match(e.name) and d != top:
                            c = "fixture"
                        elif e.name in REGEN_DIRS:
                            c = "build"
                    stack.append((e.path, c, here_wt))
                elif e.is_file(follow_symlinks=False):
                    size = e.stat(follow_symlinks=False).st_blocks * 512
                    c = cat
                    if c is None and e.name == ".git":
                        c = "git"
                    if c is None and L.is_regenerable_file(e.name, REGEN_GLOBS):
                        c = "build"
                    if c is None:
                        c = "worktree" if here_wt else "evidence"
                    summary[c][0] += 1
                    summary[c][1] += size
                    if c == "evidence":
                        rel = os.path.relpath(e.path, top).split("/")
                        by_dir["/".join(rel[:2]) if len(rel) > 2 else rel[0]] += size
            except OSError:
                continue
    return summary, by_dir


if __name__ == "__main__":
    p = argparse.ArgumentParser(prog="survey.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dir")
    p.add_argument("--top", type=int, default=20, help="how many evidence dirs to list (default 20)")
    a = p.parse_args()
    top = os.path.realpath(a.dir)
    summary, by_dir = survey(top)
    print(f"{'category':<13}{'files':>10}{'GiB':>9}")
    for c in CATS:
        n, b = summary.get(c, (0, 0))
        print(f"{c:<13}{n:>10}{b / 2**30:>9.2f}")
    print(f"\nlargest evidence dirs under {top}:")
    for d, b in sorted(by_dir.items(), key=lambda kv: -kv[1])[: a.top]:
        print(f"{b / 2**20:>9.1f}M  {d}")
