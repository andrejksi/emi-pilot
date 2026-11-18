# The drafting study, rerun on EMI with the improvement plan's phases 1 to 3

The ten tasks' drafted rules from the drafting study
(`andrejksi/emi-drafting`, `drafts/<task>/`), checked again by
`emi rules check --format json` with the command the study's instructions
fix (no raised budget), on EMI built from
`andrejksi/emi` `claude/confident-johnson-zcpmkk` at 9d727d1 (release
build). Nobody answered the brief's questions this time either: these are
the study's own drafts, unchanged.

For each task, `run.sh` checks:

- **first**: the draft before any check (`first/`);
- **final**: the last draft (`checked/`, else `last/`); narwhals has no
  later draft than its first, so it has no final row;
- **final-again**: the final draft once more, with the state directory of
  the run before kept, so stand-in results are read rather than run.

Each check starts from an empty state directory except `final-again`.
`table.md` (from `summary.py`) sets each beside the study's own check of
the same draft (its first and last check files). `out/` holds every JSON
answer and `times.tsv` (task, version, exit, seconds).

`out/md-fix.{1,2,3}.json` are markdownify's final drafts checked three
times with results kept, on e754457 (a debug build), which stops a kept result
spending the run budget. Before that commit the second check left the
same 26 stand-ins untried as the first.

## Results

| | study | rerun |
|---|---|---|
| final drafts ready under the fixed command | 6 of 10 | 8 of 10; 9 with a second check (markdownify, at e754457) |
| first drafts ready | 4 of 10 | 7 of 10 |
| slowest check | 4,398 s (bluesky, budget 450) | 34 s (eodag) |
| every check | 14 s to 4,398 s, for the four checks whose time was written down | 4 s to 34 s |

- **bluesky** stays not ready, for one reason in the area its rules are
  about (`plans.py::_check_detectors_type_input` can be replaced by a
  trivial body without any rule failing). In the study it was about 70
  findings, in vendored code and the scan engine.
- **eodag** and **narwhals** become ready: their remaining findings were all
  outside the code the rules import (progress bars, order and retry,
  other backends, `@overload` stubs).
- **meltano**'s first draft becomes ready: EMI's own runs no longer create
  the Hypothesis cache that broke the tests' collection.
- **trino**'s first draft becomes ready, and that is a cost. The study's
  first check found that `ClientSession.__init__` in `trino/client.py`
  could do nothing without any guard failing, and the drafter added a guard
  the task text supports ("unchanged from the previous version"). That
  function is outside the area now (the rules import `trino.dbapi`, not
  `trino.client`), so the rerun only notes it. The overnight sweep or
  `laws.area` would bring it back.
- **Remarks** (notes only):
  - "already asserted" found the markdownify guard repeated at
    `tests/test_conversions.py:92`, but not the more-itertools or trino
    repeats, which are written differently;
  - "accepts any error" fired on narwhals' two out-of-bounds rules;
  - "speaks of any input" fired twice on bluesky;
  - "old tests import what its new rules are about" fired on 7 tasks and
    named 38 files on anta and 65 on conan: on a big project it is too broad
    to help.
- **Kept results** save little here (final-again: 5 to 29 s against 7 to
  34 s), because with the narrowed area most of a check is running the rules,
  not the stand-ins.

Timings are from one run each on a 4-core container; the tasks from meltano on ran while a build and EMI's fast checks
were running beside them.
