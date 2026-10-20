---
name: squash
description: Squash-merge one PR with an approved custom message passed explicitly to gh. Run only when the operator names squash.
---

# squash

`squash` merges one PR with a message that the operator approved, passed
explicitly with `--subject` and `--body-file`. It ignores the repository's
squash defaults. Run it only when the operator names it.

Read [../references/message-style.md](../references/message-style.md) and
[../references/ledger.md](../references/ledger.md) first.

## 1. Gate checks

Stop and report instead of merging when any of these is true:

1. The PR is not open, or it is a draft.
2. The base is not the default branch. A stacked PR needs its parent
   merged first. Name `ready` and `gh stack merge` for a stack.
3. GitHub reports `CONFLICTING`.
4. Required checks on the current head are not green.

## 2. Draft and approve

Draft the message with message-style.md from the PR description and,
when the description is thin, the diff. The subject is explicit, so GitHub
does not append `(#N)`. Add ` (#N)` to the subject when the repository
convention has it.

Predict the commit. It is not yet tested whether GitHub appends the
branch commits' `Co-authored-by` trailers to an explicit body, as it does
to the default body (see [../references/github.md](../references/github.md)).
Assume that it does. When the branch commits carry such trailers, report
the possible append and name `seal` as the sure correction. Record the
outcome in the `merged` event.

Show the complete message in a code block. Wait for an explicit yes. An
edit makes a new message that needs a new approval. Write the `approved`
event with the SHA256 of `<subject>\n\n<body>`, and save the message file.

## 3. Merge and verify

Write the body to a file and merge with exactly the approved bytes:

    gh pr merge N -R OWNER/REPO --squash --match-head-commit <full head sha> \
      --subject "<subject>" --body-file <body file>

Pass the full 40-character head sha. `gh` rejects a short one. Use
`--delete-branch` only when the operator asks or the repository deletes
branches automatically.

Fetch, read the squash commit message (`git log -1 --format=%B <oid>`),
and compare it with the approved bytes and the prediction. Write the
`merged` event with `matches_approval`. On a difference that the
prediction did not list, show both texts. A difference in meaning is an
incident, not a footnote.

Report the one-line `git log` of the merge and the two ledger events.
