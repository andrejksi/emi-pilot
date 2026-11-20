# Eval checklist: before a number counts

Every study in this repository goes through these four stages in order. A
result from a run that skipped one is a development result, labelled so,
never a gate result. The stages exist because each one would have caught a
flaw that cost an earlier study its answer; the flaw is named beside each
item.

The plan (`PREREG.md` or `gate.md`) says which items apply. An item left
out is left out in writing, with the reason, before the plan is signed.

## Stage 1: the plan is reviewed before it is signed

- [ ] **Every departure from real use is listed**, each marked *changes the
      question* or *does not*, with why. Real use means: an agent with the
      whole repository, its tests, package servers and the task's
      discussion; a person who knows the project answering its questions;
      timing that a clock records.
      *(Laws study: the issue text stood in for the person's answers, and
      nobody marked that this turned "laws a person approves" into "laws an
      agent drafts from the issue".)*
- [ ] **Someone other than the author reads the plan for ways it could go
      wrong in both directions**: ways it could flatter EMI, and ways it
      could sink it for reasons that are not EMI (too little context,
      tasks too hard, a broken harness). Each point gets an answer before
      signing. *(The November review looked for ways the study could
      flatter EMI; none looked for an eval too unrealistic to pass.)*
- [ ] **Each agent's starting conditions are written down once** and used
      for every agent in the study (candidate writers, drafters, scenario
      authors): the repository and its tests, the network, the step budget,
      the files given (CONTRIBUTING, AGENTS.md), and the task text, which
      for tasks mined since #27 includes the issue's discussion before the
      fix was opened (`harness/mine_prs.py`, `format_problem_statement`).
      *(Held-out candidates were written from the issue body alone.)*
- [ ] **Models, producers and drafters are named, and changing one means
      amending the plan before the run.** *(Both models were swapped after
      signing.)*
- [ ] **Every approver is recruited before signing**, or the criterion
      that needs them is dropped in writing. *(The outside approver never
      took part.)*
- [ ] **What a pass and a fail each lead to is written in the plan.**

## Stage 2: the harness gives its known answers

Run on the tuning set before any held-out run, and again on every replay:

- [ ] `harness/check_tasks.py`: each task's `nothing` fails the oracle and
      its `gold-with-tests` passes.
- [ ] `study/check_harness.py --replays <replays.jsonl>` exits 0:
  - the ceiling (hidden tests as laws) blocks every wrong candidate and at
    most 2% of right ones. *(The held-out ceiling blocked 28% of right
    candidates on five tasks; the tuning ceiling caught 0%.)*
  - the two replays of each candidate agree;
  - no row is an error. *(The restore condition errored on every conan
    run, unreported.)*
- [ ] Its warnings are read and answered in writing:
  - **pytest_baseline**: plain pytest is run once on the unchanged baseline
    (`replay_gate.py` records it as `baseline`). Where the visible tests
    already fail, plain pytest's blocks are not catches. *(isort's visible
    tests failed with no change because the task's virtualenv was not on
    PATH; tornado's fail outside its own runner. Both looked like 6 of 6
    catches.)*
  - **unexplained**: every EMI block carries `why`, the receipt's own
    reason, and blocking receipts are kept under `receipts/`. *(Five
    false blocks and the whole ceiling problem were recorded only as a
    table row, `shows_nothing`, which covers six different facts.)*
  - **outcome_mix**: at most a third of tasks have only right, or only
    wrong, candidates. *(9 of 28 tasks all wrong and 12 all right left 7
    tasks that could show a checker telling right from wrong.)*
- [ ] **Planted wrong patches**: a few patches with a known defect go
      through the pipeline beside the real candidates and come out labelled
      wrong by the oracle and blocked by the ceiling.

## Stage 3: a rehearsal on three to five tasks

The full procedure, end to end, on a few tasks drawn by the plan's seed,
before the rest:

- [ ] **The outcome mix is checked first.** If more than a third of the
      rehearsal tasks come out all right or all wrong, the agents' starting
      conditions or the task filter are fixed before harvesting the rest.
- [ ] **Every run is scripted and headless**, and commits its transcript,
      step count, tokens and model id. Interactive sessions do not produce
      study candidates. *(Held-out `run.json` files hold none of these.)*
- [ ] **Timings are recorded by the tool**, per task, never typed in.
      *(Every approval reads 2.3 minutes.)*
- [ ] **For probes and scenarios: they reach the changed code**, and the
      share that could not run is reported.
- [ ] Each fix made after the rehearsal is logged as a deviation with its
      date. The rehearsal's tasks then join the tuning set.

## Stage 4: the full run

- [ ] **Blindness is a property of the workspace, not an instruction.** An
      author of laws, scenarios, alternatives or questions works from an
      export that holds no fix, hidden test, candidate verdict or label.
      Anyone who has seen a label does not author. *(The rival arm's
      alternatives were written knowing which candidates were wrong; their
      `alt_right` was declared, not measured.)*
- [ ] **Labels are measured, never declared**: every alternative or planted
      patch is run against the hidden tests like a candidate.
- [ ] **Setup does not change between the rehearsal and the run.**
- [ ] **The workflow commits its raw output with the run id**: rows,
      oracle verdicts and kept receipts. A number that is not committed does
      not count. *(Held-out results sat in an Actions artifact.)*
- [ ] **Scores are recomputed from the committed records** by a second
      pass, and must match.
- [ ] **Wrong candidates are sorted by a blind labeller** reading only the
      task text: *contradicts the task* / *a choice the task left open* /
      *a test detail (a name, a message)*. Catch rates are reported per
      kind. *(A wrong label from hidden tests mixes all three.)*

## After the run

- [ ] The data set is spent. Anything designed by looking at its failures
      is tested on fresh tasks before it is claimed.
