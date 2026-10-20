---
name: drafters
description: Who writes the first draft of a message, and how to swap the drafter. Read before you draft.
---

# Drafters

A drafter writes the first draft of a message. Everything after the draft
is the same for every drafter: the lint in
[message-style.md](message-style.md), the prediction in
[github.md](github.md), the approval batch, and the ledger. Only the first
draft changes.

The contract: the input is one PR (its title, its description, its diff,
and its changed files). The output is one message file in the form
`<title>\n\n<description>`. The ledger `drafted` event names the drafter.

## `claude` (default)

The session model writes the draft from the PR and from
[message-style.md](message-style.md). Read the diff when the description is
thin or when the code snippet needs a line from it.

## `wt` (later)

worktrunk can generate a message without a commit:
`wt step squash --dry-run` prints the prompt, the command, and the message.
A house template goes in through the setting
`commit.generation.squash-template`. Use `wt` only when the operator names
it. Parse the message out of the dry-run output, then lint it like any
other draft. Its ledger name is `wt`.

`wt` cannot squash with an approved message, and `wt merge` merges into a
local trunk, not on GitHub. So `wt` is a drafter only.
