# Adversary round 2: what the drafting did differently from the plan

Written after the drafts were in, before the adversary's run. PREREG.md is
not changed; these are reported beside the result.

The drafter (one cloud session, emi-drafting `DRAFTING_ROUND2.md`) drafted
all ten tasks in one turn of 38 minutes: 103 steps, 100,261 output tokens,
$6.96 at list price. Every task was `ready` after one `emi rules check`.
Predictions: 67 entries, by kind C1 11, C2 20, C3 10, C4 8, C5 6, other 12.

## 1. The drafter wrote a fix for each task

By its own report, for each task it wrote a plausible fix in a scratch copy
of the project outside `work/`, ran its new rules against it, and committed
nothing from it. `DRAFTING_ROUND2.md` says the drafter never writes code
for the tasks. Effects:

- "Checks needed" (PREREG, measure 4) says nothing about drafting effort:
  the rules were worked out against the scratch fix before EMI saw them.
- The rules were tuned not to refuse the drafter's own fix, which may make
  rules that refuse a fix the task allows rarer than they would otherwise
  be. The replay against round 1's 13 hidden-pass tries is the check.
- The scratch fixes were not kept and cannot be inspected.

## 2. Guards moved where EMI does not try stand-ins on them

For markdownify, narwhals and eodag, guards were moved into files that also
hold new-behaviour rules. For bluesky and eodag, round-1 rules that had
been added only to satisfy the checker were dropped; their guards from the
task text are kept, inside the new rules (bluesky) or moved unchanged
(eodag).

EMI 0.1.1 tries stand-ins per file and sends a file back only when every
rule in it still passes under a stand-in. A new-behaviour rule fails on
the starting code under any stand-in, so a guard in the same file is never
tried on its own, and the check does not say so. These guards may pin
nothing; the attack shows whether that matters. It is also a gap in EMI,
reported to EMI separately.

## 3. The fixed-example remark

`example_only.txt` was saved from the final rules (each task's `first/`
and `checked/` are identical), yet remarks still fire for anta (2), bluesky
(1), conan (2), eodag (2), huggingface_hub (1) and trino (1). The drafter
reports 7 answered with a rule and 2 with a reason. The rules it counts as
answers sit in other files or were there before the remark was recorded,
so an answer cannot be told apart from a rule written anyway. This is the
known flaw of the prototype: it looks at one file at a time.

## 4. Rules the drafter changed or flagged

- huggingface_hub: two round-1 rules were wrong. Their subprocess inherited
  `HUGGINGFACE_CO_STAGING=1` from the project's pytest settings and failed
  even on a correct fix. The variable is now removed for the subprocess and
  the assertions are unchanged. Round 1's huggingface_hub result is read
  with this in mind.
- anta: the rules assume Dps numbers 1–8191, which the task does not state.
- narwhals: a negative index must be refused. The drafter reads this in the
  task's interface; the simplest fix fails it.

Each is named for a person to judge, alongside the replay's result.

## 5. What was and was not checked about access

- The session's usage record counts 0 web searches and 0 web fetches by the
  provider.
- Its environment allowed package servers only.
- Its transcript was not read in full. Whether it fetched a task's project
  from a package server, which the instructions forbid, is not checked.
- emi-drafting holds no fixes or hidden tests (`tasks/<task>/` has the code
  and `task.json` only).
