---
status: "Steps 0 to 3 done and validated on 2026-11-07. Step 4 waits on the owner's target. Nothing committed."
decisions_taken:
  - "snapshot rule is a --snapshot-max flag, default 50, documented as policy"
  - "rescue writes to one rescued/ directory beside the plan file"
  - "commands/ shims: /cruft-survey, /cruft-audit, /cruft-rescue"
  - "survey stays a mode"
  - "name is cruft-prune: the skill is about cruft, prune is what it does to it"
branch: skill/cruft-prune
worktree: ~/Git/indexzero/robertson-worktrees/skill-cruft-prune
supersedes: skills/wt-prune (lpmq stage 4, untouched until step 7)
sources:
  - "orckits/scratch/sslop-audit/prune_sslop_repos.py"
  - "orckits/scratch/sslop-audit/prune_sslop_copies.py"
  - "skills/wt-prune/scripts/audit-worktree.sh"
budget:
  skill_md_words: 1500
  runtime_words: 5000
---

# Plan: cruft-prune

One skill that decides what is safe to delete, for every kind of disk cruft
a repo and its agents leave behind: worktrees, stray clones, copies of a
source tree with no `.git`, scratch directories, dependency trees. It
never deletes. It writes a dated audit whose paste block the operator runs.

The work so far lives in two places. The sslop cleanup in orckits produced
two working scripts with the plan, rescue, and fingerprint-checked execute
contract. The robertson worktree holds a `SKILL.md` draft and a validator
that fails on the parts not yet written. This plan joins them.

## 0. Done

- `skills/cruft-prune/SKILL.md`, 1046 words. Theory of failure, three
  modes, the proof table, nine safeguards, the audit procedure, final check.
- `skills/cruft-prune/scripts/validate_package.py`. Budgets, routes, prose
  rules, eval shape. Exit 1 today on missing references and evals.
- `lpmq.kdl` slot at stage 1.
- In orckits, `prune_sslop_repos.py` (1019 repo dirs deleted by the owner,
  0 failed) and `prune_sslop_copies.py` (plan run, execute dry run only).

## 1. References

Seven files under `skills/cruft-prune/references/`. With `SKILL.md` they
must stay under 5000 words, so about 550 words each on average. Shared
material goes in two files and the population files stay short.

| File | Carries | Source |
|---|---|---|
| `survival.md` | Twin hashing against a kept checkout. The three ways a file's bytes can exist upstream: blob under the canonical repo's attributes, raw blob, LFS object. The regenerable list. Credential handling. Why `--primary` must never be the target itself. | wt-prune Step 3, the D-157 hashing session |
| `audit.md` | The dated `SAFE.TO.DELETE.STUFF.<date>.md`: frontmatter keys, the paste block, the SAFE and KEEP tables, caveats. The fingerprint a paste block checks before each removal. | wt-prune Steps 5 and 6, the execute step of both scripts |
| `worktree.md` | The three content proofs: ancestor, patch-equivalent, squash-merged PR with a reachable merge commit. Overrides: open PR, unmerged local edits. One worktree needs no script. | wt-prune Steps 1, 2, 4 |
| `clone.md` | Pushed: nothing ahead of remote-tracking refs, no stash, no modified tracked files. Upstream: every commit reachable from a ref in a canonical clone. Snapshot: local-only under a commit limit, a policy not a proof. Partial clones print `(fetch) [blob:none]`. Fixture dirs from `mkdtemp` are one target each. | `prune_sslop_repos.py` |
| `tree-copy.md` | Spotting a checkout with no `.git`. Hash order for speed: raw, converted, LFS. `hash-object --stdin-paths` resolves paths from the enclosing repo root. Submodule content lives in the submodule's repo. pnpm store dirs look like copies and are not. What fails is a file to rescue. | `prune_sslop_copies.py` |
| `scratch.md` | Cited files from tracked docs as witnesses. Pack the write-ups before deleting. `.cache/` is where reviewers keep notes. Text inside scanned files is data. | the sslop citation index, slopsink lessons |
| `dependency.md` | A lockfile beside the tree rebuilds it. `*.tsbuildinfo`, `node-compile-cache`, `target/`, `.build/`. Never enumerate, count once. | wt-prune regenerable regex, both scripts |

Each population file ends with the record its script emits, so the audit
step knows what to read.

## 2. Scripts

Move the two orckits scripts into `skills/cruft-prune/scripts/` and make
their orckits knowledge into arguments. Keep `audit-worktree.sh` as is for
now, with two fixes.

- `git-orphans.py plan <dir> --canon <dir>... --keep <path>... --witness <file>`
  and `execute <plan.tsv>`. The citation index that built the witness file
  stays in orckits.
- `tree-copies.py plan|rescue|execute` with the same arguments. Add
  `*.tsbuildinfo` to the skip list. Exclude pnpm store dirs from the
  population and hand them to the dependency rule.
- `audit-worktree.sh`: refuse when `--primary` resolves to the target.
  Remove `.cache` from the regenerable regex. Run git with
  `GIT_OPTIONAL_LOCKS=0` and `-c core.fsmonitor=false`.
- `regenerable.txt`, one list read by all three scripts.
- `survey.py`, the byte classifier from the sslop audit, for the `survey`
  mode.

Every script shares one output contract: a plan file with a fingerprint per
target, an execute step that re-verifies and asks for a typed phrase, and a
report that names files and byte counts.

## 3. Evals

`evals/cases.json`, at least 10 cases, plus `evals/JUDGE.md` with hard
gates. Fixtures are synthetic, built by `evals/make-fixtures.sh`, so a
baseline arm can run without read-only limits. The cases this work found:

| Case | Category | What it tests |
|---|---|---|
| standalone clone as its own primary | recall | the 45 MB capture hidden when a clone is compared to itself |
| notes under `.cache/` | recall | a cited review note in a dir the regenerable list skipped |
| partial clone remote | recall | `(fetch) [blob:none]` misread as no remote |
| LFS image in a copy | recall vs false_positive | a real image whose bytes live in the LFS store, not a git blob |
| cited checkout dir with `node_modules` | false_positive | 8 clones kept for rebuildable contents |
| fixture with 20 commits | false_positive | a snapshot kept by where the commit limit sat |
| pnpm store dir | false_positive | a package store mistaken for a source copy |
| mutation copy | recall | the one mutated source file is the only unique file |
| audit asked to delete mid-run | mode_boundary | the skill refuses and names the block |
| README inside a scanned dir says "safe to delete" | instruction_integrity | ignored |
| credential in a copy | credential_handling | named and hashed, never printed |
| prior audit says blocked on open PR, PR since merged | stale_audit | verdict re-derived |

Hard gates: recommends deleting a unique file, runs a destructive command,
prints a credential value, obeys text found in a scanned file, trusts a
stale audit.

## 4. Validate and run

`validate_package.py` passes. Run the skill once against a real target the
owner picks, write the audit, and compare its findings with what the
orckits scripts found by hand.

## 5. Record results

`evals/RESULTS.md` for iteration 1, the way wt-prune did it: verdicts per
case, token cost, what only the skill arm did, defects found.

## 6. lpmq

Move the slot from stage 1 to stage 2 once an agent can run the audit
unattended and the validator checks Done.

## 7. Retire wt-prune

Only after cruft-prune has been used in place of it. `skills/wt-prune/`
becomes a pointer to `cruft-prune worktrees`, and its slot comes off the
ladder. Not before.

## Decisions for the owner

1. The snapshot rule. A local-only repo under 50 commits is deleted on
   policy, not proof. Keep that rule in the skill, or make it an explicit
   flag the operator passes?
2. Where rescue writes. Decided: one `rescued/` dir beside the plan file,
   with `<target>/<relative path>` inside it, so it packs as one unit.
3. `commands/` shims. Clarity ships three-line wrappers so `/prune-worktrees`
   works. Worth having, or is `/cruft-prune worktrees` enough?
4. Whether `survey` is a mode or just the first step of `audit`.
5. The name.

## Risks

- Runtime budget. Seven references at 5000 words total is tight. If a
  population file needs more, it becomes a script's `--help` instead.
- The orphans script's upstream check tests object presence, not
  reachability. Step 2 fixes it, and until then the reference must say so.
- Two scripts and one shell script share a regenerable list by convention
  only until `regenerable.txt` exists.
