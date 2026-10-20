---
name: ledger
description: The kabocha ledger. Its events, its fields, and the reconcile classes that turn the operator's merges into evidence. Read before the first ledger write and at reconcile.
---

# Ledger

The ledger is the memory of kabocha. It records what kabocha drafted,
what the operator approved, what kabocha wrote to GitHub, and what happened
next. Over time it shows how often kabocha's "ready" matched the operator's
merge. That record is the evidence for a future version that merges.

## Location

- Default: `~/.claude/kabocha/ledger.jsonl`, one JSON object on each line,
  append-only.
- `KABOCHA_LEDGER` overrides the path. Evals set it to a scratch file, so
  they never write to the real ledger.
- Message files go next to the ledger as `<owner>-<repo>-<pr>.msg`: UTF-8,
  LF line ends, one final newline. Hash these exact bytes.
- Write under `~/.claude/` with the file tools, not shell redirects. A
  sandboxed shell cannot create files there.
- The ledgers of the earlier skills, `~/.claude/ste-squash/approvals.jsonl`
  and `~/.claude/ste-seal/ledger.jsonl`, stay where they are. They are
  approval records. Read them only to answer a question about an old PR.

## Events

Every event has `event`, `repo`, `at` (ISO 8601 UTC), and `run` (one id for
each kabocha run). Add the fields below.

| event | when | fields |
|---|---|---|
| `resolved` | the PR set is known | `topic`, `prs`, `tier`, `scopes` (each with its PRs) |
| `drafted` | a draft exists | `pr`, `drafter`, `message_sha256` |
| `signal` | a check found something to trace | `pr`, `kind` (`mixed-scope`, `long-line`, `coauthor-append`, ...), `detail` |
| `approved` | the operator approved a batch | `scope`, `prs`, `message_sha256` for each PR |
| `applied` | kabocha wrote a title and description | `pr`, `message_sha256`, `body_sha256`, `applied_at` |
| `linked` | a stack was linked | `scope`, `stack`, `prs` in order |
| `predicted` | the commit prediction is done | `pr`, `predicted_sha256`, `differences` |
| `ready` | the ready report names the PR | `pr`, `stack`, `merge_command` |
| `sealed` | `seal` pushed a branch | `pr`, `old_head`, `new_head`, `tree`, `message_sha256` |
| `merged` | `squash` merged a PR | `pr`, `merge_sha`, `message_sha256`, `matches_approval` |
| `observed` | reconcile read GitHub's record | `pr`, `class`, `merged_at`, `merge_sha`, `minutes_ready_to_merge`, `detail` |

`message_sha256` covers `<title>\n\n<description>`. `body_sha256` covers
the description alone. Strip one final newline before each hash, because
GitHub stores the description without it.

## Reconcile classes

At the start of each run, reconcile every `applied` PR in the repository
that has no `observed` event. Read the PR with the GraphQL query in
[github.md](github.md). Then choose the first class that matches:

| class | condition |
|---|---|
| `merged-as-approved` | merged, and the squash commit equals the `predicted` message |
| `merged-platform-changed` | merged, and the commit differs from the approved bytes only in the ways the prediction listed |
| `merged-operator-edited` | merged, and the description changed after `applied_at` with a body hash that kabocha never wrote |
| `merged-unpredicted` | merged, and the commit differs in a way that no prediction listed |
| `merged-without-ready` | merged, and the ledger has no `ready` event for it |
| `closed-unmerged` | closed, not merged |
| `open-stale` | still open 14 days after `ready` |
| `open` | still open and not stale: record nothing yet |

`merged-unpredicted` is the class that teaches kabocha the most. Copy the
differing lines into `detail`.

Report one line at the start of the run, for example:
"Reconciled 7 PRs: 7 merged-platform-changed (coauthor-append)."
