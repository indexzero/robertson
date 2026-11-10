#!/usr/bin/env python3
"""Validate the cruft-prune package: frontmatter, word budgets, routes, evals.

Exit 0 when every check passes, 1 otherwise. Prints one PASS or FAIL line per check.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
BODY_BUDGET = 1500
RUNTIME_BUDGET = 5000
MIN_CASES = 10
CASE_FIELDS = {"id", "population", "mode", "category", "prompt", "requirements", "prohibitions"}
CATEGORIES = {"recall", "false_positive", "mode_boundary", "instruction_integrity",
              "credential_handling", "stale_audit"}

failures = []


def ok(msg):
    print(f"PASS  {msg}")


def fail(msg):
    failures.append(msg)
    print(f"FAIL  {msg}")


def words(text):
    return len(re.findall(r"\b[\w'-]+\b", text))


def split(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    return (m.group(1), m.group(2)) if m else ("", text)


if not SKILL.is_file():
    fail("SKILL.md is missing")
    sys.exit(1)

front, body = split(SKILL.read_text())
if re.search(r"^name:\s*cruft-prune\s*$", front, re.M):
    ok("frontmatter names cruft-prune")
else:
    fail("frontmatter name is not cruft-prune")
if re.search(r"^\s+version:\s*[\"']\d+\.\d+\.\d+[\"']\s*$", front, re.M):
    ok("frontmatter has a semantic version")
else:
    fail("frontmatter metadata.version is missing or not semantic")
if re.search(r"^disable-model-invocation:\s*true\s*$", front, re.M):
    ok("skill is explicit-only")
else:
    fail("disable-model-invocation is not true")

n = words(body)
(ok if n <= BODY_BUDGET else fail)(f"SKILL.md body is {n} words (budget {BODY_BUDGET})")

routes = sorted(set(re.findall(r"`((?:references|scripts)/[\w./-]+)`", body)))
missing = [r for r in routes if not (ROOT / r).is_file()]
if missing:
    fail("routes missing: " + ", ".join(missing))
else:
    ok(f"{len(routes)} routes exist")

shims = [f"commands/cruft-{m}.md" for m in ("survey", "audit", "rescue")]
missing_shims = [s for s in shims if not (ROOT / s).is_file()]
if missing_shims:
    fail("command shims missing: " + ", ".join(missing_shims))
else:
    ok("3 command shims exist")

refs = [ROOT / r for r in routes if r.startswith("references/") and (ROOT / r).is_file()]
runtime = n + sum(words(p.read_text()) for p in refs)
(ok if runtime <= RUNTIME_BUDGET else fail)(
    f"runtime is {runtime} words across SKILL.md and {len(refs)} present references (budget {RUNTIME_BUDGET})")

for bad, label in ((r"[–—]", "em or en dash"), (r"^\*\*[^*\n]+:\*\*", "bold-label line")):
    hits = [i + 1 for i, line in enumerate(body.splitlines()) if re.search(bad, line, re.M)]
    if hits:
        fail(f"{label} at SKILL.md body line(s) {hits}")
    else:
        ok(f"no {label}")

cases_path = ROOT / "evals" / "cases.json"
if not cases_path.is_file():
    fail("evals/cases.json is missing")
else:
    try:
        cases = json.loads(cases_path.read_text())["cases"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        cases = []
        fail(f"evals/cases.json is invalid: {exc}")
    ids = [c.get("id") for c in cases if isinstance(c, dict)]
    malformed = [c.get("id", f"case {i}") for i, c in enumerate(cases)
                 if not isinstance(c, dict) or not CASE_FIELDS.issubset(c)
                 or not c.get("requirements") or not c.get("prohibitions")]
    found = {c.get("category") for c in cases if isinstance(c, dict)}
    if len(cases) < MIN_CASES:
        fail(f"evals has {len(cases)} cases (minimum {MIN_CASES})")
    elif len(ids) != len(set(ids)):
        fail("eval case ids are not unique")
    elif malformed:
        fail("malformed eval cases: " + ", ".join(map(str, malformed)))
    elif not CATEGORIES <= found:
        fail("eval categories missing: " + ", ".join(sorted(CATEGORIES - found)))
    else:
        ok(f"{len(cases)} eval cases cover every required category")

if failures:
    print(f"\n{len(failures)} failure(s)")
    sys.exit(1)
print("\ncruft-prune package validation passed")
