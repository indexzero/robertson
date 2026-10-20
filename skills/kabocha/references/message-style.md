---
name: message-style
description: The house form of a kabocha commit message. Every command reads it before it drafts or checks a message.
---

# Message style

A kabocha message is a PR title plus a PR description. GitHub turns them
into the squash commit, so the description is written as a commit body,
not as a PR essay. The long PR description stays in GitHub's edit history.

The reasons come from *The Elements of Documentation*, fetched by the
[.vlurpfile](../.vlurpfile) to
[of-structure/the-elements-of-documentation.md](of-structure/the-elements-of-documentation.md).
This file cites its rules by number. Read a rule in the book when you need
its reason or its example.

## The form

The PR title is the subject. The PR description is everything below it:

````text
Update exact/path/to/most/salient/change.ext to behave in this way

```
SPECIFIC_USAGE_IS=true exact/path/to/most/salient/change.ext
exact/path/to/most/salient/change.ext SPECIFIC=VALUE
```

That behavior enables a pragmatic outcome that has obvious value.

Closes #N

<!-- metadata.txt

Assisted-by: <model display name>, claude-code@<version>
````

Say what it does, then why that is valuable. Do not dwell on failures or
history.

## Subject

- One imperative sentence: `Update`, the exact repository path of the
  single most salient file, then `to` and the behavior that file now has
  (Rules 1 to 4). Name the behavior, not the mechanism.
- The most salient file is the one whose new behavior is the point of the
  PR. It is usually not a test, a fixture, a lockfile, or a doc.
- No final period, no parenthetical, no PR number. GitHub appends `(#N)`.
- 72 columns or fewer. When the path is long, choose a shorter, exact verb
  phrase.
- A subject that needs "and" for two claims is a mixed-scope signal. Write
  the subject anyway and log the signal (SKILL.md invariant 9).

## Usage block

- One to three lines that exercise the change: a command, an environment
  variable with the command, or a route the app serves (Rule 12).
- Put the lines in a fenced code block that opens the description. Indent
  nothing. GitHub strips the leading whitespace of the description's first
  line in the squash commit, so an indented first line loses its indent.
- Verify each line against the repository at the PR head: a package.json
  script, a bin, a CLI command and its flags, or a route. Never invent a
  flag. Prefer a line you ran.

## Value line

- One declarative sentence after the usage block.
- Its subject is a demonstrative plus a noun that points back to the
  subject line: "That behavior", "That rule", "That event".
- Its verb is exactly one of `enables`, `allows`, or `unblocks`. Its object
  is the outcome.
- Wrap it at 72 columns.

## References

- Rule 9: keep the PR's closing keyword, `Closes #N` or `Fixes #N`, as its
  own line after the value line. A rewritten description that drops it
  leaves the issue open at merge. Copy it from the PR body, or from
  `gh pr view N --json closingIssuesReferences`. Verify the number.
- No verification logs, review rounds, dispatch ids, run names, or
  planning section numbers. They belong in the PR history.

## Attribution block

The description ends with the attribution block that the operator's
instructions require. The default:

```text
<!-- metadata.txt

Assisted-by: <model display name>, claude-code@<version>
```

- `<model display name>` is the model in this session. `<version>` is the
  output of `claude --version`. Check both for each run.
- Leave the comment open. A closing `-->` makes git miss the trailer.
- The block is the last paragraph. GitHub can append a paragraph after it.
  [github.md](github.md) says when, and how to predict it.

## Lint before approval

Check each draft before you show it:

1. The subject starts with `Update `, names a path, contains ` to `, and
   is 72 columns or fewer.
2. The description opens with a fenced usage block, and no line in the
   description starts with whitespace.
3. Every line is 72 columns or fewer.
4. The value line uses `enables`, `allows`, or `unblocks`.
5. The PR's closing keyword is present.
6. `git interpret-trailers --parse` finds the attribution trailer in
   `<subject> (#N)` + blank line + description.
