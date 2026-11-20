# The scenario study: what is measured, and what decides

**Status: DRAFT, 20 Nov 2026. Not signed. It takes effect when the person
running the study signs it below, after the plan review of
`study/EVAL_CHECKLIST.md` stage 1. The decisions marked OPEN must be made
before signing.**

## The question

On tasks nobody has used, does one public scenario per task, written from
the task text before any candidate exists, catch wrong patches that EMI's
completion check lets through, without flagging right ones?

A scenario is an ordinary test in the project's own runner that records
one named observation, stated in one sentence a person can read ("calls
`download_all` twice and counts the requests"), instead of asserting it.
It is the cheapest form of the disagreement idea: one candidate, one
well-chosen observation, no rival implementations. Rivals and generated
alternatives are a later study, run only if this one leaves a gap
(see "What a result leads to").

## What this study is not

- Not a study of people. The person's answers are simulated from the
  known truth (`study/EVAL_CHECKLIST.md`, the simulated answerer). Results
  are an upper bound: a person who always knows the right answer.
- Not a test of laws drafted before coding. That study ended (`gate.md`,
  failed at 19.1% catch).

## Tasks

- **Development set:** the 28 tasks of `batches/heldout.txt`. They are
  spent; anything may be tried on them. The scenario runner is built and
  debugged here.
- **Study set:** about 30 tasks from the `mine` workflow run of 20 Nov
  2026 (since 2026-10-24, the pilot's repositories, at most 3 per
  repository, tasks already under `tasks/` skipped), each sound by
  `harness/check_tasks.py`, none in `batches/seen.txt`. If more than 30
  qualify, 30 are drawn by `random.Random(20261120).sample(sorted(ids), 30)`.
  Their task text includes the issue's discussion before the fix was opened.
- **Rehearsal:** 4 tasks of the study set, drawn first with the same seed,
  go through every step before the rest. They count in the study only if
  nothing changed after the rehearsal; otherwise they join the development
  set and are replaced from the remaining qualified tasks.

## Candidates

- Scripted and headless (`harness/agent.py`, `chat` backend), arm
  `control` (no gate), 3 seeds per task and model, `max_steps` 150. Each
  run commits its transcript, step count, tokens and model id.
- **OPEN:** the two models, from different makers, their endpoint, and the
  `MODEL_API_KEY` secret. Changing either after signing is an amendment.
- Each candidate is labelled right or wrong by the task's hidden tests
  (`harness/oracle.py`).
- Outcome mix: if the rehearsal's tasks are mostly all-right or all-wrong
  (more than a third either way), the starting conditions are fixed
  before the rest is harvested, and the change is recorded.

## Scenarios

- Written by a scripted agent per task, from the task text and the
  repository at the baseline only: no fix, no hidden test, no candidate,
  no label. One scenario per task, at most 3 observations.
- **Admitted** when, at the baseline, it runs twice under the pins with the
  same observation and it calls at least one public name the task text
  names. A scenario that patches or reads a private name (`_x`) of the
  project is sent back to its author once, then counted as not admitted.
- Not admitted, or crashing at the baseline: counted, never dropped from
  the denominator. Reported as reach.

## The simulated answerer

Code in the harness, never an agent: it runs the task's merged fix on the
scenario and records the merged fix's observation. For each candidate:

- candidate's observation **equals** the merged fix's: no finding;
- **differs**: a finding, answered "should be the merged fix's";
- the merged fix's observation is not the same on two runs: "either", no
  finding.

No agent that writes scenarios or candidates can read what it runs.

## Conditions

Every candidate is replayed twice, sandboxed:

- **A**: EMI's completion check, defaults (`emi_default`), at the EMI
  commit tagged before the study.
- **B**: A, and the scenario's finding: B blocks a candidate A blocks, or
  one with a finding.

A candidate whose two runs disagree counts for neither side.

## Measures

- **Catch over A**: of the wrong candidates A answers `stop` to, the share
  with a finding.
- **False flags**: of the right candidates A answers `stop` to, the share
  with a finding.
- **Reach**: the share of tasks whose scenario was admitted and executed
  a line the merged fix changes.
- **Cost**: findings per task.
- Intervals: 95% percentile intervals from 10,000 resamples of tasks
  (`random.Random(20261120)`).

## The decision

**OPEN** (the numbers below are proposed): pass when catch over A is at
least 30% and false flags at most 10%; fail when catch over A is under
15% or false flags over 20%. Between: no claim, and the per-task table is
read for whether reach or the scenarios' choice of observation lost the
catches.

The gate reads the point estimates. The intervals are reported beside them.

## What a result leads to

- **Pass**: a live phase on the same tasks: the agent gets B's finding as a
  repair round, and the patch that lands is judged by the hidden tests
  (wrong patches repaired, right patches made worse). Its plan is written
  and signed before it runs. Then: a study adding rivals and alternatives
  at the same budget, to learn whether they catch what one scenario
  misses.
- **Fail with reach under half**: the bottleneck is reaching the code.
  Decide whether to invest in scenario writing (fixtures, fake servers) or
  to stop.
- **Fail with reach over half**: scenarios do not add enough. EMI takes the
  validator branch of the November plan.

## Before the run

`study/EVAL_CHECKLIST.md`, all four stages. `study/check_harness.py` exits
0 on the development set's replay first.

## Sign-off

Signed: ______  Date: ______
