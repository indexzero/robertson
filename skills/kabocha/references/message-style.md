---
name: message-style
description: The house form of a kabocha commit message. Every command reads it before it drafts or checks a message.
---

# Message style

A kabocha message is a PR title plus a PR description. GitHub turns them
into the squash commit, so the description is written as a commit body,
not as a PR essay. The long PR description stays in GitHub's edit history.

The rules come from *The Elements of Documentation*, fetched by the
[.vlurpfile](../.vlurpfile) to
[of-structure/the-elements-of-documentation.md](of-structure/the-elements-of-documentation.md).
This file cites them by number and adds only the house limits. Read a rule
in the book when you need its reason or its example.

## Subject

- Rules 1 to 4: the subject is for a reader who never opens the commit. Use
  the form `area: what changed`, imperative, falsifiable, effect before
  mechanism.
- Lowercase after the colon. No final period. Aim for 50 characters and stay
  under 65.
- The area names the subsystem, not the repository.
- Remove every parenthetical except this PR's own `(#N)`. GitHub appends
  `(#N)` itself when the squash title comes from the PR title, so the PR
  title carries no number.
- A subject that needs "and" for two claims is a mixed-scope signal. Write
  the subject anyway and log the signal (SKILL.md invariant 9).

## Body

- Rule 5: record what evaporates. Rule 6: state the problem before the
  fix. Rule 7: complete sentences, most important first. Rule 8: address
  posterity, not the reviewer.
- Two to six sentences for each paragraph group. A deep PR can use up to six
  sentences of problem and six of fix.
- Sentences under 20 words. One fact for each sentence. Active voice,
  simple tenses. No `should`, `would`, `may`, `might`, or `could`.
- No verification logs, review rounds, dispatch ids, run names, or
  planning section numbers. They belong in the PR history.
- A known gap gets one plain sentence, like a BUGS entry (Rule 14).
- Wrap prose at 72 columns.
- Rule 9: references go last, one for each line: `Closes #N` or `Refs #N`.
  Verify each number with `gh` before you cite it.

## Code snippet

A snippet shows the minimum code that carries the change.

- At most 10 lines, including comment lines and blank lines.
- Indent each line by four spaces. Never use a fence.
- No line longer than 72 columns, indentation included. GitHub rewraps a
  longer line in the squash commit and removes its indentation.
- The first line can be a comment that names the file.
- Copy the code from the PR head. Mark an elision with `...`, and only
  inside a line.
- Put the snippet after the prose and before the references. Omit it when
  no code carries the change, for example a version bump.

## Attribution block

The description ends with the attribution block that the operator's
instructions require. The default:

    <!-- metadata.txt

    Assisted-by: <model display name>, claude-code@<version>

- `<model display name>` is the model in this session. `<version>` is the
  output of `claude --version`. Check both for each run.
- Leave the comment open. A closing `-->` makes git miss the trailer.
- The block is the last paragraph. GitHub can append a paragraph after it.
  [github.md](github.md) says when, and how to predict it.

## Lint before approval

Check each draft before you show it:

1. Every sentence outside the snippet is under 20 words.
2. No banned modal, no semicolon in prose.
3. The snippet has 10 lines or fewer, and no line is over 72 columns.
4. `git interpret-trailers --parse` finds the attribution trailer in
   `<subject> (#N)` + blank line + description.
5. The subject has no parenthetical and no final period.
