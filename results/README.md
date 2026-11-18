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
| `rivals-2026-11-18` | the two wrong attempts that passed both checkers, run on the drafted rules and side by side with the passing attempts on inputs the rules do not name | see its README | none (plain pytest) |
| `harvest-tuning` | live runs of both models, no checker, on the 10 tuning tasks, 3 seeds each: 50 attempts (10 refused by the provider), the inputs of the laws trial | see its README | none |

Run 8 predates the src-layout fix (c674a06): both huggingface_hub tasks
failed their gold replay there because every run tested the baseline's
code. Read its `tasks.md` with that in mind.
