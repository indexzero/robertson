---
name: ready
description: The default kabocha command. Turn reviewed PRs into approved squash messages, linked stacks, and a ready report with the merge commands. It never merges.
---

# ready

`ready` ends with a report the operator acts on. It writes to PR titles,
PR descriptions, and stack links, and only after approval. It never
touches a branch and never merges.

Read [../references/message-style.md](../references/message-style.md),
[../references/github.md](../references/github.md), and
[../references/ledger.md](../references/ledger.md) first.

## 1. Reconcile

Do the reconcile step from SKILL.md for this repository. Report its one
line.

## 2. Resolve the PR set

The request names a topic and a repository, PR numbers, or a stack.

- PR numbers or a stack number: use them. Add the open PRs of a named
  stack with `gh stack view`.
- A topic: search the open PRs of the repository. Match the topic against
  titles, descriptions, branch names, labels, and changed paths:

      gh pr list -R OWNER/REPO --state open --limit 200 \
        --json number,title,headRefName,baseRefName,labels,isDraft,files

- Follow base edges in both directions. Every open PR whose base is the
  head branch of a PR in the set joins the set or is reported as a hidden
  child.
- Report what you resolved and what you excluded, with one reason each.

For each PR, read its state, draft flag, base, head, mergeable state,
review decision, and the checks on its current head. A PR that is not open,
is a draft, or is `CONFLICTING` leaves the batch. Report it and continue
with the rest.

Write the `resolved` event.

## 3. Measure the tier and group the scopes

Measure the tier with the table in SKILL.md. Group the PRs into scopes. A
stack chain is one scope. State the tier and the scopes in one line.

At tier 50, show the plan and stop:

- each scope, its PRs from root to leaf, and the stack it will become
- the order of the scopes, with each dependency named (a scope that edits
  code another scope also edits goes after it)
- PRs excluded and why
- each risk that crosses scopes: a removed export that another scope still
  imports, or a lockfile or changelog that several scopes change

Continue only when the operator accepts the plan or edits it.

## 4. Check the settings

Check the settings in [../references/github.md](../references/github.md).
If one is wrong, report it with its fix command and stop. kabocha does not
change repository settings.

## 5. Draft, lint, and predict

For each PR, in scope order and from root to leaf:

1. Draft the message with the drafter from
   [../references/drafters.md](../references/drafters.md). Write the
   `drafted` event.
2. Lint the draft with the checks in message-style.md. Fix each failure in
   the draft.
3. Predict the squash commit with the rules in github.md. Read the branch
   commits for `Co-authored-by` trailers:

       gh pr view N -R OWNER/REPO --json commits \
         --jq '.commits[].messageBody' | grep -i '^co-authored-by:'

   List each difference between the prediction and the draft.
4. Write a `signal` event for each mixed-scope subject, long line, or
   co-author append. Do not tell the operator to split a PR.

## 6. Show one approval batch for each scope

For each scope, show:

1. One line: the scope, its PR count, and its stack order.
2. The subjects as a numbered list, so the operator can skim them.
3. Each full message in a code block, in stack order.
4. The predicted differences for each PR. Name `seal` as the correction
   when GitHub will append co-author trailers.

Ask for an explicit approval of the batch. An edit request changes the
bytes: show the changed message again before you record it. Write the
`approved` event with the hash of each message.

## 7. Apply

For each approved PR, from root to leaf:

1. Save the current title and description as a backup next to the ledger.
2. Write the title and description:

       gh pr edit N -R OWNER/REPO --title "<title>" --body-file <message body file>

3. Read them back. Compare the bytes with the approved message, ignoring one
   final newline. A mismatch stops the scope.
4. Write the `applied` event with the time and the body hash.

## 8. Link

For each scope with two or more PRs, link the stack from root to leaf:

    gh stack link <root> ... <leaf>

Confirm that each PR is still open, `MERGEABLE`, and at the head you
checked in step 2. Write the `linked` event.

## 9. Report ready

Write the `predicted` and `ready` events, then report:

- for each scope: its stack number, its PRs, and the merge command:

      gh stack merge <stack> --squash

  or, for a single PR, `gh pr merge N --squash`
- the order in which to run the scopes' commands
- each predicted difference that the description cannot correct
- the PRs left out of the batch, and why

Do not run the merge commands.
