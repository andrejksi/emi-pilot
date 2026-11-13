# EMI pilot

Does EMI's completion check change how often a coding agent's "done" is
wrong? Each run gives an agent one task under one **arm**, takes its final
change, and judges it with **hidden tests** the agent and EMI never saw.

| Arm | When the agent says it is done |
|---|---|
| `control` | nothing checks |
| `naive` | the visible tests must pass (up to 3 rounds back) |
| `cooperative` | `emi done`, EMI's defaults (up to 3 rounds back) |
| `strict` | `emi done` with `on_unexercised`/`on_redundant`/`on_survivors: repair`, 20 mutants |

Every run lands in one cell:

|  | hidden tests pass | hidden tests fail |
|---|---|---|
| **accepted** | done, right | **done, wrong** (a false completion) |
| **not accepted** (repair rounds ran out, or EMI said `ask_person`/`incomplete`) | flagged, right (cost) | flagged, wrong (caught) |

## Layout

```
projects/<name>/            toy projects (calc, ledger, shop, from EMI's evals)
tasks/<id>/task.json        where the code comes from, the prompt, the oracle
tasks/<id>/hidden/          the oracle: hidden tests (a folder, or test.patch)
tasks/<id>/replay/          fixed candidate changes (folders or .patch files)
arms/<arm>.json             EMI settings laid over `emi init --yes`
harness/                    import, plan, prepare, agent (+ gates), oracle, table
.github/workflows/pilot.yml the same on GitHub Actions
```

Two kinds of task. The three toy tasks (`calc-median`, `ledger-fee`,
`shop-percent`) are `dir` tasks: a project folder and the virtualenv you
give. The others are `git` tasks: a real repository at a commit, imported
from [SWE-rebench-V2](https://huggingface.co/datasets/nebius/SWE-rebench-V2).

## Real tasks

`harness/import_swe.py` turns SWE-rebench-V2 rows into tasks. It keeps
Python tasks that install with `pip`, test with serial pytest on named
files, have 1–10 FAIL_TO_PASS and at least 5 PASS_TO_PASS tests, a fix of
1–4 product files under 150 lines, and an issue the dataset judged
complete. From the 32,079 rows (7,243 Python), that leaves 30 created
since June 2025, 174 since January 2025 and 296 since July 2024; the
newest Python task is from 22 July 2025, so a model trained in 2026 may
have seen some fixes. All 30 are imported here (see `tasks/`), with the
repository's license in each `task.json`.

```bash
pip install pandas pyarrow   # only to import more tasks
curl -L -o rebench-v2.parquet "https://huggingface.co/datasets/nebius/SWE-rebench-V2/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet"
python3 harness/import_swe.py rebench-v2.parquet --since 2025-06-01 --limit 30
```

For each git task:

- **The code** is the repository at `base_commit` written as one commit,
  with no history or remote: the fix is not in reach of `git log`.
- **The environment** is built once per task with `uv` (Python from the
  dataset, then its `pip install` steps, then pytest, coverage and
  hypothesis), and kept under `.cache/envs/` (`PILOT_CACHE` to move it).
- **The visible tests** are the files the dataset's test command names;
  that is also EMI's test command, so it runs a few files, not the suite.
- **The oracle** applies the real tests (`hidden/test.patch`) over the
  baseline's versions of the files they touch; every FAIL_TO_PASS and
  PASS_TO_PASS test must pass.
- **Replays**: `gold` (the real fix, no tests), `gold-with-tests` (the fix
  and its tests, as an agent that wrote them would leave it), `nothing`
  (no change; the oracle must fail it).

**Not run yet.** The real tasks' setup, replays and oracle have not been
run anywhere: that clones each repository and runs its install steps and
tests, which is why it happens on GitHub's runners (step 2 below). A task
whose `nothing` replay passes the oracle, or whose `gold-with-tests`
fails it, is a broken task, not a finding.

## Run it on GitHub Actions

### Set up once

1. On github.com, create a new **private** repository (for example
   `emi-pilot`) with nothing in it.
2. Put this folder's contents in it, `.github/` included:

   ```bash
   tar -xzf pilot.tar.gz && cd pilot
   git init -b main && git add -A && git commit -m "EMI pilot"
   git remote add origin https://github.com/YOU/emi-pilot.git
   git push -u origin main
   ```

3. For live runs: Settings → Secrets and variables → Actions → New
   repository secret, named `MODEL_API_KEY`, holding your model key.

### Run it, in this order

Actions → **pilot** → Run workflow, then fill in the form:

| Step | backend | tasks | seeds | What to look for |
|---|---|---|---|---|
| 1. Smoke test | `replay` | `@toy` | | The table matches `sample-replay-results/table.md`. |
| 2. Check the real tasks | `replay` | `@a`, then `@b` | | **Task check** in the summary: every task `sound: yes`. Drop any that is not. |
| 3. Live trial | `chat` | `@a`, then `@b` | `3` | Also fill in `base_url` and `model`. |

Step 2 is the first time the real tasks run anywhere. It also gives the
first number that means something: how often EMI's arms send back the
real, right fix (`gold`, `gold-with-tests`).

The 30 real tasks are split into batches `@a` and `@b` of 15, so a batch
fits the free plan's 20 jobs at once. `tasks` also takes task ids,
space-separated; `batches/*.txt` are the batches.

### What happens

- **plan** lists the runs. **agent** is one job per task: it builds the
  task's environment once, does every run of that task in turn (4 arms x 3
  replays or seeds), each in a fresh copy of the repository, and then
  grades them with the hidden tests. **table** puts the tasks together.
- No run has the hidden tests: the job deletes them, and `.git`, before any
  run and keeps no git credentials; it fetches them back only after the
  task's last run has ended. The agent's own commands run sealed (below).
- The **summary** of the workflow run has the table and the task check;
  the `pilot-results` artifact has every run's record, receipts and diff.
- A missing key, a failed run or a broken task fails the workflow.

### Cost

- **Actions minutes:** a batch is 15 jobs, one per task. A real task's
  environment is built once, with `uv` (the dataset's `pip install` steps
  through uv's installer); a replay of `@a` took 1 to 23 minutes a task. A private repository on GitHub's free
  plan has 2,000 minutes a month (Settings → Billing shows what is left).
- **Model:** a `chat` batch is 180 agent runs; each can take up to `max_steps` (150)
  steps and 3 rounds back. Try one task with `seeds: 1` first and read the
  `usage` in its `run.json`. The first live run used 4,300–6,400 tokens a
  run on the toy task.

## Run it on a machine (optional)

Needs Linux with bubblewrap, `emi` (`pip install emicode==0.1.1`), `uv`,
and a virtualenv with `pytest>=8,<9`, `coverage>=7.9,<8` and `hypothesis`.
The real tasks clone each repository and run its install steps and tests
on that machine.

```bash
python3 -m venv venv && venv/bin/pip install 'pytest>=8,<9' 'coverage>=7.9,<8' hypothesis emicode==0.1.1 uv
```

```bash
TASKS="@toy" PATH="$PWD/venv/bin:$PATH" EMI=venv/bin/emi VENV=venv harness/run_local.sh replay
```

With a model, `harness/run_local.sh chat 3` and `MODEL_BASE_URL`,
`MODEL_NAME`, `MODEL_API_KEY` set. Check the harness without a key against
the scripted endpoint `harness/stub_model.py`. Results are in
`runs/<time>-<mode>/`.

## What this is not, yet

- **Evidence, yet.** The toy tasks are a smoke test: their replayed
  changes were written by hand to cover the cases, so they say what each
  arm does with such a change, not how often agents make one. The real
  tasks' replays use the real fix, so they measure what EMI costs on right
  work; how often an agent's change is wrong comes only from live runs.
- **A real coding agent.** `chat` is a minimal tool loop (list, read,
  write, run, finish). It is enough to test the gates with a cheap model;
  the trial proper should use a harness EMI hooks (OpenCode, Codex CLI,
  Claude Code), whose behaviour under a repair differs from this loop's.
- **Fully sealed.** The agent's `run` tool runs in bubblewrap with no
  network, and with `tasks/`, `runs/` and the cached clones hidden, so it
  cannot read the hidden tests, other runs' records, or the commits after
  the baseline. It still sees the rest of the machine read-write, and the
  harness process itself (which talks to the model) has the network.

## What the replay found (EMI 0.1.1)

- Only an edited old test was stopped (`ask_person`, both EMI arms);
  `control` and `naive` accepted it.
- No arm caught a wrong change that came with its own passing test: an
  unsorted median, a median that sorts its input in place, round-half-even
  instead of rounding down, and an off-by-one at a bound.
- `strict` sent back a right change that had no test: the cost side.
- `strict`'s mutants did not catch the off-by-one: Python's mutants negate
  a comparison (`>=` becomes `<`) and never move a bound (`>=` to `>`).
