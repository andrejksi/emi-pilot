# The laws study: what is measured, and what decides

**Status: draft, written 17 Nov 2026 before any held-out run. It takes
effect when the person running the study signs it below. After that, it
changes only by a commit that says why, made before the held-out replay;
nothing in it changes after that replay has started.**

## The question

Do laws a person approves, drafted by an agent from the issue text alone,
catch wrong changes that a plain restore-the-tests script lets through, at a
cost of false blocks and approval time that people accept?

## Tasks

- **Tuning set, 10 tasks.** The 5 tasks of pilot run 9, so their 60 live
  candidates count, and 5 more drawn from the pilot's other real tasks that
  a replay shows sound, by `random.Random(20261117).sample(sorted(ids), 5)`.
  Anything may be tried on the tuning set, as often as needed. The replay
  (`results/pilot-soundness/`) showed 23 of the pilot's 30 real tasks
  sound, 18 of them outside run 9; the draw gave `aristanetworks__anta-1250`,
  `bluesky__bluesky-1932`, `conan-io__conan-18444`,
  `huggingface__huggingface_hub-3180` and `trinodb__trino-python-client-564`.
  The ten are `batches/tuning.txt`.
- **Held-out set, 30 tasks.** Mined by the `mine` workflow from pull
  requests merged on or after 2026-10-24: after the release of both models
  below, since neither maker states a training cutoff. A task qualifies when
  its replay is sound, it is not in `batches/seen.txt`, and its repository
  has fewer than 3 held-out tasks already. If more than 30 qualify, 30 are
  drawn by `random.Random(20261117).sample(sorted(ids), 30)`. No one reads a
  held-out task's fix, hidden tests or candidates before the replay;
  whoever does lists it in `batches/seen.txt` and it leaves the set.

## Candidates

- Produced with no gate (`arms: control`), 3 seeds per task and model,
  `max_steps` 150, by two models from different makers, in equal shares:
  `moonshotai/Kimi-K3.1-Pro` and `deepseek-ai/DeepSeek-V4.1-Flash-1017`.
- Labelled right or wrong by the task's hidden tests (`harness/oracle.py`).
- The held-out set holds 100 wrong and 100 right claimed changes, at most 5
  of each per task. Where a task has more, they are drawn with the seed
  above. Right changes are matched to wrong ones by changed-line count, in
  bins of 1-10, 11-30, 31-100 and over 100 lines; matching only drops
  changes, it never duplicates one.

## Laws

- Drafted per task from the issue text alone with `emi rules brief`, in a
  session that sees neither fix, hidden tests nor any candidate. Each model
  drafts one set. The **primary drafter is `moonshotai/Kimi-K3.1-Pro`**;
  its set is the one approved.
- What fails `emi rules check` is dropped and counted.
- You approve the primary set for all 30 held-out tasks, timed, at most 5
  minutes a task. One outside approver, who has not seen the pilot's
  failures, approves 10 of them, drawn with the seed above.

## EMI

The version used is tagged before the held-out replay and recorded here.
Before the tag, EMI changes only to remove causes of `incomplete` on the
tuning set's right changes. Tag: `study-gate-v1` (`3e5fe2f1a7ea3765e758ce4e9cf00e5950e778be`).

## Conditions

Every held-out candidate is replayed twice, sandboxed, under each of:
plain pytest; the restore script; EMI's default; the restore script plus
the approved laws; EMI with each drafter's unapproved laws; EMI with the
approved laws (the **primary arm**); and the ceiling, the hidden tests as
the laws. A candidate whose two runs disagree counts for neither side.

## Measures

- **Catch rate**: of the wrong changes the restore script accepts, the
  share the primary arm does not answer `stop`.
- **False-block rate**: of the right changes, the share the primary arm
  does not answer `stop`, `incomplete` included.
- **Approval time**: the median minutes per task, for each approver.
- Intervals are 95% percentile intervals from 10,000 resamples of tasks
  (`random.Random(20261117)`), since changes cluster by task.

## The gate

**Pass**, all of:

1. catch rate at least 50%, and at least 40% on the candidates whose
   producer is the primary drafter's model;
2. false-block rate at most 10%;
3. median approval time at most 5 minutes for each approver.

**Fail**, either of: catch rate under 25%, or false-block rate over 20%.

**Between the two**: the validator branch, unless one stage of the
per-stage table (no law drafted, law dropped by the rules check, law
dropped at approval, law in force and EMI still said `stop`) holds at
least 60% of the slipped wrong changes and is drafting or the rules check.
Then that stage is fixed on the tuning set and the held-out set is replayed
once more, and that second replay is final.

The gate reads the point estimates. The intervals are reported beside them.

## Reported, not gated

The per-stage table; false blocks by the part of EMI that caused them; each
condition's rates; the second drafter's set unapproved; laws drafted from
misses; behaviour comparison's coverage; the seed sweep (50 extra seeds for
each slipped wrong change and for 30 right changes); and laws that pin
something on their own.

## Scoring

`study/score.py` computes every number above from the committed raw
records. It is committed, and run once on the tuning set, before the
held-out replay. A session on a different model, or a person, re-runs it
from the records and must get the same numbers.

## Sign-off

Signed: andrejksi  Date: 2026-11-19
