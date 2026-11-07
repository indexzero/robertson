---
name: stack
description: Prepare an explicitly requested stack, PR set, or topic with one approval per scope.
---

# prepare a stack or set

Use this path only for `prepare --stack PR`, a named stack, multiple PRs,
or an explicit topic. An ordinary PR selector uses [prepare.md](prepare.md).

## Resolve the requested set

Read [github.md](../references/github.md). Use a named stack's metadata
and confirm its base/head edges. Before linking, verify that each parent's
current head is an ancestor of its child. Report divergence as a blocker
for linking and merging; it does not authorize restacking. For a topic,
search the named repository's
open PRs, including titles, bodies, branches, labels, and changed paths.
Report included PRs and exclusions with reasons.

Find open child PRs whose base is a selected branch. Report children
outside the requested stack or scope; do not silently add them. Description
preparation does not rewrite a parent's history, so an outside child does
not by itself prevent preparing that parent.

Group related work into scopes. A scope is one purpose in one area. A
dependency chain can form one stack; unrelated PRs sharing a topic need
not become a stack. For several scopes, show the groups and dependency
order before drafting and let the operator correct them. Keep one approval
batch per scope. A deep single PR still uses the ordinary path.

## Prepare each message

Use the helper from [prepare.md](prepare.md) to inspect each qualified
target. Work from root to leaf. Draft each message from its own diff, lint
it, and create its proposal. Do not reuse the root's changes as a child's
description. Closed or merged PRs leave the set. Drafts and conflicts can
have descriptions prepared but must be reported as blocked for merging.

Show the subjects, then the complete messages and predicted differences.
Ask for one approval per scope. After approval, record each proposal's
approval and apply it through the helper. Unchanged approved proposals
can resume without a repeated approval.

## Link only the requested stack

For a requested stack whose base edges form a chain, confirm the planned
links in the approval batch. After message application, recheck the PR
heads and bases, then link from root to leaf:

```sh
gh stack link ROOT ... LEAF
```

Use the named repository's context. If the installed `gh stack` command
cannot select a remote repository directly, use a checkout of that
repository. Do not run a stack command in an unrelated checkout. If the
extension or command is unavailable, report that limitation without
installing tooling or guessing the operation.

Record the `linked` event. Do not link disconnected PRs merely because
they have the same topic. Repository settings and linking failures do
not erase the messages already prepared; report partial progress.

## Report

Reinspect current heads and status. Report prepared PRs, remaining merge
blockers, predicted platform changes, and exclusions. Give merge commands
in dependency order for stacks that are ready. Do not run them. A stack
with unknown or failing checks is not ready merely because its messages
were applied.

Reconcile historical runs only when requested; see
[ledger.md](../references/ledger.md). Repository-wide reconciliation is
not a prerequisite for preparing the selected set.
