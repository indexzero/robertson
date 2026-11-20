# pr-sizes

**Count what a stack of pull requests adds: docs, code and tests, apart.**

`scripts/pr-sizes.py` measures each PR of a stack against the one below
it, and the whole stack as one diff from its base. It splits every changed
file into docs, code, tests, or generated and data, and writes a Markdown
report. It reads git objects only. It never checks out, commits or fetches.

It needs Python 3.10+ and git, and `gh` when items are PR numbers.

## Run it

From the root of this repository:

~~~sh
python3 tools/pr-sizes/scripts/pr-sizes.py \
  --repo ~/Git/OWNER/REPO \
  --base BASE \
  --config tools/pr-sizes/examples/js-library.json \
  --date 2026-11-18 --out /tmp/pr-sizes.md --json /tmp/pr-sizes.json \
  12 13 14
~~~

Arguments:

- `ITEM ...`: the stack, bottom first. A bare number (`12` or `#12`) is a
  PR, resolved with `gh pr view` from inside `--repo`. Anything else is a
  git ref; `ref:NAME` forces a ref when a name is all digits.
- `--base REF`: the commit the first item is measured against.
- `--config FILE`: the file-to-group mapping. Without it, a generic default
  applies. That default is a guess; write a config for each repository.
- `--gh-repo OWNER/REPO`: for `gh` when the clone's remote is another repo.
- `--out FILE`, `--json FILE`: the report, and every count as JSON.
- `--date`: the date in the report's first line (default: today).
- `--strict`: exit 2 when any check below is flagged.
- `--run-tests COMMAND`, `--worktree ITEM=PATH`: the optional test run, off
  by default. See below.

Every commit must be present locally. Fetch first; the tool does not.

## Checks it runs first

The report opens with these, each stated per item:

- the number of commits from the item below to this one, and whether it is one;
- whether the single commit's parent is the item below;
- whether the item below is an ancestor at all (if not, the diff includes
  changes from outside the stack);
- for a PR: its commit count on GitHub, its base branch against the head
  branch of the PR below, and its base branch's commit against the item below;
- files created, deleted or renamed (`git diff --name-status -M`);
- files in no group, binary files, and added lines that start like a block
  comment (`/*`, `*`, `*/`), which count as substantive.

Flags are reported, not fixed. The counts still measure what is there.

## Groups

A config is JSON. `rules` is an ordered list; a file takes the group of the
first rule with a matching pattern. The groups are `docs`, `code`, `tests`
and `generated`. A file that matches no rule is `unassigned` and is listed.

~~~json
{
  "rules": [
    { "group": "docs", "patterns": ["README.md", "doc/**"] },
    { "group": "generated", "patterns": ["spec/**", "test/vectors.json", "package.json"] },
    { "group": "code", "patterns": ["index.js", "lib/**", "schema/**"] },
    { "group": "tests", "patterns": ["test/*.js", "test/helpers/*.js"] }
  ],
  "comment_prefixes": [{ "patterns": ["**/*.js"], "prefixes": ["//"] }],
  "test_call_regex": "(^|[^.A-Za-z_])test(\\.solo|\\.skip|\\.todo)?\\(",
  "test_count_regex": "# tests = (\\d+)"
}
~~~

Patterns match the whole path from the repository root. `*` and `?` stay
within one name, `**` crosses directories, and `**/` is zero or more
directories. `README.md` is the root file only; `**/README.md` is any.

Order matters where groups overlap: in `examples/js-library.json`,
`test/vectors.json` is generated data and is listed before `test/*.js`.

Other keys:

- `comment_prefixes`: per file pattern, the prefixes of a comment-only line.
- `block_comment_prefixes`: what the block-comment check looks for.
- `test_call_regex`: a line that declares a test.
- `test_files`: patterns of files to search for test calls (default: the
  `tests` rule's patterns).
- `test_count_regex`: the test count in the output of `--run-tests`.

`examples/js-library.json` is one repository's mapping, as a worked example.

## What it counts

For each item, for the sum of the items, and for the stack as one diff:

- **Raw added, removed, net** per group: `git diff --numstat --no-renames`.
  Every line counts, blank lines and comments included.
- **Substantive added** per group. For code and tests: an added line that,
  trimmed, is not empty and does not start with a comment prefix. A line of
  code with a trailing comment counts. For docs and generated: non-blank.
- **Files changed** per group.
- **Test calls added and removed**: added and removed lines in test files
  that match `test_call_regex`.
- **Tests at each commit**: lines matching `test_call_regex` in every test
  file of the tree, at the base and at each item. This reads the tree; it
  runs nothing.
- **Doc words added and removed**: whitespace-separated words on the `+` and
  `-` lines of `git diff --word-diff=porcelain` over the docs.
- **Moved lines** in code and tests: lines `git diff --color-moved=blocks`
  marks as moved, per file, added side and removed side.
- **Ratio of tests to code** for the stack: raw added, substantive added, net.
- **Largest added files** in the stack, with each one's share of its group.

The headline is lines added in docs, code and tests. Generated and data
files have their own column so they do not inflate the three.

The sum of the items and the stack differ when a later item rewrites lines
an earlier one added. The sum counts those lines once per item. The stack
counts what lands on the base branch.

## The optional test run

`--run-tests COMMAND` runs COMMAND through the shell in a worktree at each
commit, and reads the last match of `test_count_regex` in its output. It
runs the target repository's code, so it is off unless asked for.

It never creates or changes a worktree. It uses `--worktree ITEM=PATH`, or
else any worktree registered with the repository whose HEAD is the commit.
It skips a worktree with local changes, and notes it if the run leaves any.
It does not install dependencies, so the command must work as the worktree
is.

~~~sh
python3 tools/pr-sizes/scripts/pr-sizes.py --repo ~/Git/OWNER/REPO \
  --base BASE --config tools/pr-sizes/examples/js-library.json \
  --run-tests './node_modules/.bin/brittle-node test/*.js' 12 13 14
~~~

## What makes the numbers misleading

- **One paragraph per line.** Docs written without hard wraps hold a
  paragraph in a line. A line of docs then holds far more than a line of
  code, and a one-word edit counts as one line removed and one added. The
  word counts show the size of such edits.
- **Changed constants.** A change to one number repeated in docs, tables and
  tests counts as a removed and an added line wherever it appears.
- **Comments.** Code heavy with comments is far larger raw than substantive.
  Read the two columns together.
- **One large new file.** A single new file can be most of a group. The
  largest-files table gives its share.
- **Moved code.** A moved block counts as removed in one place and added in
  another. The moved-lines table counts what git can match. A block moved
  and edited in the same change is not matched.
- **Renames.** Counts use `--no-renames`, so a renamed file counts as all
  removed and all added. The checks list every rename.
- **Generated files.** Build output and data files can be large. They count
  only where the config puts them; a missing rule puts them in a headline
  group or in unassigned.
- **Test counts.** The test-call pattern counts declarations in the source.
  A test declared in a loop counts once, and a removed declaration is often
  a renamed test. `--run-tests` gives the count the runner reports.

## Tests

~~~sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools/pr-sizes/evals -p 'test_*.py' -v
~~~

They build throwaway git repositories and call no network or `gh`.
