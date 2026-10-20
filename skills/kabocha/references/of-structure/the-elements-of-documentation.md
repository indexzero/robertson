---
_id: a0f9edad7dccb008ed4b0b89e178c5e02eb52fbd1ecc6e64a4ce1c722fa7d05c15
_rev: "3d0aabb7a34baca93afb1c13634b39f5c0845f2a51f6ddd484197f4c806e0913"
type: guide
title: The Elements of Documentation
---


# THE ELEMENTS OF DOCUMENTATION

*rules, and the prices they charge*

---

## Dedication

For the engineer at midnight, two years from now, who cannot ask us anything.
Every rule in this book is an answer she will need.

## Epigraphs

> Record what evaporates.

> The bad message wasn't cheaper to write — it was only cheaper to think.

The first tells you what to write. The second tells you why you didn't.

---

## Preface

Begin with two commit messages that describe the same change:

```
Fixed some issues with the connection handling code.
```

```
pool: return connections to the pool after idle timeout
```

You already prefer the second, and you have not read a single rule yet. That is
the bet this book makes on every page: shown a good example and a bad one side
by side, you will know which is which. The rules exist only to tell you *why*
you knew, so that you can do it on purpose, at nine in the morning, on a
change you barely care about. Anyone writes well about work they love. The
rules are for the other days.

This book has one design center, and every rule serves her: the engineer at
midnight, two years from now, bisecting a failure, who finds your commit at
the bottom and cannot ask you anything. Write for her and everyone else is
served for free — the novice, because she needs plain sentences; the expert,
because he needs the load-bearing sentence findable; the machine, because
retrieval wants exactly what the tired human wants: one term per concept,
falsifiable claims, facts stated once, examples that run.

Every rule names its scope in parentheses, because a rule applied to the
wrong reader is a bug wearing a badge of virtue. What reference forbids,
teaching sometimes requires; say a thing once in a man page and twice in a
tutorial — but let the second telling know it is a second telling.

Two honest notes before we start. First, on our own prose: some of these
rules carry a subordinate clause. We let them stand, and we record why — a
rule may spend words to forestall the misreading that would cost more than
the words. Concision is a budget, not a vow. Second, on enforcement: about
five of these twenty-two rules can be checked by a machine — subject form,
trailer spelling, examples that compile, a term dictionary, a drift check.
Lint those, and spend the reviewer's rescued attention on the seventeen that
need a human. Lint the form; review the truth. The reviewer's checklist for
the seventeen is short: Is the subject falsifiable, and is it true? Does the
body say why? Does anything in the message contradict the diff? Does anything
in the diff surprise a reader of the message? Four checks, two minutes,
permanent value.

The nine of us who argued this book into existence closed with one sentence
each. They are the book, compressed:

- **McIlroy:** Documentation is the part of the program that runs on people — write it, test it, and delete it to the same standard.
- **Kernighan:** Write so that the reader who knows least loses least, and the reader who knows most loses nothing.
- **Ritchie:** Every sentence of documentation is a promise; make only the promises you can keep, and keep every one you make.
- **Pike:** The diff says what; the message says why; anything else, one of you is lying.
- **Thompson:** Say it once, say it true, stop.
- **Cox:** Write for the reader who cannot ask you anything, because soon every reader is that reader.
- **Bernstein:** A sentence you cannot check is a sentence you cannot trust — write checkable sentences.
- **de Raadt:** If the documentation is embarrassing to write, the design is what's embarrassing — fix that, then write.
- **White:** Omit needless words; the words that remain, make true; and of the true words, keep the ones the reader cannot get anywhere else.

---

# CHAPTER I — THE SUBJECT LINE

*Rules for the fifty characters read a thousand times.*

The subject line is read a hundred times for every time the body is read, and
a thousand times for every time the diff is read. `git log --oneline` strips
everything else away. Every rule in this chapter is therefore written for one
reader: the person scanning five hundred subjects who will never open yours.

Underneath the chapter stands one principle, adopted verbatim: every layer of
documentation is a filter for the layer below. Subject filters body; body
filters diff; comment filters code. Each layer must add information, or be
deleted.

## Rule 1. Write the subject for the reader who will never open the commit. *(subjects)*

Sin:

```
misc updates and improvements
```

Obedience:

```
parser: accept dates before 1970
```

Read the first subject and ask what you now know. Nothing — except that you
must now read the diff yourself, which means the message saved you no time,
which means it failed at its only job. Read the second and you can decide, in
under a second, whether this commit concerns you. That decision is the
subject's entire purpose. It is a filter for the layer below it, and a layer
that filters nothing should be deleted — but you cannot delete a subject
line, so you must instead write one.

In practice the form is: address, colon, claim. The address (`parser:`) names
the territory so the scanning reader can skip whole territories at a stride.
The claim is lowercase — the address already did the capital's job — and
takes no terminal period, because a subject is a heading, and headings do not
claim to be finished sentences. Also, the period is one more character.

## Rule 2. Use the imperative: name the act, not the aftermath. *(subjects)*

Sin:

```
Fixed race condition in scheduler
```

Obedience:

```
scheduler: fix race between shutdown and tick
```

"Fix," not "fixed" or "fixes." A commit is not a diary entry; it is an
instruction to the tree — apply this, and the race is fixed. The imperative
names the act the way a function name does: `fixLeak()`, never
`leakWasFixed()`. There is honest humility in it, too. "Fixed" announces a
fact about the past that the commit cannot actually promise — the bug may
outlive the commit — while the imperative names only an intention, which is
the one thing the author truly knows.

## Rule 3. Make the subject falsifiable. *(subjects)*

Sin:

```
cleanup
```

Obedience:

```
smtpd: reject bare LF in commands
```

Take the second subject to the diff and you can verify the claim in thirty
seconds: there is the check, there is the rejection. Take the first to the
diff and you can verify nothing, so you must verify everything, so the
message saved you nothing — and worse. The subject line is the only part of
most changes anyone will ever audit. A subject that cannot be checked
against its diff is not a summary; it is decoration, and decoration invites
forgery. "Cleanup," "various fixes," and "improvements" are therefore
forbidden — not discouraged, forbidden. A subject is falsifiable or it is
decoration.

## Rule 4. State the effect, not the mechanism — unless the mechanism is the news. *(subjects)*

Sin:

```
dial: use sync.Once for connection setup
```

Obedience:

```
dial: connect only once per address
```

The sin subject tells the reader what she would learn from the diff in ten
seconds anyway. The obedient one tells her the thing the diff cannot say: the
behavior she may now rely on. Never spend the subject on information the
reader already holds in her hands.

The exception is built into the rule, because it is real: sometimes the
mechanism *is* the news. A revert, a vendoring bump, a rename — say it
plainly:

```
runtime: revert CL 12345
```

The principle beneath both halves: say the thing the reader cannot get
anywhere else.

---

# CHAPTER II — THE BODY

*Rules for the midnight reader.*

The diff preserves the *what* forever. The *why* dies with the author's
attention — usually within a month, sometimes by Friday. The body exists to
record precisely the part that evaporates, and nothing else. The early Unix
commits had no bodies at all; their authors are still answering email about
them forty years later. The flag is three characters. The thread is forty
years long.

## Rule 5. Record what evaporates. *(commit bodies)*

Sin — the diff is `-timeout: 10s` / `+timeout: 30s`, and the body reads:

```
Increase timeout to 30s.
```

Obedience — same diff:

```
The CI runners got slower after the migration to arm64; the old
10s limit now fails about one build in twenty with no real fault.
```

The sin body recites what the diff already says eternally. The obedient body
records the one fact that exists nowhere else and will exist nowhere at all
once the author forgets it. That is the whole law of the body: the why, the
alternatives rejected, the costs knowingly accepted — and nothing the reader
already holds.

When is a body owed at all? Not always. `spell: fix typo in error message`
needs no body; its why is self-evident for exactly as long as the diff
exists, which is forever, and the empty body is not an exemption from the
standard — it *is* the standard, applied. The test: would a competent reader
of the diff still have a question? Measure by the diff's consequence, never
its size. One-character diffs have shipped root holes; if the one character
matters, the message says why. `if (a = b)` to `if (a == b)` deserves a
paragraph.

## Rule 6. State the problem before the solution. *(commit bodies)*

Sin — the body opens:

```
Switch the pool's free list to a doubly linked list and release
timed-out slots through put().
```

Obedience — the body opens:

```
Connections that hit the idle timeout were closed but never removed
from the pool's active count, so the pool eventually reported itself
full while holding no live connections. New requests then blocked
forever in Get.

The timeout path now releases the slot through the same put() as the
normal path, so the count can no longer drift from the live set.
```

A body that opens with the fix is a proof with no theorem. Paragraph one
earns the reader's belief that a problem exists — stated so that a reader
with no context believes it. Paragraph two states the fix at the level of
intent: what invariant now holds that did not before. Only if needed,
paragraph three: alternatives rejected and why, and what to look at if this
turns out to be wrong.

## Rule 7. Write complete sentences, in order of importance. *(commit bodies)*

Sin:

```
fixed leak. also refactor. tests pass. first I looked at the timer
code, then I noticed the pool wasn't releasing.
```

Obedience:

```
The pool leaked one slot per idle timeout. The timeout path now
releases through put(), like the normal path. The leak was invisible
in tests because the test pool's timeout exceeded the test duration.
```

A sentence forces a claim; a fragment gestures at one. "Also refactor" — what
was refactored, toward what? A sentence would have had to say. And put the
sentences in order of importance, not in order of discovery. "First I looked
at X, then I noticed Y" is the author narrating their own afternoon, and
nobody cares about your afternoon. State the conclusion. State why it is
right. Stop.

That third obedient sentence is worth noticing: when the bug was interesting,
spend one sentence on the *shape* of the trap — not your day, the trap. It
teaches the next reader to see traps of that shape, and it is the difference
between a log entry and a lesson.

## Rule 8. Address posterity, not the approver. *(commit bodies)*

Sin:

```
Please review the locking carefully — this touches critical code!
See the discussion in #4127 for why this approach was chosen.
```

Obedience:

```
Taking the pool lock inside the timer callback deadlocks against
Close, which holds the lock while waiting for timers to drain
(repro and benchmarks in #4127). The timer now snapshots the slot
under the lock and releases it outside.
```

The review dies within the week; the log is forever. "Please look carefully"
is addressed to a person who will have finished looking before the ink dries,
and it will still be there, useless, in a decade. Worse is the load-bearing
link: "see #4127 for why" outsources the *why* to a system with a different
lifetime, and the day the tracker migrates, your commit becomes a locked box
labeled "key elsewhere." The rule for links: the message stands alone on the
why; the link carries the archaeology — repro logs, benchmarks, dead ends.
Summarize the verdict; cite the trial.

## Rule 9. End with the trailers, exactly spelled. *(commit bodies)*

Sin:

```
...so the count can no longer drift. this fixes issue 4127 btw
```

Obedience:

```
...so the count can no longer drift.

Fixes #4127
```

Machines read the bottom of the message, and machines do not do "btw."
`Fixes #4127` closes the issue; "fixes issue 4127," buried mid-paragraph,
closes nothing, and the issue stays open until a human notices, which is to
say, stays open. Trailers go at the bottom, one per line, in the machine's
dialect, spelled exactly. This is the cheapest rule in the book to obey and
among the most commonly broken, a combination that should embarrass us all.

## A boundary dispute: the changelog is not the commit log in a suit

The commit log addresses the maintainer of the code; the changelog addresses
the operator of the software. Different reader, different unit. The commit's
unit is a change to the tree; the changelog's unit is a change to the
*user's world* — a flag added, a default altered, a behavior gone. Most
commits produce no changelog line; some changelog lines summarize forty
commits. Generating one from the other force-feeds two readers one document.

The changelog line has its own grammar: what changed for you, what you must
do about it, nothing else.

Sin: `Upgraded internal parser.`
Obedience: `Dates before 1970 no longer parse as errors.`

## Worked example: the commit message

A specimen from the wild. Keep your composure:

```
Fixed some issues with the connection handling code. There were
several problems that this PR addresses. First I noticed that the
pool wasn't working right so I investigated and found that it was
related to how we were handling timeouts. Also refactored some
stuff in pool.go to be cleaner and more maintainable going forward.
Please review carefully since this touches critical code!
Various other small fixes included as well.
```

The diagnosis, rule by rule. Every sentence is unfalsifiable — "some issues,"
"several problems," "working right," "some stuff": six claims, zero checkable
(Rule 3). Past tense narrating the afternoon — "First I noticed... so I
investigated" (Rule 7). "Cleaner and more maintainable going forward" — three
phrases, no information, one of them naming the direction time already goes.
"Please review carefully" — addressed to the approver, dead within the week
(Rule 8). And "various other small fixes" is the confession that this commit
should have been three.

The cure begins with the split: the timeout bug and the refactor ride
separately, because Rule 3 cannot hold a subject over a mixed diff. Commit
one:

```
pool: return connections to the pool after idle timeout

Connections that hit the idle timeout were closed but never removed
from the pool's active count, so the pool eventually reported itself
full while holding no live connections. New requests then blocked
forever in Get.

The timeout path now releases the slot through the same put() as the
normal path, so the count can no longer drift from the live set. The
leak was invisible in tests because the test pool's timeout exceeded
the test duration.

Fixes #4127
```

Commit two:

```
pool: hoist dial retry out of Get

No behavior change.
```

— where "no behavior change" is stated as the claim it is, checkable by any
reader against the diff.

Now notice what the rewrite cost: nothing. Every sentence came from knowledge
the original author held and withheld. The bad message wasn't cheaper to
write — it was only cheaper to think.

---

# CHAPTER III — DOCUMENTATION

*READMEs, references, tutorials, man pages.*

## Rule 10. First sentence: X is a Y that Z. *(all documents)*

Sin:

```
Flowlite is a blazingly fast, lightweight, developer-first framework
for building next-generation data pipelines with unparalleled DX.
```

Obedience:

```
Flowlite runs data pipelines defined as plain Python functions, on
one machine, without a scheduler service.
```

The sin sentence has the form "X is a Y that Z" — where Y is "framework" and
Z is a row of adjectives. Blazingly fast compared to what, measured how?
Lightweight in what unit? After twenty-two words the reader still does not
know what the thing *does*. The obedient sentence gives category and
distinguishing property, before virtues, before history, before comparison —
so the reader who stops after one sentence stops informed. This is the topic
sentence, promoted to institution.

Two corollaries. Do not open with what it *isn't* — "X is not a framework" —
because negation is not identity; say what it is and the reader will work
out the complement. And do not open with the roadmap: promises about the
future are the least checkable claims in the document. Document what runs
today; the rest is marketing wearing documentation's clothes.

## Rule 11. One document, one reader. *(all documents)*

Sin — a reference page, paragraph three:

```
The --jitter flag adds up to N milliseconds of random delay. Don't
worry if that sounds scary! Randomness is your friend here, and by
the end of this section you'll love it. The delay is drawn uniformly
from [0, N). Trust us, this is easier than it looks!
```

Obedience — a reference page, line one:

```
This page is the reference for flowlite-retry. New to retries? Start
with the tutorial: docs/tutorial.md.
```

The sin is the hybrid: reference interrupted by pep talk, alternating modes
paragraph by paragraph, serving neither reader and lying to both about what
kind of page it is. The expert under attack at 3 a.m. cannot find the
load-bearing sentence between the reassurances; the novice cannot follow the
uniform-distribution clause between the encouragements. The answer was never
one document. It is the oldest solution we have: the man page and the paper —
reference and narrative, separated, cross-linked, each pure, neither
apologizing for the other.

So decide which reader you are serving before the first sentence, say so in
the first sentence, and route the other reader away by link. One line; both
readers served. No document should try to be a hallway and a room at once.

Brevity that locks out the second reader is not economy; it is cost-shifting —
a paragraph saved, and a thousand strangers each pay an afternoon. Verbosity
is cost-shifting too: it moves the afternoon from the novice to the expert,
who cannot find the load-bearing sentence on page nine. Routing is how both
debts are paid by the author, once, where they belong.

## Rule 12. Lead with a worked example, and make it complete. *(teaching; any document with examples)*

Sin:

```
# ...assuming the client from chapter 2 is configured:
result = client.run(pipeline, ...)
```

Obedience:

```
$ pip install flowlite
$ python -c "
import flowlite

def hello():
    return 'hello, world'

print(flowlite.run(hello))
"
hello, world
```

An example is the one form of documentation the author cannot fake. Prose can
bluff — "the tool handles errors gracefully" — but an example either runs or
it doesn't. The reader who has run something believes you; the reader who has
read four pages of abstractions is still deciding whether to. That is why the
example leads: it is the fastest trust you will ever earn.

But only a *complete* example earns it. Not "..." elided, not "assuming the
setup from chapter 2." Select, paste, run. An example with invisible
prerequisites is worse than none — it fails on the reader's machine and
teaches her to distrust the whole document. Where the tooling allows, put the
examples in the build: examples that compile under CI are prose under test,
caught by a machine before they can lie to a person.

## Rule 13. Answer the five questions in order. *(reference)*

Obedience:

```
NAME
     flowlite-retry - re-run a failed pipeline stage

SYNOPSIS
     flowlite retry [-n count] [--jitter ms] stage

DESCRIPTION
     Retries the named stage with exponential backoff...

EXAMPLES
     Retry the fetch stage up to 3 times:
           flowlite retry -n 3 fetch

BUGS
     Backoff is computed per stage, not per pipeline; parallel
     stages can thundering-herd the upstream.
```

Sin: the same content as one continuous essay, the invocation syntax first
mentioned in paragraph four, the example nowhere, the known deficiency
nowhere at all.

The man page anatomy is fifty years old and nobody has beaten it, because
every section answers exactly one question a reader arrives with, in the
order she asks them: What is this. How do I invoke it. What does it do. Show
me. What will bite me. Sections are routing. A README that answers the five
questions in its first screen is complete; everything after is appendix — and
a README that opens instead with a logo, twelve badges, and a paragraph of
adjectives has spent its first screen proving the project is alive instead of
saying what it is.

## Rule 14. Keep the BUGS section, and tell the truth in it. *(reference)*

Sin: the empty BUGS section. Or no BUGS section. Or — most common — a
"Limitations" heading containing one limitation, chosen for being flattering.

Obedience:

```
BUGS
     Slow, and stupid about tabs. Filenames with newlines confuse
     the -print output; use -print0. (Known since 2019.)
```

Modern documentation omits known deficiencies as if omission fixed them. The
old BUGS sections bought reader trust at the price of author vanity, and it
was the best purchase in the manual: a document that admits one true fault is
believed about everything else. State the known deficiencies plainly, dated
if possible. The confession is the credential.

One narrowing, from the security desk: do not publish *suspicions* in
security-sensitive documentation — "this area is probably weak" is a treasure
map. Confess the deficiencies you would bet on, or say nothing. The
credential is the confession's accuracy, not its existence.

## A boundary genre: the deprecation notice

The deprecation notice is the only documentation written *to* someone you are
actively inconveniencing, and it is usually written as if to someone you are
rid of.

Sin:

```
Deprecated: use NewThing instead.
```

Obedience:

```
Deprecated: parse() stops working in v3.0 (June 2027).

    old:  parse(s, true)
    new:  parseStrict(s)

If you relied on parse(s, false) recovering malformed input, there
is no one-to-one replacement; see recover() and its caveats.
```

The complete form has four parts and fits in four lines: what stops working;
*when* it stops; the one-to-one replacement, shown, not named — old call
above, new call below; and the escape hatch for the case where the mapping
isn't one-to-one. "Deprecated" without a date is a mood, not a notice; the
reader plans around dates, not vibes. And have the courage to finish the
sentence — announce, date, remove. A deprecation that lives five years
documents a decision you declined to make.

The migration guide is part of the breaking change: same commit, same review.
If writing the migration table is too much work, you have just measured the
pain you are about to ship, multiplied by your user count. Reconsider the
break.

## Worked example: the README first screen

The specimen:

```
# ⚡ Flowlite ⚡
[12 badges]
Flowlite is a blazingly fast, lightweight, developer-first
framework for building next-generation data pipelines with
unparalleled DX. Built from the ground up with performance
in mind. No bloat. Batteries included.
## Why Flowlite?
We believe data engineering should spark joy...
```

The diagnosis: an adjective stack where the first sentence should be (Rule
10); "No bloat. Batteries included" — two slogans contradicting each other
three words apart; twelve badges proving the project is alive instead of
saying what it is; and a manifesto where the reader's five questions should
be (Rule 13).

The cure, four sentences:

```
Flowlite runs data pipelines defined as plain Python functions, on
one machine, without a scheduler service. A pipeline is a function;
a dependency is an argument. If you need distributed execution or a
UI, use Airflow — Flowlite is for the case where Airflow is too
much.
```

Category, property, boundary — and the honest routing of the wrong reader,
which is the roadmap in reverse and checkable today. "Spark joy" returns to
the drawer whence it came.

---

# CHAPTER IV — COMMENTS AND THE PLACEMENT OF TRUTH

*Where facts live so they cannot lie.*

The comment's great vice is that it cannot be executed, so it cannot be
caught lying. The compiler checks the code; nothing checks the comment
against the code. Every comment therefore starts life as a small debt, and
this chapter is about taking on only the debts worth their interest.

## Rule 15. Give every fact one home; let every other mention point. *(all prose)*

Sin — the number 30 appears in four places:

```
config.go:    DialTimeout = 30 * time.Second
dial.go:      // dials time out after 10 seconds
README.md:    Dials time out after 10 seconds.
wiki:         The dial timeout is 15s (increased 2019).
```

Obedience:

```
config.go:    DialTimeout = 30 * time.Second   // the one home
README.md:    Dials time out after DialTimeout (see config.go);
              the default ships in config.go, not here.
```

The moment a fact appears in the code, a comment, the README, and the wiki,
three of the four copies are future lies — you just don't know which three
yet. In the sin above, all three copies have already rotted, each to a
different decade. State the fact once, where it is checkable — code, or a
test, or a generated reference — and let every other mention point at the
home instead of copying its contents.

This rule convicts most wikis, which are places where facts go to escape
review: no diff, no reviewer, no test, no owner. Documentation lives in the
tree, versioned with the code it describes, or it drifts alone in the dark.

## Rule 16. Comment what the code cannot say. *(comments)*

Sin:

```c
i++;  /* increment i */
```

Obedience:

```c
/* Retry once: the first read after resume returns EIO on this
 * controller even when the device is healthy. */
```

The sin comment proves only that the author was alive at the keyboard. The
code already says `i++`, faster and more reliably, and the comment that
translates code into English insults two languages at once. A comment earns
its debt only by saying what the code *cannot*: intent, invariant, the reason
the simpler approach fails. If a comment would survive being checked against
the code by a machine — because it says nothing the code doesn't — it should
not survive being checked by you.

## Rule 17. Spend your prose at the interface. *(comments)*

Sin — the contract, buried mid-function:

```c
    /* note: p must be locked by the caller or this races */
    n = flush(p);
```

Obedience — the contract, on the declaration:

```c
/* Flush p's pending writes and return the count flushed.
 * Caller must hold p->lock. Returns -1 and sets errno on I/O
 * failure; p is left consistent and may be retried. */
int flush(struct pipe *p);
```

The comment on the declaration is the contract; the code below is merely one
implementation of it. Callers compile against your sentence, not your body —
which makes the interface comment the most load-bearing prose in the system
and the right place for the whole maintenance budget. The amendment from the
austerity desk stands: preconditions or silence. "Assumes the lock is held"
prevents a category of bug; "loops over the array" prevents nothing.

## Rule 18. Sign the cliffs; skip the coastline. *(comments)*

Sin — the travelogue:

```c
/* This module manages the free list. First we initialize the
 * array, then we link the slots, then during operation we pop
 * from the head and push to the head, and on shutdown we walk
 * the list freeing each slot... */
```

Obedience — the warning sign, at the exact line:

```c
slots[n] = s;   /* slots stays sorted by fd; lookup() bisects it */
```

Internals stay undocumented — the reader who needs them has the source, which
is always current, being the thing itself, and prose that narrates the
implementation freezes the very thing that most needs to stay free to change.
The one exception is the boundary of surprise: the fact a maintainer would
never guess — the array that must stay sorted, the field that aliases
another — written precisely at the line it governs, and nowhere else. A
warning sign at the cliff, not a travelogue of the coastline. The corollary
about position: a comment three lines above the code it describes is already
lying about something, because locality is a claim.

Three things that are never worth the debt: history ("previously this used a
linked list") — the past has a whole subsystem, git, staffed and indexed, and
a comment holding history is a tombstone; aspirations ("TODO: handle
overflow") — a TODO in code is a tracked item that escaped tracking, so file
it where undone work is counted; and the implementation narrative above,
which you have already been warned off.

## Rule 19. A change to behavior changes its documentation in the same commit. *(all prose)*

Sin — a merged diff:

```
 M  src/retry.c        (adds the --jitter flag)
```

and a review comment: "docs to follow in a separate PR."

Obedience — one diff:

```
 M  src/retry.c
 M  man/retry.1
 M  test/retry_examples.t
```

"Docs to follow" is where docs go to not exist; the follow-up commit has a
documented survival rate of nil. The mechanism matters here, not the
sentiment: when the doc can only change in the same commit, under the same
review, it cannot drift *separately* from the code — same diff, same
reviewer, same test run. A feature nobody could document in a sentence has,
more than once, turned out to be a feature nobody could defend; the doc is
the design review. Enforce this in review; better, enforce it in CI, which
can blush on your behalf.

---

# CHAPTER V — AN APPROACH TO STYLE

*One page. It earns it.*

## Rule 20. Place yourself in the background. *(all prose)*

Sin: `Whoever wrote this was careless; typical of the old networking code.`

Obedience: `This check was wrong for nine years; the test was wrong the same way, so nothing noticed.`

Blunt about code, silent about character. The obedient sentence is harsh and
correct: softening it into "an opportunity to improve historical correctness"
would not spare the original author, it would delete the lesson. But "whoever
wrote this was careless" is speculation, in the permanent record, about a
person who may have worked under constraints you cannot see from here. The
log is not the place to win an argument with a ghost — the blame layer is
`git blame`, and even that names lines, not character.

## Rule 21. One concept, one word, everywhere. *(all prose)*

Sin: a page that says *node*, *vertex*, *element*, and *item*, and means one
thing.

Obedience: the page says *node*, forty times if it must.

The thesaurus is where documentation goes to die, for three readers at once.
The human infers distinctions you never intended. The second-language reader —
by now the majority of programmers — pays for each synonym twice. And grep is
a reader too: the searcher who queries `vertex` finds half your document and
trusts all of it. Plain words travel; short words travel farther; one word
per concept arrives.

## Rule 22. Earn the aphorism. *(all prose)*

Sin — a review verdict, addressed to a junior engineer:

```
obviously wrong, revert
```

Obedience:

```
This reverts the change: Close now races the timer it started, and
the test only passed because the runner is single-core. Short
version for the log: don't signal a timer you might be freeing.
```

Terseness is a dialect of experts. The one-liner lands in this room because
forty years of context stand behind it; the junior who receives "obviously
wrong, revert" learns only fear. Default to the longer plain sentence, and
earn the aphorism — write it *after* the explanation it compresses, as the
obedient example does, so the expert gets the compression and the novice
gets the derivation.

And once per thousand pages, when a sentence can carry a chapter, let it.
The BUGS section of `tunefs(8)` ended: "You can tune a file system, but you
can't tune a fish." It survived decades of solemn committees because it was
placed with care — in BUGS, the one section already licensed for confession
and slouching, self-contained, load-bearing on nothing. A joke in the
SYNOPSIS is a bug; a joke in BUGS is a feature. One fish. Style is the sound
sense makes.

---

# APPENDIX A — THE SINS

*Fifteen named anti-patterns. Errors with names shame better than a
paragraph of theory; that is why the dangling participle never survived
being called one.*

**1. THE HOSTAGE NOTE.** `i++ /* increment i */`. A comment proving only that
the author was present at the keyboard. (v. Rule 16.)

**2. THE AFTERNOON.** "First I looked at X, then I noticed Y..." The author
narrating their day instead of stating their conclusion. Nobody cares about
your afternoon. (v. Rule 7.)

**3. THE UNFALSIFIABLE SUBJECT.** "cleanup," "various fixes,"
"improvements." A claim no diff can confirm or deny, therefore worthless as
a filter. (v. Rule 3.)

**4. THE TOMBSTONE.** The comment describing what the code used to do.
History belongs to the log; a comment holding history lies in the present
tense. (v. Rule 18.)

**5. THE APOLOGY TOUR.** "This is a bit hacky, sorry" — self-deprecation
standing where the actual constraint should be. Say why the hack is
necessary, or fix it. Shame is not documentation. (v. Rule 16.)

**6. THE GREENHOUSE.** The example that only grows in the author's
environment — invisible prerequisites, "assuming the setup from chapter 2."
It fails on the reader's machine and poisons the document's credit. (v. Rule
12.)

**7. THE ADJECTIVE STACK.** "Blazingly fast, lightweight, powerful" —
properties claimed in units that do not exist. Measurements have numbers;
the rest is weather. (v. Rule 10.)

**8. THE ECHO.** The commit body that recites the diff: "Renamed foo to bar,
updated callers." The reader has eyes. (v. Rule 5.)

**9. THE DOCS-TO-FOLLOW.** The behavior change merged on a promise of future
documentation. The follow-up has a documented survival rate of nil. (v. Rule
19.)

**10. THE LOAD-BEARING LINK.** "See #4127 for why." The why, outsourced to a
system with a different lifetime; when the tracker dies, the commit becomes
a locked box labeled "key elsewhere." (v. Rule 8.)

**11. THE THESAURUS.** Node, vertex, element, item — four terms, one
concept, zero grep. (v. Rule 21.)

**12. THE HEDGE.** "Should probably," "seems to," "I think this fixes." If
you verified it, say so plainly; if you didn't, say *that* plainly.
Uncertainty is honest; vagueness about your uncertainty is not. (v. Rule 3.)

**13. THE BADGE WALL.** Twelve shields announcing CI status, coverage, and
chat channels — the first screen spent proving the project is alive instead
of saying what it is. (v. Rules 10, 13.)

**14. THE ORPHANED WHY.** The constraint documented nowhere near the code it
constrains — the invariant in a wiki, the warning in a README, the cliff
sign filed in a drawer three buildings from the cliff. (v. Rules 15, 18.)

**15. THE CONFIDENT ESSAY.** Length worn as authority: a thousand words,
wrong in every paragraph. Length reads as diligence and is not. Style does
not save you; verification saves you. (v. Rules 3, 5.)

---

# APPENDIX B — THE CONFESSIONS

*Each rule's honest breaking point, from the authors. A rule book written by
people who never break the rules is written by people who never write. The
subtitle of this book is these nine entries.*

**Pike, against Rule 4 (effect over mechanism).** When the mechanism is a
landmine for the next person, name it in the subject even though the effect
is small. `runtime: don't use cgo in the signal handler` — the effect was a
rare crash fixed; the subject's job that day was to make the *pattern*
radioactive. Sometimes the subject is a warning label, not a summary.

**Kernighan, against Rule 11 (one document, one reader).** In a book,
deliberately. A book can braid reference and teaching because it has a spine
and an index — the reader can enter twice. The rule is really about
documents with one door.

**McIlroy, against Rule 12 (lead with the example).** When the concept is
dangerous half-understood. `rm` does not want an inviting example at the top
of the page. For sharp tools, preconditions before invitations — the reader
you hook is the reader you're responsible for.

**Thompson, against all of them.** In code written for myself alone. The
rules price the reader's time above the writer's; when the writer *is* the
reader, the price is wrong. The mistake is only forgetting which kind of
code you're in.

**Ritchie, against Rule 16 (comment what the code cannot say).** For the
reader-in-training. In teaching code, comments that narrate the obvious are
the point; the annotated program is a genre of its own, and the C book's
examples do it shamelessly. Pedagogy licenses what production forbids.

**Cox, against Rule 7 (conclusion first).** When the conclusion is
unbelievable without the journey. Some fixes are so strange the reader
rejects the summary until walked to it; those messages read like proofs
because the claim looked insane. The afternoon is still forbidden; the
*derivation* is not. The difference: a derivation could convince a stranger;
an afternoon only describes the author.

**Bernstein, narrowing Rule 14 (the honest BUGS section).** Not in
security-sensitive documentation. A published "this area is probably weak"
is a treasure map. Confess the deficiencies you'd bet on, or say nothing —
the credential is the confession's accuracy, not its existence.

**de Raadt, against Rule 20 (author in the background).** Every time the
background caused the bug. When code is wrong because a vendor lied or a
standard is malignant, say so, in the commit, with the vendor's name.
Posterity deserves the indictment; softening it would be deleting the
lesson.

**White, against Rule 21 (one concept, one word).** At the sentence where
the twelfth repetition would deafen the reader to the one that matters, the
word may rest. Even grep forgives a pronoun.

---

*The rules obey themselves where they can, and where they cannot, the record
says why. Omit needless words; the words that remain, make true; and of the
true words, keep the ones the reader cannot get anywhere else.*

---

# BUGS

This book states rules more confidently than their exceptions deserve;
Appendix B is the patch, applied by hand. Five of its twenty-two rules can be
enforced by machine; the other seventeen require a reviewer who has read
them, which is a dependency this book cannot declare. Chapter V claims to be
one page and is, by a generous compositor.

You can tune a style guide, but you can't tune a fish.

<!--
EDITORIAL (the judge). Winner: the Teacher's draft; its text is the base and
its voice governs throughout. Grafts from runners-up:
1. Preface: closing statements attributed by name (the Clerk).
2. Preface: Bernstein's four-check reviewer's checklist (the Auditor/the
   Clerk, per Round VII).
3. Chapter I intro: the filter principle — "each layer must add information,
   or be deleted" — adopted verbatim on the floor (the Clerk, per Round I).
4. Rule 11: the cost-shifting paragraph on brevity and verbosity (the
   Stylist).
5. BUGS: the book's own BUGS section, ending on the fish (the Stylist,
   lightly adapted).
No other text was altered.
-->
