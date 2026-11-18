# EMI bug audit, 18 Nov 2026

Whether the bugs on a "fix before any big benchmark" list are still in EMI,
checked on EMI `andrejksi/EMI` at 9ab84be (release build), each on a small
project made by these scripts. `lib.sh` lays a project out (a `calc.py`, its
tests, `.venv` linked from a venv with pytest, coverage and hypothesis) and
runs `emi done`; `scen.sh NAME` runs one case. Paths in `lib.sh` point at
the session's scratchpad: change `S` and `EMI` to rerun.

| Item | Result | Case |
|---|---|---|
| a rule file named like a project test | no crash, `stop` | `scen.sh clash` |
| a plugin loaded by `addopts = -p` | no crash, `stop` | `scen.sh plugin` |
| a plugin loaded by `pytest_plugins` | no crash, `stop` | `scen.sh plugins_var` |
| a test file renamed | no crash; `ask_person` (the old file counts as deleted, is put back and passes) | `ren2.sh` |
| a test function renamed in an old file | `ask_person` (old test changed) | `scen.sh renamed_fn` |
| 30 one-second tests | 33 s, `stop` | `scen.sh slow` |
| Hypothesis cache in the project | none written | `scen.sh hyp` |
| `addopts = -qq --tb=no -x` | `stop` | `scen.sh quiet` |
| a rule that runs no inputs (`Phase.explicit` only, empty parametrize, `skip`) | `rules check` sends it back as skipped; `emi done` counts it `pending`, not holding | `zero.sh`, `zero2.sh` |
| a rule whose inputs are all `assume`d away | fails (Hypothesis health check) | `zero.sh` |
| git settings seen by a test | no `GIT_*` variables, no address rewriting, no user config; **the machine-wide `/etc/gitconfig` is read** | `gitcfg.sh` (as rules, so each probe's outcome is shown) |
| what the agent is told | a failing test quotes its assertion and values; **a failing rule quotes its input but not the failing line** | `lawfail.sh` |

Found on the way: with no `.gitignore` for `__pycache__`, `emi done` lists
`__pycache__/calc.cpython-313.pyc` as a changed file that is "not Python"
(a note; no decision changes). `EXPECTED-CHANGES` is read only by
`emi rules check` (shown to the person); `emi done` asks a person about
every changed old test whether listed or not.
