---
name: ste-seal
description: Seal reviewed GitHub PRs as one commit each, with approved house-style messages. Preserve stack boundaries and leave PRs open. Use when asked to squash PR history without merging.
---

# ste-seal

Seal the selected PR or stack. Each PR ends with one commit relative to its
immediate base. Preserve its complete file tree and leave it open.

Keep the message, attribution, approval, and verification workflow of
`ste-squash`. Replace its squash-merge with a local squash and leased push.
Never run `gh pr merge`, `gh stack merge`, or any other merge operation.
Do not enable auto-merge, close PRs, delete branches, or push the default branch.

Examples:

- `Use ste-seal on PR #42.`
- `Use ste-seal on the #40 -> #42 -> #45 stack.`

An instruction to create this skill does not authorize sealing those example PRs.
A stack request means one commit per PR, never one commit for the entire stack.

## 1. Inspect and pin the scope

Read repository instructions. Resolve the repository, push remote, PR branches,
and their worktrees. Fetch the named refs without changing checkout contents.
Do not assume that `origin` is the PR head repository, especially for forks.

Use `gh pr view` to inspect the full body, diff, state, draft flag, base,
head, review state, and current-head checks. Read the actual commit messages.
Use the stack metadata when available, then verify its edges against PR bases.

Before rewriting, require:

- Each PR is open and ready. It has no active auto-merge or merge-queue enrollment.
- GitHub does not report `CONFLICTING`. Sealing does not repair source conflicts.
- The requested review is complete and current-head CI passes under repository policy.
- Each affected worktree is clean, with no rebase, merge, or other Git operation active.
- Each local branch equals its pinned remote PR head. Do not discard local-only commits.
- No other author or reviewer owns an affected worktree.
- No selected head is the default branch or another shared integration branch.

Record this table before changing any ref:

| PR | Head repository and branch | Old head | Immediate base | Old boundary | Original tree |
|---|---|---|---|---|---|

For a PR based on the default branch, use its unique merge-base with the
fetched base as `old_boundary`. Base advancement alone is not a reason to
include unrelated upstream commits in this squash.

For a stacked PR, require the pinned parent head to be an ancestor of the
child. Use that exact old parent head as the boundary. If it is not an
ancestor, resolve the existing stack divergence as a separate task first.

Count and inspect only `old_boundary..old_head`. Recover messages and trailers
from that range, never from every commit reachable from the branch.
If the range is empty or contains merge commits, stop before rewriting.
This workflow handles linear PR histories. Do not silently flatten a merge.

Find open child PRs by their base branch, including children outside any stack
listing. Rewriting a parent invalidates those children's ancestry.
Include only authorized descendants. If a child is outside scope, obtain an
explicit scope extension before rewriting its parent. Do not leave a hidden
child with the old parent commits in its PR diff.

## 2. Draft the house-style message

Read the PR diff against its pinned boundary. Explain only changes in that PR.
Use `ste-squash` conventions:

- Title: `area: what changed`, lowercase after the colon, with no final period.
- Aim for about 50 characters. Keep the title under roughly 65 characters when practical.
- Name the subsystem, not the repository. Use a plain change verb.
- Remove planning-section markers and unrelated `(#N)` suffixes.
- Append this PR's own `(#N)` only when the repository convention requires it.
- Separate title and body with a blank line. Wrap body text near 72 columns.
- Use two to six short sentences. One sentence can suffice for a simple change.
- Keep sentences under 20 words. Use active voice, simple tenses, and one fact per sentence.
- Explain the problem and reason. Include consequential side effects or surprising behavior that remains.
- Remove filler and speculative claims. Do not use `should`, `would`, `may`, `might`, or `could`.
- For deleted dead code, verify its origin with history. Cite the introducing commit when that history explains the deletion.
- Verify issue numbers before using `Closes #N.` or `Refs #N.` near the bottom.
- Do not cite private run ledgers, dispatch IDs, or internal planning sections.

Recover `Co-Authored-By:` trailers from the PR-owned commits. Preserve the
actual author attribution, including Codex or Claude. Never substitute the
sealing agent for the author. Deduplicate identical trailers without losing
distinct contributors. If none exists, use the actual session attribution
required by the repository. Never invent a model name.

End the body with nine hyphens, a blank line, and the recovered trailer lines:

```text
---------

Co-Authored-By: Codex <noreply@openai.com>
```

The example trailer is illustrative. Use the recovered attribution.

## 3. Prepare the approval record

Store message files and an append-only ledger under `~/.claude/ste-seal/`,
or a run-local path required by the repository. Use the host's permitted
file-write mechanism. Do not assume a particular sandbox or bypass a denial.

Write each complete message to a file. Canonical bytes are UTF-8 with LF
newlines and exactly one final newline. Hash those exact bytes with SHA256.
Use the same file for the eventual commit. Do not interpolate its contents
into shell commands or reconstruct it from escaped JSON.

Prepare the complete plan before requesting approval:

- Exact PRs and branches, ordered from the stack root to its leaves.
- Each old head, old boundary, and original tree.
- The complete proposed message for each PR, in a code block.
- The descendants that need restacking and the exact force-push leases.

Ask for approval of the displayed messages and history rewrite. One explicit
approval can cover the displayed batch. Reuse an existing approval only when
it already binds these messages, heads, boundaries, and branches.
A general code-review approval does not approve an unseen commit message.

An edit request changes the proposed bytes. Show the edited message before
recording its approval. Append an event for each approved PR:

```json
{"event":"approved","repo":"owner/name","pr":42,"head_repo":"owner/name","branch":"feature","old_head":"...","old_boundary":"...","tree":"...","message_sha256":"...","at":"ISO8601"}
```

Recheck the live heads, PR states, base relationships, and approval binding
before the first rewrite. If an unexpected ref changed, stop and rebuild the
plan. Do not silently refresh an old approval or its expected lease.

## 4. Squash and restack locally

Create local backup refs for every old head before the first rewrite.
Use unique names under `refs/ste-seal/<run-id>/`. Record their names in the
ledger. Do not delete them during this operation or push them to the remote.

Work from root to leaves, in each branch's existing clean worktree.
Use repository worktree tooling if an additional checkout is required.
Never switch a branch that is checked out in another worktree.

If the range already has one commit with the approved message and parent,
leave it unchanged. Otherwise amend only what this operation authorizes.

For a child whose parent was sealed in this batch, first replay only the
child-owned commits onto the new parent:

```sh
git -c rebase.updateRefs=false rebase --no-autostash \
  --onto "$new_parent" "$old_parent" "$child_branch"
```

`old_parent` is the immutable parent head from the original plan. Never use
the newly moved parent ref as the exclusion boundary.
For a root, retain its recorded merge-base as `squash_boundary`.
For a child, use the new parent head, or the unchanged parent when not selected.

Apply the Sigstore squash procedure to this exact PR range:

```sh
git -c rebase.updateRefs=false rebase -i --no-autostash \
  --no-autosquash "$squash_boundary"
```

Keep the oldest PR-owned commit as `pick`. Change every remaining PR-owned
commit to `squash`. Never include the parent PR's commit in that list.
For unattended execution, use a deterministic sequence editor that rejects
an unexpected todo list. Do not use a broad text substitution over arbitrary commands.

Replace the combined message with the approved file:

```sh
git commit --amend --cleanup=verbatim -F "$approved_message_file"
```

Preserve the original first commit's author identity and required signing
policy. Do not bypass required hooks or signoff rules. If a hook changes the
approved message, stop before pushing and resolve the mismatch.

On a conflict, abort only the rebase started by this operation. Keep backups
and report the affected PR. Do not resolve content conflicts, change source,
regenerate artifacts, or run `reset --hard` as part of sealing.

Before any push, prove for each selected PR:

- Its new tree equals the recorded original tree exactly.
- Its sole commit has the expected immediate parent.
- `git rev-list --count "$squash_boundary..HEAD"` returns `1`.
- Its PR diff against the new boundary equals the original PR diff.
- Its message bytes match the approved SHA256.
- Its working tree and index are clean.

Use the raw commit object to read message bytes after the header's blank
line. Do not use `%B` output with an extra newline or trim arbitrary whitespace
before hashing. A message mismatch is a failed gate, not a harmless normalization.

For a rewritten parent, also verify its tree equals the old parent's tree.
That equality is required for the child's unchanged tree and diff claims.
Record new heads and proof results before touching any remote ref.

## 5. Push, verify, and leave open

Push one branch at a time, root to leaves. Verify the PR still targets the
same base branch and that the destination is the recorded head repository.
Use the exact old remote head in the lease and an explicit branch refspec:

```sh
git push --force-with-lease="refs/heads/$branch:$old_head" \
  "$push_remote" "refs/heads/$branch:refs/heads/$branch"
```

Never use bare `--force`, an unqualified lease, `origin HEAD`, or `--delete-branch`.
After each push, fetch and verify the remote head, tree, message hash, and
unchanged PR base. Append the outcome immediately:

```json
{"event":"pushed","repo":"owner/name","pr":42,"old_head":"...","new_head":"...","message_sha256":"...","matches_approval":true,"tree_unchanged":true,"at":"ISO8601"}
```

If a lease fails, stop. Do not retry with a fresh lease or overwrite the
concurrent work. If an earlier push succeeded, record the partial batch and
identify the descendants still awaiting repair. Never roll back remote refs
or merge a partial stack automatically.

Verify the final stack edges and one-commit counts after all pushes.
Wait for required CI on the new heads. Old green checks do not cover new
commit IDs. Report a failed or unavailable check without claiming completion.
Do not close and reopen a PR, add a trigger commit, or change source just
to manufacture a successful sealing run.

Append `sealed` only after the remote proofs and new-head CI pass.
Report each PR, old head, sealed head, commit subject, and CI status.
State that every PR remains open and unmerged. Link the approval ledger.
Sealing does not make a branch immutable. Later changes require a new seal.

## Sources

The user-supplied [Sigstore contributing guide](https://github.com/sigstore/.github/blob/main/CONTRIBUTING.md#squash-commits)
provides the pick-first, squash-rest procedure and commit-message guidance.
This skill uses an exact lease instead of the guide's bare force push.

- [Git interactive rebase and upstream recovery](https://git-scm.com/docs/git-rebase)
- [Git explicit force-with-lease semantics](https://git-scm.com/docs/git-push)
