# Pilot results

Raw records of pilot runs, copied from each run's `pilot-results` artifact so
they outlive GitHub's artifact expiry. Each run directory holds `table.md`
(and, for replays, `tasks.md`) and `runs/<task>.<arm>.<which>/` with the
run's `run.json`, its final `candidate.diff`, EMI's receipts, and the hidden
tests' verdict in `oracle.json`.

| Run | What | Workflow run | EMI |
|---|---|---|---|
| `run-08` | replay of the fixed changes (`gold`, `gold-with-tests`, `nothing`) on the 30 real tasks, every arm: 180 runs | [43471967610](https://github.com/andrejksi/emi-pilot/actions/runs/43471967610) | 0.1.1 |
| `run-09` | live runs, `deepseek-ai/DeepSeek-V4.1-Flash-1017`, 5 tasks x 4 arms x 3 seeds: 60 runs | [43479164382](https://github.com/andrejksi/emi-pilot/actions/runs/43479164382) | 0.1.1 |
| `rerun-2026-11-18` | the drafting study's drafts checked again on EMI with the plan's phases 1 to 3 | see its README | claude/confident-johnson-zcpmkk 9d727d1 |
| `adversary-2026-11-18` | an agent writing wrong fixes that pass the drafted rules, scored against the rules, the existing tests and the hidden tests | see its README | none (plain pytest) |
| `rivals-2026-11-18` | the two wrong attempts that passed both checkers, run on the drafted rules and side by side with the passing attempts on inputs the rules do not name | see its README | none (plain pytest) |
| `adversary-round2` | round 2 of the adversary: rules strengthened with a lesson file, predictions and a fixed-example remark, attacked afresh; `PREREG.md` was committed before drafting | see its `PREREG.md` | 0.1.1 (drafting); none (scoring) |
| `harvest-tuning` | live runs of both models, no checker, on the 10 tuning tasks, 3 seeds each: 50 attempts (10 refused by the provider), the inputs of the laws trial | see its README | none |
| `gate-replay-tuning` | double-replay of the 10 tuning tasks (120 candidates x 7 conditions x 2 runs) against `study/gate.md` | [44505647263](https://github.com/andrejksi/emi-pilot/actions/runs/44505647263) | `study-gate-v1` (`fc602d2`) |
| `gate-replay-heldout` | double-replay of the 28 clean held-out tasks (165 candidates x 8 conditions x 2 runs) against `study/gate.md` (`replays.jsonl`, `score.json`, `score.md`, `oracles/`) | [44571822516](https://github.com/andrejksi/emi-pilot/actions/runs/44571822516) | `study-gate-v1` (`fc602d2`) |

Run 8 predates the src-layout fix (c674a06): both huggingface_hub tasks
failed their gold replay there because every run tested the baseline's
code. Read its `tasks.md` with that in mind.
