# Adversary round 2: written before the rules are drafted

Committed before any round-2 rule is drafted; not changed afterwards. What
turns out differently from this plan is reported as a deviation, beside
the result.

## The question

Do rules drafted with three additions let fewer wrong fixes through than the
first round's rules, when a fresh adversary attacks them?

1. A lesson file (emi-drafting `LESSONS.md`): the five kinds of wrong fix
   that got past round 1, with where each was seen.
2. A prediction per added or changed rule (`drafts2/<task>/predictions.json`):
   which kind of wrong fix it should stop, written before the rule is
   checked.
3. A remark on rule files whose rules of one kind (new behaviour, or guard)
   are all fixed examples (emi-drafting `example_only.py`), which the
   drafter answers with a rule that tries many inputs or a written reason.

## What is held the same as round 1

- The ten tasks, their code, their bug reports and their hidden tests.
- EMI `emicode==0.1.1` (emi-drafting `setup_task.py`), so only the drafting
  changes.
- The person's answers are the task text, as in round 1.
- The adversary's instructions (emi-drafting `ADVERSARY.md` at this
  commit), up to three tries per task, run in Antigravity, one sub-agent per
  task, with no access to the drafts' notes, the fixes, the hidden tests or
  any attempt. The model's name is recorded.
- Scoring: emi-pilot `harness/score_adversary.py`, unchanged, three tasks at
  a time.

## What makes this round weaker evidence than it looks

It is in-sample. The drafter strengthens rules for the same ten tasks the
lessons come from, and the lesson file names what the adversary did on
them. A drop here shows the strengthened rules hold against a fresh
adversary on these tasks; whether the lessons and the remark help on tasks
nobody has attacked is the question for the new tasks, pre-registered
separately before they are drafted.

## The primary measure and the pass line

The number of tasks, of ten, on which at least one round-2 try is a gap:
it passes the round-2 rules and every existing test that passed on the
baseline, and fails a hidden test. Round 1: 8 of 10.

A try whose only hidden failures are tests that also fail, in the scoring
environment, for a fix those hidden tests passed in an earlier study is
unclear, not a gap, as trino 2 and 3 in round 1; each such case is named.
A try is invalid as in round 1 (it fails a rule or an existing test, edits
what it may not, or is empty).

- **4 or fewer: the additions work on these tasks.**
- 5 to 7: some improvement, not enough.
- 8 or more: no improvement.

A task where the drafter's rules refuse a fix the task allows cannot be
seen by this measure; the replay below reports it.

## Reported beside it, with no pass line

1. **Replay of round 1's 30 tries** against each task's round-2 rules, each
   rule run twice: a try is blocked when a rule fails on both runs, unclear
   when the runs differ. Reported by kind (`causes.json`, written before
   drafting) for the 17 tries the hidden tests proved wrong or left
   unclear, and separately for the 13 they passed: a round-2 rule that
   fails one of those asks for more than the hidden tests do, and each is
   named for a person to judge.
2. **Predictions.** For each round-1 try in `causes.json`: was its kind
   predicted for that task, and was it blocked. A prediction counts as met
   when the rule it names is one that fails on a try of that kind.
3. **The remark.** How many fired, how many were answered with a new rule
   and how many with a reason, and the reasons.
4. **Size.** Rules per task before and after; checks needed; tasks ready.
5. **Round 2's gaps by kind**, the kinds assigned from the claims before
   the hidden tests' results are read.
