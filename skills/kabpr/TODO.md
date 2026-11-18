---
status: "prepare implemented; broader behavioral evals remain"
branch: "feat/kabpr"
---

# Remaining work

- Run the broader stack, seal, and squash behavioral fixtures in
  [evals/evals.json](evals/evals.json). The prepare helper has isolated
  behavioral tests; they do not establish live merge behavior.
- Verify whether explicit squash bodies receive co-author trailers.
  Until then, retain the uncertainty in `commands/squash.md`.
- Reconcile historical kabocha runs when requested. Their approval
  records remain under `~/.claude/kabocha/`.

## Consolidated branch work

The original kabocha implementation from `skill/kabocha` landed through
robertson PR #4. Its remaining commit `6e066f8` was cherry-picked as
`8431ad5`: update `.vlurpfile` usage and lineage-restore instructions.
The instructions now use the renamed `skills/kabpr` directory.

`next/iter` commit `8692361` was cherry-picked as `5a982a8`. Its old
`skills/ste-seal/SKILL.md` path had been removed, so the conflict was
resolved into the current `commands/seal.md`: capture full object IDs
from Git, omit PR-number suffixes on sealed titles, and take lease values
from backup refs. The follow-up `9db1eac` restored the rule to stop after
a failed lease. That rule was already in kabocha and remains unchanged;
the temporary retry exception from `8692361` was not carried forward.

The user's `8ad99fd` on `feat/kabpr` preserves the pending title-style
changes and matching eval expectations. No historical branch needs to
be retained solely for unique source changes after this branch is saved.
Old untracked or ignored local files should be checked before removing
their worktrees.
