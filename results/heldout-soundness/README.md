# Held-out tasks: soundness

Replay run 44064810847 (control arm, commit bdab345), checked with
`harness/check_tasks.py`. Only these verdicts were read: no fix, hidden
test or test name.

| task | nothing (must fail) | gold-with-tests (must pass) | gold | sound |
|---|---|---|---|---|
| conan-io__conan-19649 | False | True | True | yes |
| cs-si__eodag-2435 | False | True | True | yes |
| cs-si__eodag-2441 | False | True | True | yes |
| huggingface__huggingface_hub-5080 | False | True | True | yes |

Replay run 44070548671 (commit 063e270):

| task | nothing (must fail) | gold-with-tests (must pass) | gold | sound |
|---|---|---|---|---|
| tornadoweb__tornado-3880 | False | True | True | yes |
