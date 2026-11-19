# Handoff: Blind Candidate Writing for the EMI Laws Study

> **Audience:** Another AI session whose ONLY job is writing blind candidate patches (no gate, `arms: control`) for the held-out tasks in `batches/heldout.txt`.
> **Everything else is already built, tested, and merged on `main`:** EMI `study-gate-v1` (`fc602d280b4fd9106b8510518e702d850060ed29`), `study/save_candidate.py`, `study/replay_gate.py`, `study/score.py`, `harness/oracle.py`, and `.github/workflows/gate-replay.yml`.

---

## 1. Strict Blindness Rules (NON-NEGOTIABLE)

To preserve held-out scientific validity per `study/gate.md`:

1. **NEVER** read, open, grep, or diff any file under:
   - `tasks/*/hidden/`
   - `tasks/*/replay/`
   - `tasks/*/task.json` (contains `oracle` test IDs)
   - `results/` (other candidates or replays)
2. **NEVER** search GitHub or the web for the PR, commit, or issue fix.
3. **ALWAYS** use `study/save_candidate.py prepare` to lay out a clean baseline repository and print ONLY the issue prompt.
4. If you accidentally view a task's fix or hidden tests, stop working on it and add its ID to `batches/seen.txt`.

---

## 2. Current State of the Study

| Component | Status | Location |
|---|---|---|
| Tagged EMI binary | Ready (`study-gate-v1` @ `fc602d2`, CI green) | `andrejksi/EMI` |
| Signed study protocol | Ready | `study/gate.md` |
| Double-replay runner + workflow | Ready & verified (0 `incomplete`, 100% `ceiling` catch / 0% false-block) | `study/replay_gate.py`, `.github/workflows/gate-replay.yml` |
| Deterministic scorer | Ready & verified byte-identical across 3 independent passes | `study/score.py` |
| Blind candidate helper | Ready | `study/save_candidate.py` |
| Held-out task list | 16 verified sound tasks in `batches/heldout.txt` (target is 30) | `batches/heldout.txt` |

---

## 3. Your Exact Task: Write Blind Candidates

For each `<TASK_ID>` in `batches/heldout.txt` and each `<SEED>` (`1`, `2`, `3`):

### Step 1 — Prepare a blind workspace
```bash
python3 study/save_candidate.py prepare \
  --task <TASK_ID> \
  --work /tmp/work/<TASK_ID>.<SEED>
```
This checks out the repository at its pre-fix `base_commit` on branch `task` (with `.venv` ready) and prints ONLY the issue prompt.

### Step 2 — Solve the issue in `/tmp/work/<TASK_ID>.<SEED>`
- Work strictly inside `/tmp/work/<TASK_ID>.<SEED>` (do not inspect the `emi-pilot` repo while solving).
- Edit code and tests as you normally would; run tests with `.venv/bin/python -m pytest ...`.
- **No EMI gate** (`arms: control`): stop when you believe your fix is done (cap: 150 tool steps per `study/gate.md`).

### Step 3 — Export the candidate
```bash
python3 study/save_candidate.py save \
  --task <TASK_ID> \
  --work /tmp/work/<TASK_ID>.<SEED> \
  --model "<YOUR_MODEL_ID>" \
  --seed <SEED> \
  --out results/harvest-heldout/runs
```
This writes:
- `results/harvest-heldout/runs/<TASK_ID>.<tag>.<SEED>/candidate.diff`
- `results/harvest-heldout/runs/<TASK_ID>.<tag>.<SEED>/run.json`

### Step 4 — Clean up and repeat
```bash
rm -rf /tmp/work/<TASK_ID>.<SEED>
```
Do **not** run `harness/oracle.py` during candidate writing (keep the session blind across seeds).

### Quota Target (`study/gate.md`)
- 30 held-out tasks × 3 seeds × 2 models from different makers (equal shares).
- Final balanced evaluation pool: **100 wrong + 100 right** candidates (at most 5 of each per task, matched by changed-line count bins `1-10`, `11-30`, `31-100`, `100+`).

---

## 4. What Happens After Candidate Writing (Owner / Post-Handoff)

Once `results/harvest-heldout/runs/` is populated and committed:

1. **Grade all candidates against hidden tests:**
   ```bash
   python3 harness/oracle.py --run results/harvest-heldout/runs/*
   ```
2. **Draft laws blindly** (in a separate blind session that sees only `emi rules brief` + the issue prompt, never fixes/hidden tests/candidates) into:
   - `results/heldout-laws/<TASK_ID>/first/` (primary drafter unapproved)
   - `results/heldout-laws/<TASK_ID>/secondary/` (secondary drafter unapproved)
   - `results/heldout-laws/<TASK_ID>/checked/` (laws passing `emi rules check` + human approval)
3. **Record timed human approvals** (`<= 5 min/task`, 30 tasks primary + 10 tasks outside approver) in `results/heldout-laws/approvals.jsonl`:
   ```json
   {"task": "<TASK_ID>", "approver": "primary", "minutes": 3.5}
   {"task": "<TASK_ID>", "approver": "outside", "minutes": 4.1}
   ```
4. **Run the sandboxed double-replay gate on GitHub Actions:**
   ```bash
   gh workflow run gate-replay.yml -R andrejksi/emi-pilot \
     -f tasks="@heldout" \
     -f attempts="results/harvest-heldout/runs" \
     -f laws_root="results/heldout-laws" \
     -f runs=2 \
     -f include_gold=false \
     -f emi_ref=study-gate-v1
   ```
5. **Independent score verification:**
   ```bash
   python3 study/score.py \
     --replays results/gate-replay-heldout/replays.jsonl \
     --approvals results/heldout-laws/approvals.jsonl \
     --json score-verify.json \
     --md score-verify.md
   diff -u results/gate-replay-heldout/score.json score-verify.json
   ```
