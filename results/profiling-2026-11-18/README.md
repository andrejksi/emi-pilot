# Where EMI 0.1.1's checks spend their time (18 Nov 2026)

Measured on a 4-core cloud container without bubblewrap. Each check ran
under `strace -f -e trace=execve,exit_group`; `timeline.py` turns a trace
into what EMI started, for how long, and how busy the machine was. One
stand-in run was sampled with py-spy and `-X importtime`.

## `emi rules check`, bluesky-1932, the drafted laws

| Budget | Wall | Test runs | A test process running | At once, while any runs |
|---|---|---|---|---|
| 48 (default) | 56 s | 60 | 85% of the time | 2.1 of 4 |
| 450 (stopped after 17 min) | 1026 s so far | 219 finished | 10% of the time | |

The drafting session's 450-budget check took 4398 s. The cause: stand-ins of
`RunEngine` code (`self._blocking_event.set()` replaced by `return None`,
`raise NotImplementedError`, ...) make the laws hang, and each hang is killed
only at the proving runs' 600 s limit (`emi-python/src/proving.rs`). Stand-ins
run in chunks of 4 that wait for their slowest member
(`run_trials`, `emi-python/src/proving/rules.rs`), so a hang idles the other
workers. `hangs.log` names the hung stand-ins.

## One stand-in run (bluesky laws, about 1.2 s)

| Part | Time |
|---|---|
| Python start | 0.01 s |
| pytest and Hypothesis imports | 0.35 s |
| bluesky's third-party imports (numpy, ophyd, ...) | 0.53 s |
| bluesky's own modules | 0.04 s |
| pytest's `gc_collect_harder` at the end | about 0.15 s (11% of samples) |
| the tests | 0.015 s |

py-spy over five runs: 56% importing during collection, 19% importing
before it, 5% plugin discovery, 1% running tests.

## `emi done`, anta-1250, a saved attempt with no laws

| | Wall | Test processes | At once, while any runs |
|---|---|---|---|
| first check (no saved baseline) | 36.9 s | 20 | 1.2 |
| again (baseline saved) | 24.1 s | 13 | 1.0 |

The warm check runs, one after another: a listing (1.9 s), the run (2.0 s),
two more listings (1.9 s, 1.8 s), five reruns of the failing tests at the
candidate and the baseline (about 1.7 s each), and a coverage run (5.2 s).
EMI's own work (git, tree copies, hashing the linked environment) is under
2 s of either check.
