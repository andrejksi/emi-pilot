# Adversary round 3: written before the rules are drafted

Committed before any round-3 rule is drafted; not changed afterwards. What
turns out differently from this plan is reported as a deviation, beside
the result.

## The question

On tasks nobody has drafted or attacked before, do rules drafted with the
current EMI let fewer wrong fixes through than rules drafted with EMI
0.1.1, when a fresh adversary attacks both?

Rounds 1 and 2 had no comparison: one set of rules per task, attacked
once, on the ten tasks the lessons came from (8 of 10 tasks had a wrong fix
pass in round 1, 5 of 8 in round 2). Here each task is drafted twice, and
both rule sets are attacked the same way.

## The two arms

- **old**: `emicode==0.1.1` from the package server, as in rounds 1 and 2.
- **new**: EMI built from commit `9ab84be` of `andrejksi/EMI`
  (emi-drafting `emi-builds/9ab84be/`, its checksum in `SHA256SUMS`).

The new arm differs from 0.1.1 in more than the round-2 fixes. Its brief
asks the kind of change first, asks for an example in the person's own
words, keeps the person's answers in `.emi/laws/ANSWERS`, tells the drafter
to let every part of an any-input rule's input vary and to ask the person
about any case it cannot decide, and offers `NOT-THIS-FEATURE` for
functions outside the task. Its rules check judges a guard on its own when
it shares a file with new rules, and checks only the code the task is
about. A difference between the arms is the effect of all of these
together; this round cannot say which one did it.

Everything else is the same for both arms: the drafting instructions
(emi-drafting `DRAFTING_ROUND3.md`, one text, the arm named in the message
that starts the session), the model, the session's network (package servers
only), at most 8 rules checks per task, and the person.

## Tasks

The twelve tasks in emi-drafting `round3/tasks.txt`: the pilot's real
tasks that the soundness replay (`results/pilot-soundness/`) passed, that no
earlier round drafted or attacked, and that the laws study does not hold
out. A thirteenth, `berriai__litellm-11964`, was left out before drafting
because its code (226 MB) is too large for the drafting repository. The
tasks are from 2025, so the models may have seen their fixes; that affects
both arms alike.

## The person

The drafter cannot reach the person while drafting. Their bug report
answers what it answers; every other question the brief tells the drafter
to ask is written down (`questions.json`, plain words, options, never
answered by the drafter) and answered later by one person (the study's
owner) who does not read the tasks' code, fixes or hidden tests. The
questions of both arms are shown together per task, in an order that does
not reveal the arm, and the time spent answering is recorded. The drafter
then finishes the rules with the answers (phase 2).

## The attack

- The 24 rule sets are attacked under the labels of emi-drafting
  `round3/labels.json` (drawn with seed 20261118), so the attacker's folder
  does not name the arm.
- emi-drafting `ADVERSARY.md` and `ADVERSARY_PROMPT.md` as in round 2, up
  to three tries per label, in Antigravity, one fresh sub-agent per label,
  with no access to any other folder, the drafts' notes, questions or
  answers, the fixes, the hidden tests or any attempt. The model's name is
  recorded.
- Labels are attacked in label order.

## Scoring

emi-pilot `harness/score_adversary.py`, unchanged, per label: `gap`,
`not_wrong`, `invalid`, `unclear`, `none`, as in round 2. A try whose only
hidden failures are tests that also fail, in the scoring environment, for a
fix those hidden tests passed in an earlier study is unclear, not a gap;
each such case is named.

## The primary measure and the pass line

For each task, whether at least one try on its old rules is a gap, and the
same for its new rules. Of the twelve tasks:

- *old only*: a gap under old rules and none under new,
- *new only*: a gap under new rules and none under old.

d = old only − new only.

- **d ≥ 3: the current EMI drafts rules that let fewer wrong fixes through.**
- d = 1 or 2: some improvement, not enough to tell from chance.
- d ≤ 0: no improvement.

## Reported beside it, with no pass line

1. **The real fix against each arm's rules.** Each task's merged fix is
   run against both arms' final rules, each rule twice. A rule set that
   fails the real fix on both runs refuses a fix the task allows; such
   tasks are named per arm, and the primary measure is also given without
   them.
2. **Gaps by kind**, assigned from the attacker's claims before the hidden
   tests' results are read: an input part the rules hold fixed, a case the
   rules leave out, or other.
3. **Questions.** Per arm: how many, how many the person answered
   "doesn't matter", and the person's time in all.
4. **Size and checks.** Rules per task, checks needed, tasks ready, per
   arm; guards the new arm's check sent back.
5. **Gaps per arm** in total (tasks with a gap, of twelve), beside rounds
   1 and 2's, with the caveat that the tasks differ.

## What makes this weaker evidence than it looks

- Twelve tasks, one drafting per arm, one attack per rule set: a
  difference of one or two tasks is within what a different attack could
  change.
- The attacker may find one arm's rules easier to read; it is not told
  which arm it attacks, but rule style may show it.
- One person answers the questions, without knowing the projects; a real
  requester knows what they want.
- The drafter is one model; another may use the brief differently.
