---
name: kabpr
description: >-
  Prepare an existing GitHub PR's title and description as an approved
  squash commit message. Resolve a PR number, owner/repo#number, URL, or
  the current branch. Use for PR message preparation and explicit stack,
  seal, or squash requests. Opening PRs and reviewing code are separate tasks.
metadata:
  version: "0.2.0"
---

# kabpr

`/kabpr prepare [PR]` prepares one PR's title and description, gets one
approval, applies the text, and reports merge status. `prepare` is the
default. `ready` is an alias.

| Request | Target |
|---|---|
| `/kabpr prepare owner/repo#34` | That PR, from any directory |
| `/kabpr prepare #34` | PR 34 in the current repository |
| `/kabpr prepare 34` | Same |
| `/kabpr prepare` | The open PR for the current branch |
| `/kabpr prepare https://github.com/owner/repo/pull/34` | That PR |

Resolve exactly the requested PR. An absent or ambiguous match needs a
specific explanation. A fully qualified target needs no checkout.

## Commands

| Command | Read | Result |
|---|---|---|
| `prepare`, `ready`, or no verb | [commands/prepare.md](commands/prepare.md) | Approved title and body, verified on GitHub, with merge status |
| `prepare --stack PR`, a named stack, or an explicit set/topic | [commands/stack.md](commands/stack.md) | One approval per scope, messages and stack links |
| `seal` | [commands/seal.md](commands/seal.md) | One commit per PR branch, pushed with exact leases, PRs left open |
| `squash` | [commands/squash.md](commands/squash.md) | One PR merged with the approved message |

An exact PR selector never expands into its stack by itself. The ordinary
path does not scan unrelated PRs or reconcile the repository's old runs.

## Shared rules

- Read [references/message-style.md](references/message-style.md) before
  drafting. Preserve issue-closing references and verify claims and the
  snippet against the selected head. The session agent is the drafter.
- Show the complete title and body before asking to apply them. Approval
  covers the displayed text and target. Reuse an unchanged approved
  proposal after an interruption. A revised proposal needs approval.
- A draft, failing check, conflict, or unsuitable squash default can block
  merging while the description is still prepared. Closed and merged PRs
  are reported without edits. Keep "prepared" and "ready to merge" distinct.
- `prepare` edits only title and body. Branch rewrites require `seal`;
  merging requires an explicit `squash` request. Repository settings and
  source-conflict repairs remain separate tasks.
- Before a write, recheck the pinned head, base, and current message.
  Read back what was written. Preserve backups and approval records.
- For history rewrites, capture full object IDs from Git, create backup
  refs, and use an explicit refspec with a lease on the original remote
  head. A failed lease stops the operation.
- A mixed-scope change can be recorded as a signal. Do not turn message
  preparation into a request to split the PR.

The Python helper in [scripts/prepare.py](scripts/prepare.py) handles
resolution, snapshots, structural lint, proposals, approval records,
application, and readback. It requires Python 3.10+ and authenticated `gh`.
The agent still judges meaning and verifies source examples.

Read [references/github.md](references/github.md) for squash prediction
or stacks, [references/ledger.md](references/ledger.md) for state and
history, and [references/drafters.md](references/drafters.md) only when
choosing a different drafter.
