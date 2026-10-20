---
name: seal
description: Squash each PR branch to one commit with its approved message and push it with a lease. Every PR stays open. Run only when the operator names seal.
---

# seal

`seal` rewrites PR branches. Each PR ends with one commit relative to its
immediate base, with its complete file tree and the approved message. The
PRs stay open. Run `seal` only when the operator names it.

`seal` corrects what a description cannot: after a seal, the branch
carries only the approved message, so GitHub has no `Co-authored-by`
trailers to append at the squash merge.

Never run `gh pr merge`, `gh stack merge`, or any other merge. Do not
enable auto-merge, close PRs, delete branches, or push the default branch.
A stack request means one commit for each PR, never one commit for the
whole stack.

Read [../references/message-style.md](../references/message-style.md) and
[../references/ledger.md](../references/ledger.md) first.

## 1. Inspect and pin the scope

Read the repository instructions. Resolve the repository, the push
remote, the PR branches, and their worktrees. Fetch the named refs without
changing checkout contents. Do not assume that `origin` is the PR head
repository, especially for forks.

Use `gh pr view` to read the full description, diff, state, draft flag,
base, head, review state, and current-head checks. Read the actual commit
messages. Use stack metadata when it exists, then check its edges against
the PR bases.

Before rewriting, require:

- Each PR is open and ready. It has no active auto-merge or merge-queue
  enrollment.
- GitHub does not report `CONFLICTING`. Sealing does not repair conflicts.
- The review is complete, and current-head CI passes under repository
  policy.
- Each affected worktree is clean, with no rebase, merge, or other Git
  operation active.
- Each local branch equals its pinned remote PR head. Do not discard
  local-only commits.
- No other author or reviewer owns an affected worktree.
- No selected head is the default branch or another shared integration
  branch.

Record this table before changing any ref:

| PR | Head repository and branch | Old head | Immediate base | Old boundary | Original tree |
|---|---|---|---|---|---|

For a PR based on the default branch, use its unique merge-base with the
fetched base as `old_boundary`. For a stacked PR, require the pinned parent
head to be an ancestor of the child, and use that exact old parent head as
the boundary. If it is not an ancestor, resolve the stack divergence as a
separate task first.

Count and inspect only `old_boundary..old_head`. If the range is empty or
contains merge commits, stop before rewriting. Do not flatten a merge.

Find open child PRs by their base branch, including children outside any
stack listing. Rewriting a parent invalidates their ancestry. Include only
authorized descendants. If a child is outside scope, get an explicit scope
extension before rewriting its parent.

## 2. Draft and approve the messages

Draft each message with [message-style.md](../references/message-style.md)
from the PR diff against its pinned boundary. When the PR already has an
approved message in the ledger, reuse it if its bytes still match.

Show the complete plan in one batch for each scope:

- the PRs and branches, ordered from root to leaf
- each old head, old boundary, and original tree
- each complete message, in a code block
- the descendants that need restacking, and the exact leases

Ask for approval of the displayed messages and the history rewrite. One
explicit approval can cover the displayed batch. A code-review approval
does not approve an unseen message. Write the `approved` event, and save
each message file next to the ledger.

Recheck the live heads, PR states, base relationships, and the approval
binding before the first rewrite. If a ref changed, stop and rebuild the
plan.

## 3. Squash and restack locally

Create a backup ref for every old head under `refs/kabocha/<run>/` before
the first rewrite. Do not delete or push them during this operation.

Work from root to leaf, in each branch's existing clean worktree. Never
switch a branch that another worktree has checked out.

For a child whose parent was sealed in this batch, first replay only the
child's commits onto the new parent:

    git -c rebase.updateRefs=false rebase --no-autostash \
      --onto "$new_parent" "$old_parent" "$child_branch"

`old_parent` is the parent head from the plan, never the moved parent ref.

Then squash the PR range onto its boundary. Keep the oldest commit as
`pick` and squash the rest, with a sequence editor that rejects an
unexpected todo list. Replace the message with the approved file:

    git commit --amend --cleanup=verbatim -F "$approved_message_file"

Keep the original first commit's author. Do not bypass hooks or signoff
rules. On a conflict, abort only this rebase, keep the backups, and report
the PR.

Before any push, prove for each PR:

- the new tree equals the original tree
- the single commit has the expected parent
- `git rev-list --count "$boundary..HEAD"` returns `1`
- the PR diff against the new boundary equals the original PR diff
- the message bytes match the approved SHA256 (read the raw commit object)
- the worktree and index are clean

## 4. Push, verify, and leave open

Push one branch at a time, root to leaf, with the exact old remote head in
the lease and an explicit refspec:

    git push --force-with-lease="refs/heads/$branch:$old_head" \
      "$push_remote" "refs/heads/$branch:refs/heads/$branch"

After each push, fetch and verify the remote head, tree, message hash, and
unchanged PR base. Write the `sealed` event. If a lease fails, stop. Do not
retry with a fresh lease.

Wait for required CI on the new heads. Old green checks do not cover new
commit ids. Report each PR, its old and sealed heads, its subject, and its
CI status. State that every PR remains open and unmerged.

## Sources

The pick-first, squash-rest procedure comes from the
[Sigstore contributing guide](https://github.com/sigstore/.github/blob/main/CONTRIBUTING.md#squash-commits).
This command uses an exact lease instead of the guide's bare force push.
See also [git-rebase](https://git-scm.com/docs/git-rebase) and
[git-push](https://git-scm.com/docs/git-push).
