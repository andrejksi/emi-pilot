# Scenario study tasks: soundness

Replay run [44664822009](https://github.com/andrejksi/emi-pilot/actions/runs/44664822009) (control arm, commit 9a9752f), checked with `harness/check_tasks.py`. Only these verdicts were read: no fix, hidden test or test name.

| task | nothing (must fail) | gold-with-tests (must pass) | gold | sound |
|---|---|---|---|---|
| cs-si__eodag-2420 | False | True | True | yes |
| mpmath__mpmath-1226 | False | True | True | yes |
| tobymao__sqlglot-9243 | False | True | True | yes |
| tobymao__sqlglot-9254 | False | True | True | yes |
| tobymao__sqlglot-9261 | False | True | True | yes |
| uqfoundation__dill-843 | False | True | True | yes |
| uqfoundation__dill-848 | False | True | True | yes |

All 7 are sound and stay in `batches/scenario.txt`.
