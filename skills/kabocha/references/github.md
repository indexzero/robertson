---
name: github
description: GitHub settings, stacks, and the changes GitHub makes when it squashes a PR. Read before you check settings, link a stack, predict a commit, or read PR edit history.
---

# GitHub

## Settings

The `ready` path depends on two repository settings. Check them before the
first write:

    gh api repos/OWNER/REPO \
      -q '{has_pull_requests,squash_merge_commit_title,squash_merge_commit_message}'

- `squash_merge_commit_title` must be `PR_TITLE`.
- `squash_merge_commit_message` must be `PR_BODY`.
  `COMMIT_MESSAGES` pastes every branch commit body into the squash commit.
- `has_pull_requests` must be `true`. The pull request feature checkbox
  sits on the same settings page, and an operator can clear it by accident.

kabocha does not change repository settings. Report the setting and the
command that fixes it, then stop.

## Stacks

`gh stack` links PRs whose bases form a chain.

- `gh stack link <bottom> ... <top>` creates or extends a stack. Each
  argument is a PR number or a branch. It prints the stack number.
- `gh stack merge <stack> --squash` merges every PR up to the top in one
  operation that succeeds for all or for none. Each PR becomes one squash
  commit. GitHub re-parents each child, so nobody rebases.
- The squash message comes only from the repository defaults. There is no
  per-PR message override, so the PR title and description must be final.
- A stack holds at most 100 PRs, all in one repository. A merge queue
  ignores the merge method and can split the stack.
- Before you link, find hidden children: open PRs whose base is a branch
  of the set but that are not in the set. Include them or report them.

## What GitHub does to a squash commit

Predict the commit before the ready report. With `PR_TITLE` and `PR_BODY`,
GitHub builds the message as follows. Each point was observed on a real
merge.

1. The subject is the PR title plus ` (#N)`.
2. The body is the PR description. GitHub removes the final newline.
3. GitHub collects the `Co-authored-by:` trailers from the squashed branch
   commits. It appends a line of nine hyphens and those trailers as a new
   last paragraph. It keeps one trailer for each email address, with the
   name from the oldest commit that uses that address. This moves
   the attribution block out of the last paragraph, and git then stops
   reading `Assisted-by` as a trailer.
4. A body line longer than 72 columns can be rewrapped, and a rewrapped line
   loses its indentation. Keep every line at 72 columns or fewer.
5. `gh pr merge --squash --subject ... --body-file ...` replaces both
   defaults. With an explicit subject, GitHub does not append `(#N)`.

When point 3 applies, the description cannot correct it. Report the
predicted trailer paragraph and name `seal` as the correction, because a
sealed branch carries only the approved message.

## Edit history and merges

GitHub keeps every revision of a PR description:

    gh api graphql -f query='query { repository(owner:"OWNER", name:"REPO") {
      pullRequest(number: N) { state mergedAt lastEditedAt
        mergeCommit { oid } body
        userContentEdits(first: 20) { nodes { editedAt editor { login } } } } } }'

The editor login is the account that owns the token. kabocha and the
operator usually share that account. Tell kabocha's edits from the
operator's by the times and body hashes in the ledger, never by the login.

Parse this output with a JSON parser in a script. A shell `echo` of the
JSON can turn `\n` escapes into newlines and break the parse.
