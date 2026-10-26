---
name: kabocha
description: >-
  Finish the last mile of reviewed GitHub PRs: rewrite each PR title and
  description into a house-style squash commit message, get one approval
  per scope, apply the messages to the PRs, link one GitHub stack per scope,
  predict the exact squash commits, and report ready with the merge commands.
  It never merges by default. Use it when the operator says "kabocha the PRs
  related to <topic> on <repo>", asks to get a set of PRs or a stack ready to
  squash-merge, wants PR descriptions turned into commit messages, or names
  `kabocha seal` or `kabocha squash`. It scales from one deep PR to about 50
  PRs across several scopes. Do not use it to open PRs, review code, resolve
  conflicts, or squash local commits that have no PR.
argument-hint: "[ready|seal|squash] <topic or PR numbers> [on <owner/repo>]"
metadata:
  version: "0.1.0"
---

# kabocha: squash the last mile

kabocha takes PRs that are reviewed and makes them ready to land as one
commit each. The PR description becomes the commit body. The operator
merges. kabocha records each verdict so that a later version can earn the
right to merge.

A typical request: "kabocha the PRs related to the cache backport on
example/widgets". kabocha finds the PRs, measures the scale, and runs the
`ready` command.

## Choose the command

The first word of the request selects the command. Without a command word,
the command is `ready`.

| Word | Read | Ends with |
|---|---|---|
| `ready` (default) | [commands/ready.md](commands/ready.md) | approved messages on the PRs, one linked stack per scope, a ready report with the merge commands. No merge. |
| `seal` | [commands/seal.md](commands/seal.md) | one commit per PR on each branch, pushed with a lease. Every PR stays open. |
| `squash` | [commands/squash.md](commands/squash.md) | one PR squash-merged with an approved custom message. |

`seal` and `squash` rewrite history or merge code. Run them only when the
operator names them in the request. When `ready` finds a defect that only
`seal` can correct, it reports the defect and names `seal`. It does not run
`seal`.

## Measure the scale

The operator does not choose a tier. kabocha computes it from the resolved
PR set, then states the result in one line before it drafts anything:
"Found 7 open PRs in one stack, one scope. One approval batch."

A scope is a set of PRs that change one area for one purpose. A linked
stack is one scope. Unlinked PRs share a scope when their titles, branches,
and changed paths name the same area.

| Tier | Shape | What changes |
|---|---|---|
| 1 | one PR | One message. A deep PR can use up to six sentences. The code snippet budget stays at 10 lines. |
| 5 | one scope, about 2 to 10 PRs | One approval batch. One stack, linked from root to leaf. Find hidden children: open PRs whose base is a branch in the set. |
| 50 | several scopes | Plan first, then stop for the operator: scopes, stacks, the order of the stacks, and the cross-stack risks. Then one approval batch and one stack for each scope. Merge commands come in dependency order. |

At tier 50, the plan is the first output. Draft nothing until the operator
accepts the plan. A batch of 50 messages is not a review.

## Invariants

These hold at every tier and in every command.

1. The operator approves bytes, not intent. Show the complete message. Hash
   the exact bytes. Write the `approved` ledger event before any write to a
   PR or a ref. An edit makes a new message that needs a new approval.
2. kabocha never merges in `ready` or `seal`. The operator runs the merge
   command. `squash` merges one PR, and only when the operator names it.
3. Every message follows [references/message-style.md](references/message-style.md):
   the subject `Update <exact path of the most salient file> to <behavior>`,
   then the problem from the PR's "Why", then the three to ten source lines
   (or the real user-facing invocation) that carry the change, then one
   value line (`That <noun> enables|allows|unblocks <outcome>`), then the
   closing keyword, then the attribution block. A test or lint command is
   never the code.
4. Before the ready report, predict the squash commit that GitHub will make
   from each PR. Compare it to the approved bytes. Correct what the
   description controls. Report the rest. See
   [references/github.md](references/github.md).
5. Verify the repository settings before the first write. Never assume them.
6. A PR that is `CONFLICTING`, a draft, or not open stops its batch.
   kabocha does not repair source conflicts.
7. Push only with an exact lease on the old remote head and an explicit
   refspec. Never use a bare `--force`.
8. The ledger records every draft, approval, edit, prediction, and verdict
   before the next action. See [references/ledger.md](references/ledger.md).
9. Log a mixed-scope signal when a subject needs "and" to join two claims or
   a diff changes two unrelated areas. Do not tell the operator to split the
   PR. The ledger keeps the signal for evals.

## Start every run with reconcile

Read the ledger for this repository before you resolve PRs. For each PR
that kabocha applied a message to and that has no `observed` event,
compare GitHub's record with the ledger and append an `observed` event.
[references/ledger.md](references/ledger.md) defines the classes. Report
the counts in one line. This step takes no approval, because it writes only
to the ledger.

## References

Read each file when its condition is true.

| File | Read when |
|---|---|
| [references/message-style.md](references/message-style.md) | Every command, before you draft or check a message. |
| [references/of-structure/the-elements-of-documentation.md](references/of-structure/the-elements-of-documentation.md) | message-style.md cites a rule by number. Fetched by [.vlurpfile](.vlurpfile). Do not edit it. |
| [references/ledger.md](references/ledger.md) | Every command, before the first ledger write, and at reconcile. |
| [references/github.md](references/github.md) | Before you check settings, link a stack, predict a commit, or read PR edit history. |
| [references/drafters.md](references/drafters.md) | Before you draft. It names who writes the first draft. |

## Must not happen

- A merge in `ready` or `seal`, or a `squash` the operator did not name.
- A write to a PR, a branch, or a ref before its `approved` ledger event.
- A ready report for a PR whose predicted commit differs from the approved
  bytes, with no line that says how.
- One approval that covers more than one scope.
- A message that claims what the diff does not contain.
- A recommendation to split a PR.
- A copy of the Elements text in this skill. Cite the rule number.
