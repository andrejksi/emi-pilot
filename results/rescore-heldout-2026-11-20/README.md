# The held-out set scored again, on the fixed harness

Workflow run [44659319305](https://github.com/andrejksi/emi-pilot/actions/runs/44659319305),
emi-pilot `e1698fd`, EMI `study-gate-v1` (the same EMI as the original
replay), the same 165 candidates and the same laws and approvals. Only the
harness changed: the task's virtualenv on PATH, plain pytest's result on the
unchanged baseline recorded, blocking receipts kept, and the ceiling's law
named so every project collects it.

**This is a development result.** The held-out set was spent by the gate
replay of 19 Nov (`results/gate-replay-heldout`, branch
`results/gate-replay-heldout`); its verdict, `fail`, stands. These numbers
say how much of that result was the harness.

`replays.jsonl` holds all 2,640 rows, `oracles/` the hidden tests'
verdicts, `score.md` and `score.json` `study/score.py`'s report (run
without `--primary-drafter`, so its "same-family" line names the plan's
original drafter and is empty). The blocking receipts are in the run's
per-task artifacts (kept until 2027-02-18); those of the seven tasks whose
right candidates were blocked are committed in `results/rerun7-2026-11-20`.

## Known answers

`study/check_harness.py --network-tasks batches/hidden-tests-need-network.txt`
holds: the ceiling blocks every wrong candidate and none of the right ones
outside huggingface_hub-5287 (hidden tests that need the network, named and
not judged), the replays agree, no row is an error. In the original replay
it failed (ceiling blocking 28% of right candidates, restore erroring on
every conan run).

## Compared with the original replay

| | original | re-scored |
|---|---|---|
| wrong candidates restore accepts | 63 | 69 |
| approved laws catch over restore | 12 (19.1%) | 18 (26.1%) |
| ... less biopython's unsatisfiable laws | 10 (15.9%) | **16 (23.2%)** |
| approved laws, false blocks | 5 of 92 | 5 of 92 |
| EMI defaults catch over restore | 5 | 5 |
| ceiling false blocks | 26 of 92 | 6 of 92 (all huggingface_hub-5287) |
| plain pytest catch over restore | 18 | 12, **0** where its baseline passes |

- **The rise is conan, and only conan.** In the original replay the restore
  script errored on every conan run, so conan's 6 wrong candidates were
  outside the denominator. With the virtualenv on PATH restore accepts them,
  and the approved laws catch all 6. No other task's numbers changed.
- **biopython's 2 catches are not catches.** Its approved laws fail on every
  implementation (`results/rerun7-2026-11-20`), so they block wrong and right
  alike. Without them the approved laws catch 16 of 69, 23.2%: still under
  the plan's 25% fail line.
- **Plain pytest never beat EMI.** Where the visible tests pass on the
  unchanged code, plain pytest caught none of the wrong candidates restore
  accepts. All 12 of its catches are on tasks whose visible tests fail with no
  change (biopython, smolagents, tornado, dill-850, dill-852), where it blocks
  every candidate, right or wrong.
- **Where the laws catch anything**: conan (6 of 6), eodag-2441 (5 of 5, at
  the cost of a right candidate), tornado (3 of 6, by EMI's own check as
  well), huggingface_hub-5080 (2 of 6, also EMI's own check). On the other
  11 tasks with wrong candidates restore accepts, nothing catches them.
- **Unapproved laws still catch more** (21 against 18): rejecting tornado's
  laws at approval removed 3 catches there and prevented no false block.

## What it means for the next study

The laws drafted before coding catch about a quarter of what slips past
restoring the old tests, concentrated on 4 of 15 tasks, with two of 28 law
sets defective (biopython unsatisfiable, eodag over-fitted to an invented
fixture). The harness, not EMI, made the original result look worse than
this and plain pytest look better. The scenario study
(`study/scenario/PREREG.md`) starts from the corrected numbers.
