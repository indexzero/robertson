---
name: ledger
description: Agent-neutral proposal storage, approval records, and optional history reconciliation.
---

# State and ledger

The helper stores state in `KABPR_STATE_DIR`, or in
`${XDG_STATE_HOME:-~/.local/state}/kabpr`. `--state-dir` overrides both.
Use a scratch directory in tests. State belongs to the user, independent
of whether the session runs in Claude Code, Codex, or another harness.

Each proposal gets a fresh run directory containing:

- `snapshot.json`: selected repository, PR, head, base, source diff, and
  the original title and body.
- `message.msg`: UTF-8, LF, one final newline.
- `proposal.json`: target identity, message and original-message hashes,
  and squash prediction.
- `before.json`: title and body read immediately before an attempted write.

Do not edit saved proposals. Revised text gets a new proposal. Hash the
title, two newlines, and body, omitting one final newline. Approval binds
that hash to the host, repository, PR, full head and base IDs, head
repository, and branch names. Legacy approvals without those fields
cannot authorize a new write automatically.

`ledger.jsonl` is append-only. Each helper event contains `event`, `at`,
`run`, the identity fields, and `message_sha256`:

| Event | Meaning |
|---|---|
| `drafted` | Immutable proposal saved |
| `approved` | User approved the displayed proposal |
| `applying` | Backup saved and write is about to be attempted |
| `applied` | Readback matched, or a resumed run found the approved text already present |
| `verify_failed` | Post-write target or content changed; inspect before further action |

The helper looks only for proposals matching the selected PR and context.
An approved message already on that PR is prepared. If the original text
is still present, resume from the saved approval. A different title, body,
head, or base requires inspection again. A lost write response can be
recovered without writing twice. The next inspection refreshes merge
status; an old green check is not a current verdict.

## Other operations and older records

For stack, seal, and squash, retain the event names `resolved`, `signal`,
`linked`, `predicted`, `ready`, `sealed`, and `merged`. Add the relevant
scope, ordered PRs, stack number, prediction differences, old/new heads,
tree, or merge SHA. Record approvals and pinned context before writes.
Source-history rewrites need approval for the rewrite as well as the text.

The old ledger remains at `~/.claude/kabocha/ledger.jsonl`; earlier
`ste-seal` and `ste-squash` ledgers remain where they are. Read them when
answering historical questions or explicitly reconciling past runs. Do
not relocate them, rewrite their events, or infer new permissions from
them. `KABOCHA_LEDGER` belongs to the legacy implementation; new runs use
`KABPR_STATE_DIR`.

## Optional reconciliation

When requested, compare relevant prior `applied` events with GitHub's PR
edit history and actual merge commit, using [github.md](github.md).
Classify the observation as `merged-as-approved`,
`merged-platform-changed`, `merged-operator-edited`, `merged-unpredicted`,
`merged-without-ready`, `closed-unmerged`, or `open-stale` after 14 days.
An open, recent PR needs no observation yet. Append an `observed` event
with the evidence and differing lines, then report the counts. Account
login alone cannot distinguish the agent's edits from the user's edits.
