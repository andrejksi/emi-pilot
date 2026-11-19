# Adversary Round 3 — Phase 1 Summary

Phase 1 of Adversary Round 3 (`andrejksi/emi-drafting` `drafts3/`, commit `bc8def0`) was published before answering questions or running the 24 Phase 2/3 adversary attacks. This note records what Phase 1 already shows without spending human review time on ~67–80 questions or additional paid adversary runs.

## Per-task Phase 1 output (`old` vs. `new` brief)

| Task | `old` Qs | `new` Qs | `old` `.py` files | `new` `.py` files |
|---|---:|---:|---:|---:|
| `aristanetworks__anta-1276` | 6 | 9 | 1 | 4 |
| `deshaw__pyflyby-391` | 1 | 3 | 2 | 2 |
| `googleapis__python-bigquery-2218` | 2 | 5 | 1 | 3 |
| `huggingface__huggingface_hub-3200` | 1 | 2 | 1 | 4 |
| `matchms__matchms-809` | 2 | 2 | 1 | 4 |
| `openmdao__openmdao-3543` | 0 | 3 | 0 | 4 |
| `pydap__pydap-519` | 4 | 9 | 1 | 3 |
| `pymc-devs__pymc-7809` | 2 | 5 | 1 | 3 |
| `tornadoweb__tornado-3521` | 3 | 4 | 1 | 4 |
| `tweag__fawltydeps-492` | 1 | _(on `claude/round3-new`)_ | 1 | _(on `claude/round3-new`)_ |
| `tweag__fawltydeps-495` | 3 | _(on `claude/round3-new`)_ | 1 | _(on `claude/round3-new`)_ |
| `yt-dlp__yt-dlp-13361` | 0 | _(on `claude/round3-new`)_ | 0 | _(on `claude/round3-new`)_ |
| **Shared 9-task merged total (`bc8def0`)** | **21 (2.33/task)** | **42 (4.67/task)** | **9 (1.00/task)** | **31 (3.44/task)** |
| **Full 12-task Phase 1 total (`0498a40`)** | **25 / 12 (2.08/task)** | **55 / 12 (4.58/task)** | **11 / 12** | **—** |

Brief size: `old` = 4,098 bytes; `new` = 6,476 bytes (+58%).

## Findings

1. **Question-load inflation (2.2x across all 12 tasks; 2.0x on the 9 merged tasks).** The newer `emi rules brief` more than doubled the number of questions per task (from 2.08 to 4.58 across all 12 tasks, peaking at 9 questions on both `anta-1276` and `pydap-519`) and more than tripled the number of drafted `.py` rule files per task on the 9 merged tasks (from 1.00 to 3.44). That directly threatens the 5-minute median human approval-time gate in `study/gate.md`.
2. **Environment note (`deshaw__pyflyby-391`).** `setup_task.py` installed pytest 8, while `pyflyby`'s own `pytest.ini` treats pytest 8's `py.path.local` deprecation warning as an error — preventing even `pyflyby`'s own tests from collecting (also explaining `pyflyby-391`'s `incomplete` in `run-08`).
3. **Why Round 3 Phase 2/3 was halted.** Round 3 tests *human-in-the-loop specification resistance against a worst-case adversary* on 12 tasks (`n = 12`, high variance, 80 questions to answer), whereas the primary unmeasured question for EMI is the **natural-distribution held-out gate** in `study/gate.md` (catch rate on real agent wrong changes, false-block rate on real right changes, and median approval time). Rather than investing more time in an adversarial-only A/B, Phase 1's free finding is recorded here and effort moves to `study/gate.md`.
