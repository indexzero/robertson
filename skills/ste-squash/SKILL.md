---
name: ste-squash
description: Squash-merge a GitHub PR with a Rob Pike / Plan 9 style commit message written in Simplified Technical English, ending with the house terminator and a Co-Authored-By trailer recovered from the branch commits. Invoked explicitly as /ste-squash <pr-number>; never auto-invoked (it merges code).
argument-hint: "[pr-number]"
arguments: [pr_number]
disable-model-invocation: true
allowed-tools: Bash(gh pr view *) Bash(gh pr diff *) Bash(gh pr checks *) Bash(git fetch *) Bash(git log *)
---

# /ste-squash — squash-merge a PR with a house-style message

Squash-merge PR #$pr_number. Draft the message, show it, get an explicit
yes, then merge. Never merge before the yes.

## Live state (injected before you start)

PR snapshot:

!`gh pr view $pr_number --json number,title,state,isDraft,baseRefName,headRefName,mergeable --template '#{{.number}} {{.state}} draft={{.isDraft}} base={{.baseRefName}} head={{.headRefName}} mergeable={{.mergeable}} — {{.title}}'`

Changed files:

!`gh pr diff $pr_number --name-only | head -20`

Branch commit messages (the trailer source):

!`gh pr view $pr_number --json commits --jq '.commits[].messageHeadline'`

## Step 1: Gate checks

Stop and tell the user instead of merging when any of these is true:

1. The PR state is not OPEN, or it is a draft.
2. The base branch is not the repository default branch. A stacked PR needs
   its parent merged and a `git rebase --onto` first — squash-merging the
   parent rewrites its commits, so the child's diff still carries them.
   Explain that; do not attempt the rebase yourself unless asked.
3. `mergeable` is CONFLICTING.

## Step 2: Recover the trailer model

The trailer names the model that AUTHORED the branch, not the model doing
the merge. Read it from the branch commits:

```
gh pr view $pr_number --json commits --jq '.commits[].messageBody' | grep -m1 'Co-Authored-By: Claude'
```

Use that line verbatim. If no commit carries one, use the current session's
model name (`Claude <Model> <noreply@anthropic.com>`).

## Step 3: Write the message

Read the PR body and, when the diff is small or the body is thin, the diff
itself (`gh pr diff $pr_number`). Say only what the diff supports. Do not
repeat the PR body if it is verbose — compress it.

**Title** — Rob Pike / Plan 9 style:
- `area: what changed` — lowercase after the colon, no trailing period,
  under ~65 characters.
- The area is the subsystem (`parser:`, `cli:`, `docs:`), not the repo.
- The verb states the change plainly: delete, move, unify, share, hoist.
- REMOVE ANY AND ALL `(#N)`, `(§N.N)`, `(N.n)`, `(N.N)` markers that are
  not the PR itself — PR titles often carry planning-doc section numbers;
  none of them land in the commit. The ONE permitted parenthetical is this
  PR's own `(#N)`, appended at the end per the repo's squash convention.

**Body** — Simplified Technical English, pragmatic mode:
- Sentences under 20 words. One fact per sentence. Active voice.
- Simple tenses only. No "should", "would", "may", "might", "could".
- No filler: leverage, robust, comprehensive, seamlessly, in order to,
  it is worth noting. Delete decoration; keep facts.
- Numbers beat adjectives: "about 1,800 parsers each second", not
  "significant overhead".
- A surprising keep or a non-obvious reason earns its own short paragraph.
- When the change DELETES dead code, the body explains its origin, not
  just its unusedness — run the archaeology (`git log --follow`,
  `git log -S`) and cite the introducing commit hash. "Shipped nowhere"
  is a smell; "built in <hash> for X, which then did Y instead" is a
  commit message. Verify the origin against history — a plausible
  recollection is not a record.
- 2–6 sentences total. If the change is fully described by the title, the
  body can be one sentence.
- References: the body names GitHub issues the change closes or relates to
  (`Closes #N.` / `Refs #N.` — verify the number is real with `gh` before
  citing) and other durable systems of record (committed docs, in-repo
  RFCs). It NEVER cites internal planning references — proposal section
  numbers, dispatch IDs, run-ledger names. Those belong in PR bodies only:
  the PR is the planning record; the commit is the permanent one.

**Terminator** — end the body with EXACTLY this (nine hyphens, blank line,
trailer). Do not omit it; do not add any other attribution line:

```

---------

Co-Authored-By: Claude <Model> <noreply@anthropic.com>
```

## Step 4: Confirm, record, merge, verify

The approval must survive the conversation. The record lives at
`~/.claude/ste-squash/approvals.jsonl` (append-only; create the directory
on first use). The hash binds the copy the user approved to the copy that
ships — without it, nothing but discipline connects the two.

1. Show the user the complete message (title + body) in a code block.
2. Wait for an explicit yes. "Looks fine" with an edit request means edit
   and show it again. Every edit invalidates the previous text; hash only
   the final approved version.
3. Record the approval. Hash the exact message (`<title>\n\n<body>`,
   terminator and trailer included) with `shasum -a 256`, then append:
   ```json
   {"event":"approved","repo":"<owner/name>","pr":N,"title":"<title>","message_sha256":"<hash>","at":"<ISO8601>"}
   ```
4. Merge with exactly the approved bytes. Write the body to a temp file
   first and pass `--body-file` — it dodges shell-quoting drift:
   ```
   gh pr merge $pr_number --squash --subject "<title>" --body-file /tmp/ste-squash-<N>-body.txt
   ```
   Use `--delete-branch` only if the user asked or the repo auto-deletes.
   NOTE: ledger writes under `~/.claude/` must use the file tools
   (Write/Edit), not shell redirects — sandboxed bash cannot create files
   there. An explicit `--subject` also means GitHub does NOT append the
   conventional `(#N)` suffix; include it in the title only if the user's
   repo convention wants it.
5. Verify the binding: fetch, read the squash commit's full message
   (`git log <merge-oid> -1 --format=%B`), trim trailing whitespace, hash
   it, and compare to the approved hash. Append the outcome:
   ```json
   {"event":"merged","repo":"<owner/name>","pr":N,"merge_sha":"<oid>","message_sha256":"<hash>","matches_approval":true,"at":"<ISO8601>"}
   ```
   On a mismatch, say so loudly and show both texts — GitHub sometimes
   normalizes whitespace; a semantic difference is an incident, not a
   footnote.
6. Report: the one-line `git log` of the merge and the two ledger lines.

## Example

Input: PR #42, "perf(render): cache compiled templates between requests
(§3.2)" — a one-file diff that removes a per-request template compile.

Output:

```
render: cache compiled templates between requests

renderPage compiled its template on every request. Each page view ran the
compiler twice, once for the layout and once for the body, so a busy
instance spent about 40% of its time compiling. Compile each template once
on first use and keep it in a module-level map. The error template stays
per-request: it interpolates the failing request into its source.

---------

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

What makes it right: the title drops the conventional-commit wrapper and
the planning-section marker for the Plan 9 form; the body is five facts in
five short sentences; the surprising keep (the per-request error template)
gets its reason; the terminator is byte-exact.

## Must not happen

- A merge before the user's explicit yes in this conversation.
- A merge whose body differs from the last APPROVED hash for that PR —
  re-show and re-approve instead.
- A message that claims changes the diff does not contain.
- A title with any parenthetical reference other than this PR's own
  `(#N)`; a body citing internal planning documents.
- A missing or altered terminator, or a second attribution line.
- Merging a stacked or conflicting PR "helpfully".
- A merge with no `approved` line in the ledger, or a completed merge with
  no `merged` line (even on mismatch — especially on mismatch).
