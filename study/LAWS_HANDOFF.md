# Handoff: Blind Law Drafting & Timed Approval (Step 3)

> **Audience:** Two blind AI sessions (primary drafter + secondary drafter from different makers) that draft EMI laws from the issue text alone before any code is written, followed by timed human approval (`<= 5 min/task`).
> **Protocol:** `study/gate.md` (EMI tag `study-gate-v1`, `fc602d280b4fd9106b8510518e702d850060ed29`).

---

## 1. Strict Blindness Rules (NON-NEGOTIABLE)

1. **NEVER** read, open, grep, or diff anything under:
   - `tasks/*/hidden/`
   - `tasks/*/replay/`
   - `tasks/*/task.json`
   - `results/harvest-heldout/` or any other candidate/replay directory
2. **NEVER** search GitHub or the web for the PR, commit, or fix.
3. **NEVER** write or edit product code or existing test files — write files **ONLY** under `.emi/laws/`.
4. Use a **fresh isolated context** (new conversation or fresh subagent per task) so drafts do not leak across sessions that wrote candidates.
5. If a fix or hidden test is accidentally viewed, stop on that task and add its ID to `batches/seen.txt`.

---

## 2. One-Time Setup: Get the `study-gate-v1` `emi` Binary

```bash
python3 study/save_laws.py ensure-emi --dest /tmp/emi-bin/emi
```

*(Downloads the prebuilt `study-gate-v1` `emi-bin` artifact from GitHub Actions. Fallback if `gh` is unavailable: build `andrejksi/EMI` at tag `study-gate-v1` with `cargo build --release -p emi-cli --bin emi`.)*

---

## 3. Blind Law Drafting Workflow (Primary & Secondary Drafters)

- **Primary drafter** runs with `--role primary` on branch `study/laws-primary` → writes `first/`, `checked_draft/`, `checks_primary/`, `draft_primary.json`.
- **Secondary drafter** (different maker) runs with `--role secondary` on branch `study/laws-secondary` → writes `secondary/`, `secondary_checked/`, `checks_secondary/`, `draft_secondary.json`.

Repeat for every `<TASK_ID>` in `batches/heldout.txt` (skip any task whose `draft_<role>.json` is already saved):

### Step 1 — Prepare a blind workspace and print the brief + issue prompt
```bash
python3 study/save_laws.py prepare \
  --task <TASK_ID> \
  --work /tmp/laws/<TASK_ID> \
  --emi /tmp/emi-bin/emi
```

### Step 2 — Draft rules strictly under `/tmp/laws/<TASK_ID>/.emi/laws/`
- Read repository source/tests inside `/tmp/laws/<TASK_ID>` as needed, and run tests with `.venv/bin/python -m pytest ...`.
- Write rule tests and `answers.txt` **ONLY** under `/tmp/laws/<TASK_ID>/.emi/laws/`, following the printed `emi rules brief`.
- Treat what the issue prompt states as the person's written answers (`A1 written: ...`); anything unstated is `"doesn't matter"`. Do not invent requirements.

### Step 3 — Check and snapshot the draft
```bash
python3 study/save_laws.py check \
  --task <TASK_ID> \
  --work /tmp/laws/<TASK_ID> \
  --role <primary|secondary> \
  --model "<YOUR_MODEL_ID>" \
  --out results/heldout-laws \
  --emi /tmp/emi-bin/emi
```
- The **first** call snapshots your initial draft (`first/` or `secondary/`).
- If `emi rules check` exits non-zero (e.g. exit `3`), fix what it reports under `.emi/laws/` and re-run `check` until it exits `0` (cap: 5 check rounds per task; if it still fails after 5 rounds, stop and keep the recorded `first/` + `draft_<role>.json` so `study/score.py` counts it accurately as `dropped_by_rules_check`).

### Step 4 — Clean up scratch workspace and commit periodically
```bash
rm -rf /tmp/laws/<TASK_ID> /tmp/laws/<TASK_ID>.emi-state
```
Commit and push `results/heldout-laws/<TASK_ID>/` every ~5 tasks.

---

## 4. Timed Human Approval (Primary + Outside Approver)

Once the primary drafter's `results/heldout-laws/` is merged on `main`:

1. **Primary approver** (reviews all held-out tasks, target `<= 5 min/task`):
   ```bash
   python3 study/approve_laws.py review \
     --approver primary \
     --laws-root results/heldout-laws \
     --tasks @heldout
   ```
   Writes approved laws to `results/heldout-laws/<TASK_ID>/checked/` and appends timing records to `results/heldout-laws/approvals.jsonl`.

2. **Outside approver** (has not seen pilot failures; reviews the deterministic 10-task sample drawn with `random.Random(20261117)`):
   ```bash
   python3 study/approve_laws.py review \
     --approver outside \
     --laws-root results/heldout-laws \
     --tasks @heldout \
     --sample-outside
   ```
   Writes timing records for `approver: "outside"` to `results/heldout-laws/approvals.jsonl`.

---

## 5. Next Step After Approval (Automated)

Once `results/heldout-laws/` (both drafters + `checked/` + `approvals.jsonl`) and all candidates in `results/harvest-heldout/runs/` are merged:
1. Run `harness/oracle.py --run results/harvest-heldout/runs/*` to grade all candidates against hidden tests.
2. Dispatch `.github/workflows/gate-replay.yml` (`tasks=@heldout`, `runs=2`, `emi_ref=study-gate-v1`, `include_gold=false`).
3. Score with `study/score.py` and independently verify byte-identical output.
