---
name: modernize.js
description: >-
  Bring a legacy Node.js package back to life: CommonJS to ESM, vows/mocha/tap
  to node:test, Travis to GitHub Actions, a current engines floor, an exports
  map, verified types, a migration guide, and a release, without losing what
  the old package promised its callers. Use it whenever the user wants to
  modernize, revive, resurrect, overhaul, or "bring up to date" an old npm
  package or Node.js repo, mentions a package they wrote years ago, asks to
  drop CommonJS, replace a dead test framework or a deprecated dependency
  (request, async, util._extend, url.parse, new Buffer), cut a long-delayed
  1.0 or a new major, or asks what it would take to revive an old package.
  Also use it to audit a modernization that is already done, especially when
  the user asks whether a green typecheck, lint, or test run can be trusted.
  Do not use it for new packages, for application code with no published API,
  or for a routine dependency bump.
argument-hint: "[path-to-package] [plan|audit]"
metadata:
  version: "0.1.0"
---

# modernize.js: bring an old Node.js package back

An old package is not legacy code to be replaced. It is a set of promises to
callers who stopped paying attention years ago, written in the only dialect
the platform had. The work is to restate those promises in today's dialect,
break the few that deserve it on purpose and in writing, and leave gates
behind so the result does not rot the way the original did.

Two things go wrong when this is done carelessly. The rewrite quietly changes
behaviour nobody decided to change, because the old tests were deleted before
anything pinned what they covered. And the new tooling reports green while
checking nothing, because a config that looks right is easy to write and
nobody asked it to fail. Most of this skill exists to prevent those two.

The first argument is the package path (default: the current directory).
`plan` stops after Step 2 and changes nothing. `audit` skips to Step 7 on a
modernization that already exists.

## Choose the size of the revival

Decide this before touching a file, and say which one you chose and why. The
smallest revival that meets the goal is the right one: every line you rewrite
is a line whose old behaviour you now have to prove you kept.

| Size | When | What it looks like |
|---|---|---|
| One feature | The package still works. The world moved in one specific way. | A shell script dormant for eleven years gains a `--path` flag because monorepos exist now. Two commits, no rewrite, no new tooling. |
| Dependency swap | One dependency is dead, blocked, or deprecated. The API is fine. | An HTTP client is replaced with a fetch-compatible one. The helpers it provided (pagination, retry, throwing on non-2xx) are reimplemented, because the replacement does not have them. |
| Tune in place | The package is depended on heavily and must stay wire-compatible. | Deprecated internals replaced and hot paths tightened behind a frozen baseline. No API change, no module-system change. |
| Full modernization | The dialect itself is the problem: CommonJS, a dead test runner, dead CI, an engines floor from another era. | A new major. Everything below. |

A package with many dependents and a working API usually wants "tune in
place", however dated the source looks. A package that is mostly yours and
whose reason to exist has been changed by the language wants the full path.

The owner asked for a revival, so the answer is a revival. That an official
or more popular package now exists, or that downloads are low, changes what
the revived package should be (smaller, zero-dependency, a different niche).
It is not a reason to recommend deprecating it. Say in one line what else
exists and how this package will differ, then get on with the work.

## Step 0: Survey

Run the survey. It reads the repository and answers the mechanical questions
in about a second, so you spend your attention on the judgement calls.

```bash
node <skill-dir>/scripts/survey.mjs <package-dir>
```

It reports the module system, legacy idioms by count and file, the test
runner, CI providers, engines, lockfiles, dependencies, the git timeline, and
whether the typecheck configuration can see the JavaScript at all. It decides
nothing.

Then find out what the survey cannot: who depends on this. Check the registry
for dependents and weekly downloads, and search for the most common import
shapes. Callers who deep-import `pkg/lib/thing.js` are part of the API whether
or not anyone meant them to be.

## Step 1: Pin the old behaviour

Do this before any modernizing edit. Once the source has changed, the only
record of what it used to do is your memory of it.

1. **Get the old tests running as they are.** Install the old runner and run
   it on a current Node. Record what fails on the untouched tree. Those
   failures are pre-existing, and you will need to tell them apart from the
   ones you cause.
2. **If there are no tests, or they need credentials or a service that no
   longer exists, write characterization tests** against the published
   version. Cover the documented examples first. The README is the contract
   most callers read.
3. **For anything on a wire or a hot path, freeze a baseline.** Snapshot the
   untouched build and assert the candidate is byte-identical to it, or no
   worse than it, on a fixed corpus. Differential gates survive a change of
   machine. Hand-written expected bytes rot.

The old suite is deleted last, not first. Port it to the new runner, run both
against the new code until the new suite covers everything the old one did,
then delete the old one in its own commit. That commit names every behaviour
the old tests checked that you dropped on purpose.

## Step 2: Write the breaking changes down before making them

List every break as a row: what it was, what it becomes, and why it is worth
breaking. This list becomes the migration guide, so it costs nothing extra,
and writing it first stops a break from happening by accident.

Typical rows: the engines floor, the module system, removed global patches,
removed dependencies on dead packages, renamed or relocated entry points.

Prefer a break that fails loudly to one that fails quietly. A removed export
throws at import. A function that silently changed its return shape does not.
When a quiet failure is unavoidable, the migration guide says exactly what to
grep for.

With `plan`, stop here and present the size, the baseline, and this list.

## Step 3: Move the platform

Read [references/idioms.md](references/idioms.md) for the old-to-new table
and the `package.json` shape. The principles behind it:

- **ESM only, no dual build.** Current Node can `require()` a synchronous ESM
  graph, so ESM-only no longer strands CommonJS callers, provided the entry
  graph has no top-level `await`. Confirm this against the Node documentation
  for the floor you chose. A dual build doubles the surface for one release
  line's benefit.
- **Set the engines floor from the release schedule, not from memory.** Look
  up which lines are in maintenance today. Choose the oldest line that will
  still be supported for the life of this major. The CI matrix is exactly the
  lines `engines` admits: a floor you do not test is a guess.
- **State the floor once.** It appears in `engines`, the CI matrix, the
  README, and the migration guide, and those drift apart within a single
  sitting.
- **Delete what the language absorbed.** A `mixin` helper, a
  `Error.prototype.toJSON` polyfill, a hand-rolled cause chain: the reason
  they existed is gone. Patches to built-in prototypes go first. They were a
  convenience in 2011 and are a hazard now, and removing one is always a row
  in Step 2 with an explicit function as the replacement.
- **Do not assume one engine.** Code that splices line 1 off a stack trace
  assumes V8's format and removes the wrong frame elsewhere. Guard
  engine-specific APIs by checking for them, and prefer the portable
  primitive (`queueMicrotask` over `process.nextTick`) where behaviour allows.
- **An `exports` map closes the package.** Every deep import that worked
  before stops working. Add a subpath for each one callers used, plus
  `./package.json`.

## Step 4: Replace the tooling

- **Tests** move to `node:test` and `node:assert/strict`. No dependency, no
  runner to go unmaintained again. Convert `done` callbacks to promises:
  it is the form every runtime supports.
- **Examples are tests.** Every file in `examples/` runs in the suite and its
  output is checked for one line that proves it did its job. An example that
  only "exits 0" passes when it prints nothing.
- **Lint and format** with one tool and one config. Follow what the owner's
  newer repositories use before choosing for them.
- **CI** runs the engines matrix, and it runs the *same* aggregate script the
  publish gate runs. If `prepublishOnly` runs `check` and CI runs only `lint`,
  the type gates run once per release, on one machine, after the code merged.
- **Look up current action and tool majors.** Do not write them from memory.
  Copy from the owner's most recently updated repository or the tool's
  releases page.

## Step 5: Types that are actually checked

Read [references/type-gates.md](references/type-gates.md) before writing a
`tsconfig`. The short version:

Default to JSDoc in the source with declarations **generated** from it at
publish time. One source of truth cannot disagree with itself.

Hand-write a `.d.ts` only when it must say something JSDoc cannot. The moment
a `.d.ts` sits beside its `.js`, TypeScript drops the `.js` from the program.
`checkJs` stays in the config and checks nothing. This has shipped in a 1.0.0
with every gate green, including a declared export that threw `SyntaxError`
at import. The reference explains the three gates that close it and the
drift that even those miss.

## Step 6: Add API only where the language caught up

A modernization is a tempting moment to redesign. Resist everything except
the cases where a language feature changes what the package is *for*, as
`AggregateError` and `Error.cause` do for an error library.

- **Additive first.** Old call shapes keep working. A JavaScript array can
  carry named properties, so one return value can be read the new way and the
  old way.
- **Rename with aliases** and a table: old name, new name, the major that
  removes it.
- **Warn once** for a call shape that still works but cannot honour new
  options.
- **Ask who owns the work.** A function handed started promises cannot limit
  or cancel them. One handed thunks can. The useful design change is usually
  about ownership, not about the return shape.

## Step 7: Review it as someone who distrusts you

The author of the code also wrote the commit messages, the README, and the
comments, so they agree with each other and prove nothing. Before calling the
work done, get two independent reads: one from a fresh context, and one from
a different model if one is available. Tell both not to trust the prose, to
read the configs instead of the exit codes, and to try to break things.

Then verify the verification. For every gate you added, reintroduce the
defect it guards and watch it fail. A gate you have never seen fail is a
hope. Three questions catch most fake gates:

- Does the checker load the files you think? (`tsc --listFiles`, the test
  runner's file list, the linter's file count.)
- Does the script named `build:*` or `check:*` do what its name claims?
- Does CI run it?

Expect the findings in the parts that felt finished. In the reference
modernization the concurrency primitive survived everything thrown at it. The
bugs were a cycle guard that tracked visited values instead of ancestors, an
accumulator on `{}` that died on an error named `constructor`, and a
`.gitignore` appended to without a trailing newline.

Fix every finding with a test, in commits separate from the features.

## Step 8: Documents that can be checked

Read [references/docs-and-release.md](references/docs-and-release.md).

- **Migration guide:** one section per row from Step 2, with before and after
  code, and what to grep for.
- **Changelog:** reconstructed from the tags back to the first release, so
  the history survives the rewrite.
- **A docs test.** Copy [assets/docs.test.js](assets/docs.test.js) into the
  suite and adjust its globs. It checks that every repository path and every
  package script the documents mention exists, that no import list repeats a
  name, and that no prose states a count of tests or errors.

Keep counts and other computed state out of prose altogether. A number
nothing recomputes is wrong one commit later. The command that prints it is
the place it belongs. A PR body lives outside the repository where no test
reaches it, so the same rule is kept there by hand.

Narrow gates outlive broad ones. Parsing every fenced block as a module
sounds thorough and fails on correct documentation, such as a fragment with
a bare `return`. A gate that fires on correct input gets switched off.

## Step 9: Release

The release is the owner's to make. Prepare it and stop: the version commit,
the tag command, and the publish path. Publish from CI with trusted
publishing rather than a token on a laptop, and remember that provenance
says where a package was built, not that its source was reviewed.

`prepublishOnly` runs the full check and the tests. If a script in that chain
emits nothing, it is not a gate. Remove it and say so in the changelog.

## Commit shape

One concern per commit, so each can be reviewed and reverted alone. The order
that has worked:

1. The platform move and the ported tests together, since neither runs
   without the other.
2. Examples.
3. CI.
4. Lint and format, as a mechanical commit with no behaviour in it.
5. Deleting the legacy tests, naming what was dropped on purpose.
6. Directory moves, as pure renames.
7. Changelog and migration guide.
8. Review fixes, each with its test.
9. The version.

Follow the repository's existing commit style and its attribution rules.

## Report

End with what a maintainer needs in order to decide:

- the size chosen and why;
- the breaking changes, as the Step 2 table;
- what the baseline showed, including failures that pre-date your work;
- each gate, and whether you watched it fail;
- anything you could not verify, stated as unverified.
- anything you changed outside the repository, such as runtimes installed
  to test the engines floor.

Do not report a count of passing tests. Report the command that prints it.
