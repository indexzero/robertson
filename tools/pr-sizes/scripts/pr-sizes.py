#!/usr/bin/env python3
"""Count the lines that a stack of pull requests adds, by group. Requires Python 3.10+ and git; gh for PR numbers.

Usage: pr-sizes.py --repo PATH --base REF [options] ITEM [ITEM ...]

Each ITEM is a PR number (12 or #12, resolved with gh) or a git ref
(ref:NAME forces a ref). Items are in stack order: each is measured
against the one before it, the first against --base.

This script reads git objects only. It never checks out, commits or
fetches. --run-tests is the one option that runs the target's code.
"""

import argparse
from datetime import date
import json
from pathlib import Path
import re
import subprocess
import sys


GROUPS = ("docs", "code", "tests", "generated")
HEADLINE = ("docs", "code", "tests")

# A generic starting point. Every repository lays out its files its own
# way: write a config for it (see examples/) rather than trusting this.
DEFAULT_CONFIG = {
    "description": "generic default",
    "rules": [
        {"group": "generated", "patterns": [
            "**/package.json", "**/package-lock.json", "**/npm-shrinkwrap.json",
            "**/yarn.lock", "**/pnpm-lock.yaml", "**/*.lock", "**/go.sum",
            "**/*.snap", "**/*.min.js", "dist/**", "build/**", "vendor/**"]},
        {"group": "docs", "patterns": [
            "**/*.md", "**/*.markdown", "**/*.rst", "**/*.txt", "doc/**", "docs/**"]},
        {"group": "tests", "patterns": [
            "test/**", "tests/**", "**/__tests__/**", "**/*.test.*", "**/*.spec.*",
            "**/*_test.go", "**/test_*.py", "**/*_test.py"]},
        {"group": "code", "patterns": [
            "**/*.js", "**/*.mjs", "**/*.cjs", "**/*.jsx", "**/*.ts", "**/*.tsx",
            "**/*.py", "**/*.go", "**/*.rs", "**/*.c", "**/*.h", "**/*.cc",
            "**/*.cpp", "**/*.hpp", "**/*.java", "**/*.kt", "**/*.swift",
            "**/*.rb", "**/*.sh", "**/*.zig"]},
    ],
    "comment_prefixes": [
        {"patterns": ["**/*.js", "**/*.mjs", "**/*.cjs", "**/*.jsx", "**/*.ts",
                      "**/*.tsx", "**/*.go", "**/*.rs", "**/*.c", "**/*.h",
                      "**/*.cc", "**/*.cpp", "**/*.hpp", "**/*.java", "**/*.kt",
                      "**/*.swift", "**/*.zig"], "prefixes": ["//"]},
        {"patterns": ["**/*.py", "**/*.rb", "**/*.sh"], "prefixes": ["#"]},
    ],
    "block_comment_prefixes": ["/*", "*", "*/"],
    "test_call_regex": r"(^|[^.A-Za-z_$])(test|it)(\.(only|solo|skip|todo))?\s*\(",
    "test_files": None,
    "test_count_regex": r"# tests = (\d+)",
}

MOVED_NEW = "\x1b[1;7;33m"  # bold reverse yellow
MOVED_OLD = "\x1b[1;7;35m"  # bold reverse magenta
ANSI = re.compile(r"\x1b\[[0-9;]*m")


class Error(Exception):
    pass


def run(args, *, cwd=None, allowed=(0,)):
    result = subprocess.run(args, cwd=cwd, capture_output=True)
    if result.returncode not in allowed:
        err = result.stderr.decode(errors="replace").strip()
        raise Error(err or f"{args[0]} exited {result.returncode}")
    return result.stdout.decode(errors="replace")


class Repo:
    def __init__(self, path):
        self.path = str(Path(path).expanduser().resolve())

    def git(self, *args, allowed=(0,)):
        return run(["git", "--literal-pathspecs", "-C", self.path, *args], allowed=allowed)

    def commit(self, ref):
        try:
            return self.git("rev-parse", "--verify", "--quiet", ref + "^{commit}").strip()
        except Error:
            raise Error(f"{ref} is not a commit in {self.path}; fetch it first")


# --- configuration --------------------------------------------------------

def glob_regex(pattern):
    """`**/` is any number of directories, `**` anything, `*` and `?` stay within one name."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + r"\Z")


class Config:
    def __init__(self, raw):
        merged = {**DEFAULT_CONFIG, **raw}
        self.description = merged.get("description", "")
        self.rules = []
        for rule in merged["rules"]:
            if rule["group"] not in GROUPS:
                raise Error(f"unknown group {rule['group']!r}; use one of {', '.join(GROUPS)}")
            self.rules.append((rule["group"], [glob_regex(p) for p in rule["patterns"]], rule["patterns"]))
        self.comments = [([glob_regex(p) for p in c["patterns"]], c["prefixes"])
                         for c in merged["comment_prefixes"]]
        self.block_prefixes = merged["block_comment_prefixes"]
        self.test_call = re.compile(merged["test_call_regex"])
        files = merged["test_files"]
        if files is None:
            files = [p for g, _, pats in self.rules if g == "tests" for p in pats]
        self.test_files = [glob_regex(p) for p in files]
        self.test_count = re.compile(merged["test_count_regex"])
        self.raw = merged

    def group(self, path):
        for name, regexes, _ in self.rules:
            if any(r.match(path) for r in regexes):
                return name
        return "unassigned"

    def comment_prefixes(self, path):
        for regexes, prefixes in self.comments:
            if any(r.match(path) for r in regexes):
                return prefixes
        return []

    def is_test_file(self, path):
        return any(r.match(path) for r in self.test_files)


def load_config(path):
    if not path:
        return Config({})
    return Config(json.loads(Path(path).expanduser().read_text()))


# --- resolving the stack ---------------------------------------------------

PR_ITEM = re.compile(r"#?([1-9][0-9]*)")


def resolve(repo, items, gh_repo):
    resolved = []
    for item in items:
        match = PR_ITEM.fullmatch(item)
        if match and not item.startswith("ref:"):
            number = int(match[1])
            args = ["gh", "pr", "view", str(number), "--json",
                    "number,title,state,headRefName,headRefOid,baseRefName,baseRefOid,commits"]
            if gh_repo:
                args += ["--repo", gh_repo]
            pr = json.loads(run(args, cwd=repo.path))
            head = repo.commit(pr["headRefOid"])
            resolved.append({
                "label": f"#{number}", "pr": number, "title": pr["title"], "state": pr["state"],
                "branch": pr["headRefName"], "base_branch": pr["baseRefName"],
                "base_oid": pr["baseRefOid"], "pr_commits": len(pr["commits"]), "head": head})
        else:
            ref = item.removeprefix("ref:")
            head = repo.commit(ref)
            resolved.append({
                "label": ref, "pr": None, "branch": None, "head": head,
                "title": repo.git("log", "-1", "--format=%s", head).strip()})
    return resolved


def check_stack(repo, base, stack):
    """What the measurement assumes, stated per item. Problems are flagged, not fixed."""
    flags = []
    prev, prev_item = base, None
    for item in stack:
        head = item["head"]
        item["base"] = prev
        item["commits"] = int(repo.git("rev-list", "--count", f"{prev}..{head}").strip())
        item["parents"] = repo.git("log", "-1", "--format=%P", head).split()
        result = subprocess.run(["git", "-C", repo.path, "merge-base", "--is-ancestor", prev, head])
        ancestor = result.returncode == 0
        item["stacked"] = ancestor
        label = item["label"]
        if not ancestor:
            flags.append(f"{label}: {prev[:7]} is not an ancestor of {head[:7]}; its diff includes changes from outside the stack")
        if item["commits"] != 1:
            flags.append(f"{label}: {item['commits']} commits in {prev[:7]}..{head[:7]}, not one")
        elif item["parents"][0] != prev:
            flags.append(f"{label}: the parent of {head[:7]} is {item['parents'][0][:7]}, not {prev[:7]}")
        if item["pr"] is not None:
            if item["pr_commits"] != item["commits"]:
                flags.append(f"{label}: GitHub lists {item['pr_commits']} commits, git counts {item['commits']}")
            if prev_item and prev_item.get("branch") and item["base_branch"] != prev_item["branch"]:
                flags.append(f"{label}: base branch is {item['base_branch']}, not {prev_item['branch']}")
            if item["base_oid"] != prev:
                flags.append(f"{label}: base branch {item['base_branch']} is at {item['base_oid'][:7]} on GitHub, not {prev[:7]}")
        status = repo.git("diff", "--name-status", "-M", "-z", prev, head).split("\0")
        changes, i = [], 0
        while i < len(status) - 1:
            code = status[i]
            if code[:1] in "RC":
                changes.append(f"{code[:1]} {status[i + 1]} -> {status[i + 2]}")
                i += 3
            else:
                if code[:1] in "AD":
                    changes.append(f"{code[:1]} {status[i + 1]}")
                i += 2
        item["created_deleted_renamed"] = changes
        prev, prev_item = head, item
    return flags


# --- measuring one diff ----------------------------------------------------

def hunk_lines(text):
    """The + and - lines of a diff's hunks, without file headers."""
    added, removed, in_hunk = [], [], False
    for line in text.split("\n"):
        if line.startswith("diff --git "):
            in_hunk = False
        elif line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line.startswith("+"):
            added.append(line[1:])
        elif in_hunk and line.startswith("-"):
            removed.append(line[1:])
    return added, removed


def substantive(lines, group, prefixes):
    count = 0
    for line in lines:
        text = line.strip()
        if not text:
            continue
        if group in ("code", "tests") and any(text.startswith(p) for p in prefixes):
            continue
        count += 1
    return count


def measure(repo, config, a, b):
    files = []
    numstat = repo.git("diff", "--numstat", "-z", "--no-renames", a, b).split("\0")
    for entry in numstat:
        if not entry:
            continue
        add, rem, path = entry.split("\t", 2)
        group = config.group(path)
        binary = add == "-"
        row = {"path": path, "group": group, "added": 0 if binary else int(add),
               "removed": 0 if binary else int(rem), "binary": binary,
               "substantive": 0, "tests_added": 0, "tests_removed": 0, "block_like": 0}
        if not binary:
            diff = repo.git("diff", "--no-renames", "--no-color", "--no-ext-diff", "--no-textconv",
                            "-U0", a, b, "--", path)
            added, removed = hunk_lines(diff)
            prefixes = config.comment_prefixes(path)
            row["substantive"] = substantive(added, group, prefixes)
            if group in ("code", "tests"):
                row["block_like"] = sum(1 for l in added
                                        if any(l.strip().startswith(p) for p in config.block_prefixes))
            if config.is_test_file(path):
                row["tests_added"] = sum(1 for l in added if config.test_call.search(l))
                row["tests_removed"] = sum(1 for l in removed if config.test_call.search(l))
        files.append(row)

    groups = {g: {"files": 0, "added": 0, "removed": 0, "substantive": 0,
                  "tests_added": 0, "tests_removed": 0}
              for g in (*GROUPS, "unassigned")}
    for row in files:
        g = groups[row["group"]]
        g["files"] += 1
        for key in ("added", "removed", "substantive", "tests_added", "tests_removed"):
            g[key] += row[key]
    for g in groups.values():
        g["net"] = g["added"] - g["removed"]

    doc_paths = [r["path"] for r in files if r["group"] == "docs" and not r["binary"]]
    words = {"added": 0, "removed": 0}
    if doc_paths:
        diff = repo.git("diff", "--no-renames", "--no-color", "--no-ext-diff", "--no-textconv",
                        "--word-diff=porcelain", a, b, "--", *doc_paths)
        added, removed = hunk_lines(diff)
        words = {"added": sum(len(l.split()) for l in added),
                 "removed": sum(len(l.split()) for l in removed)}

    return {"base": a, "head": b, "files": files, "groups": groups, "doc_words": words,
            "moved": moved_lines(repo, a, b, [r["path"] for r in files
                                              if r["group"] in ("code", "tests") and not r["binary"]])}


def moved_lines(repo, a, b, paths):
    """Lines git's --color-moved=blocks marks as moved, per file, added side and removed side."""
    if not paths:
        return {}
    out = run(["git", "--literal-pathspecs", "-C", repo.path,
               "-c", "color.diff.newMoved=bold reverse yellow",
               "-c", "color.diff.newMovedAlternative=bold reverse yellow",
               "-c", "color.diff.oldMoved=bold reverse magenta",
               "-c", "color.diff.oldMovedAlternative=bold reverse magenta",
               "diff", "--no-renames", "--no-ext-diff", "--no-textconv", "--color=always",
               "--color-moved=blocks", a, b, "--", *paths])
    moved, path = {}, None
    for line in out.split("\n"):
        plain = ANSI.sub("", line)
        if plain.startswith("diff --git a/"):
            rest = plain[len("diff --git a/"):]
            path = rest[:(len(rest) - 3) // 2]
        elif line.startswith(MOVED_NEW + "+"):
            moved.setdefault(path, [0, 0])[0] += 1
        elif line.startswith(MOVED_OLD + "-"):
            moved.setdefault(path, [0, 0])[1] += 1
    return {p: {"added": v[0], "removed": v[1]} for p, v in moved.items()}


def tests_in_tree(repo, config, commit):
    total = 0
    for path in repo.git("ls-tree", "-r", "--name-only", "-z", commit).split("\0"):
        if path and config.is_test_file(path):
            blob = repo.git("cat-file", "blob", f"{commit}:{path}")
            total += sum(1 for l in blob.split("\n") if config.test_call.search(l))
    return total


# --- the optional test run -------------------------------------------------

def worktrees(repo):
    found, path = {}, None
    for line in repo.git("worktree", "list", "--porcelain").split("\n"):
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line.startswith("HEAD ") and path:
            found.setdefault(line[5:], []).append(path)
    return found


def run_tests(repo, config, command, commits, explicit):
    """Run COMMAND in a clean worktree at each commit. Never creates or changes a worktree."""
    by_head, results = worktrees(repo), {}
    for commit in commits:
        candidates = [explicit[commit]] if commit in explicit else by_head.get(commit, [])
        result = {"worktree": None, "count": None, "exit": None, "note": None}
        for path in candidates:
            head = run(["git", "-C", path, "rev-parse", "HEAD"]).strip()
            dirty = run(["git", "-C", path, "status", "--porcelain"]).strip()
            if head != commit:
                result["note"] = f"{path} is at {head[:7]}"
                continue
            if dirty:
                result["note"] = f"{path} has local changes; skipped"
                continue
            proc = subprocess.run(command, shell=True, cwd=path, capture_output=True, text=True)
            output = proc.stdout + proc.stderr
            counts = config.test_count.findall(output)
            after = run(["git", "-C", path, "status", "--porcelain"]).strip()
            result = {"worktree": path, "exit": proc.returncode,
                      "count": int(counts[-1]) if counts else None,
                      "note": "the run changed files in the worktree" if after else None}
            break
        else:
            if not candidates:
                result["note"] = "no worktree at this commit"
        results[commit] = result
    return results


# --- the report ------------------------------------------------------------

def table(header, rows, right=None):
    right = right if right is not None else set(range(1, len(header)))
    lines = ["| " + " | ".join(header) + " |",
             "| " + " | ".join("---:" if i in right else "---" for i in range(len(header))) + " |"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def ratio(a, b):
    return f"{a / b:.1f}" if b else "n/a"


def render(data):
    stack, steps, total, summed = data["stack"], data["steps"], data["total"], data["sum"]
    s = lambda h: h[:7]
    out = [f"# Sizes of {', '.join(i['label'] for i in stack)}", "",
           f"Lines added and removed in {len(stack)} stacked changes of `{data['repo']}`, "
           f"from `{s(data['base'])}` to `{s(stack[-1]['head'])}`, measured {data['date']}. "
           f"Groups from: {data['config']}.", ""]

    out += [table(["Item", "Branch", "Commit", "Base", "Commits", "Title"],
                  [[i["label"], f"`{i['branch']}`" if i["branch"] else "", f"`{s(i['head'])}`",
                    f"`{s(i['base'])}`", i["commits"], i["title"]] for i in stack], right={4}), ""]
    out += ["## Checks", ""]
    out += [f"- {f}" for f in data["flags"]] or ["- Each item is one commit whose parent is the item before it; every PR's base on GitHub matches."]
    for i in stack:
        if i["created_deleted_renamed"]:
            out.append(f"- {i['label']} creates, deletes or renames: " +
                       ", ".join(f"`{c}`" for c in i["created_deleted_renamed"]) + ".")
    unassigned = sorted({r["path"] for r in total["files"] if r["group"] == "unassigned"})
    if unassigned:
        out.append("- Not in any group, counted nowhere above the unassigned row: " +
                   ", ".join(f"`{p}`" for p in unassigned) + ".")
    block = sum(r["block_like"] for r in total["files"])
    if block:
        out.append(f"- {block} added code or test lines start like a block comment and count as substantive.")
    binary = sorted({r["path"] for r in total["files"] if r["binary"]})
    if binary:
        out.append("- Binary, counted as 0 lines: " + ", ".join(f"`{p}`" for p in binary) + ".")
    out.append("")

    rows = [(i["label"], m) for i, m in zip(stack, steps)] + [("Sum of the items", summed), ("Stack, one diff", total)]
    out += ["## Lines added", "",
            "Raw is `git diff --numstat`. Substantive is added lines that are not blank; "
            "for code and tests, also not a line that is only a comment. For docs it is non-blank.", ""]
    out += [table(["Item", "Docs raw", "Code raw", "Tests raw", "Docs non-blank",
                   "Code substantive", "Tests substantive"],
                  [[label] + [m["groups"][g]["added"] for g in HEADLINE] +
                   [m["groups"][g]["substantive"] for g in HEADLINE] for label, m in rows]), ""]

    show = [g for g in (*GROUPS, "unassigned") if total["groups"][g]["files"] or g in HEADLINE]
    out += ["## Added, removed and net (raw)", ""]
    out += [table(["Item"] + [f"{g.capitalize()} +/-/net" for g in show],
                  [[label] + [f"{m['groups'][g]['added']} / {m['groups'][g]['removed']} / {m['groups'][g]['net']}"
                              for g in show] for label, m in rows], right=set()), ""]

    out += ["## Files changed per group", ""]
    out += [table(["Item"] + [g.capitalize() for g in show] + ["All"],
                  [[label] + [m["groups"][g]["files"] for g in show] + [len(m["files"])]
                   for label, m in rows if label != "Sum of the items"]), ""]

    tc = data["tests_in_tree"]
    out += ["## Test cases", "",
            "Lines matching the test-call pattern in test files; a removed call is often a renamed test.", ""]
    trows = [["base", "", "", "", tc[data["base"]]]]
    trows += [[i["label"], m["groups"]["tests"]["tests_added"], m["groups"]["tests"]["tests_removed"],
               f"{m['groups']['tests']['tests_added'] - m['groups']['tests']['tests_removed']:+d}", tc[i["head"]]]
              for i, m in zip(stack, steps)]
    trows.append(["Stack", total["groups"]["tests"]["tests_added"], total["groups"]["tests"]["tests_removed"],
                  f"{total['groups']['tests']['tests_added'] - total['groups']['tests']['tests_removed']:+d}",
                  tc[stack[-1]["head"]]])
    out += [table(["Item", "Calls added", "Removed", "Net", "Tests at the commit"], trows), ""]
    if data.get("test_runs"):
        out += ["Test runs (`" + data["test_command"] + "`):", ""]
        out += [table(["Commit", "Worktree", "Exit", "Count", "Note"],
                      [[f"`{s(c)}`", r["worktree"] or "", "" if r["exit"] is None else r["exit"],
                        "" if r["count"] is None else r["count"], r["note"] or ""]
                       for c, r in data["test_runs"].items()], right={2, 3}), ""]

    out += ["## Docs in words", "", "Whitespace-separated words on `+` and `-` lines of `git diff --word-diff=porcelain`.", ""]
    out += [table(["Item", "Words added", "Words removed"],
                  [[label, m["doc_words"]["added"], m["doc_words"]["removed"]] for label, m in rows]), ""]

    g = total["groups"]
    out += ["## Ratio of tests to code, stack", "",
            f"{ratio(g['tests']['added'], g['code']['added'])} raw added, "
            f"{ratio(g['tests']['substantive'], g['code']['substantive'])} substantive added, "
            f"{ratio(g['tests']['net'], g['code']['net'])} net.", ""]

    out += ["## Moved lines in code and tests", "", "Lines `git diff --color-moved=blocks` marks as moved, added side / removed side.", ""]
    mrows = [[label, f"`{p}`", v["added"], v["removed"]] for label, m in rows if label != "Sum of the items"
             for p, v in sorted(m["moved"].items())]
    out += [table(["Item", "File", "Moved in", "Moved out"], mrows, right={2, 3}) if mrows else "None.", ""]

    out += ["## File to group", ""]
    by_group = {}
    for r in total["files"]:
        by_group.setdefault(r["group"], []).append(r["path"])
    out += [f"- {grp.capitalize()}: " + ", ".join(f"`{p}`" for p in sorted(paths)) + "."
            for grp, paths in sorted(by_group.items(), key=lambda kv: (*GROUPS, "unassigned").index(kv[0]))]
    out += ["", "## Largest added files", ""]
    biggest = sorted(total["files"], key=lambda r: -r["added"])[:5]
    out += [table(["File", "Group", "Added", "Removed", "Share of its group's added lines"],
                  [[f"`{r['path']}`", r["group"], r["added"], r["removed"],
                    f"{100 * r['added'] / g[r['group']]['added']:.0f}%" if g[r["group"]]["added"] else ""]
                   for r in biggest], right={2, 3, 4}), ""]
    return "\n".join(out)


def summed(steps):
    out = {"files": [], "groups": {}, "doc_words": {"added": 0, "removed": 0}, "moved": {}}
    for g in (*GROUPS, "unassigned"):
        out["groups"][g] = {k: sum(m["groups"][g][k] for m in steps) for k in steps[0]["groups"][g]}
    for k in ("added", "removed"):
        out["doc_words"][k] = sum(m["doc_words"][k] for m in steps)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("items", nargs="+", metavar="ITEM", help="PR number or ref:NAME, in stack order")
    parser.add_argument("--repo", default=".", help="local clone (default: .)")
    parser.add_argument("--base", required=True, help="the commit the first item is measured against")
    parser.add_argument("--config", help="JSON file of groups and patterns (default: built-in generic)")
    parser.add_argument("--gh-repo", help="OWNER/REPO for gh, when the clone's remote is not it")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--out", help="write the Markdown report here (default: stdout)")
    parser.add_argument("--json", help="also write every count as JSON here")
    parser.add_argument("--run-tests", metavar="COMMAND",
                        help="OFF by default. Run COMMAND (via the shell) in a clean existing worktree at each commit")
    parser.add_argument("--worktree", action="append", default=[], metavar="ITEM=PATH",
                        help="the worktree for an item's run; otherwise any registered worktree at its commit")
    parser.add_argument("--strict", action="store_true", help="exit 2 if any check is flagged")
    args = parser.parse_args(argv)

    try:
        repo = Repo(args.repo)
        config = load_config(args.config)
        base = repo.commit(args.base)
        stack = resolve(repo, args.items, args.gh_repo)
        flags = check_stack(repo, base, stack)
        steps = [measure(repo, config, i["base"], i["head"]) for i in stack]
        total = measure(repo, config, base, stack[-1]["head"])
        data = {"repo": repo.path, "date": args.date, "base": base, "stack": stack,
                "config": args.config or "built-in generic default", "flags": flags,
                "steps": steps, "sum": summed(steps), "total": total,
                "tests_in_tree": {c: tests_in_tree(repo, config, c)
                                  for c in [base] + [i["head"] for i in stack]}}
        if args.run_tests:
            explicit = {}
            for spec in args.worktree:
                label, _, path = spec.partition("=")
                match = [i["head"] for i in stack if i["label"] in (label, "#" + label.lstrip("#"))]
                explicit[match[0] if match else repo.commit(label)] = str(Path(path).expanduser())
            data["test_command"] = args.run_tests
            data["test_runs"] = run_tests(repo, config, args.run_tests,
                                          [base] + [i["head"] for i in stack], explicit)
        report = render(data) + "\n"
    except Error as e:
        print(f"pr-sizes: {e}", file=sys.stderr)
        return 1

    if args.out:
        Path(args.out).expanduser().write_text(report)
    else:
        sys.stdout.write(report)
    if args.json:
        Path(args.json).expanduser().write_text(json.dumps(data, indent=2) + "\n")
    return 2 if args.strict and flags else 0


if __name__ == "__main__":
    sys.exit(main())
