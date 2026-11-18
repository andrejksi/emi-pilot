# Handoff, 18 Nov 2026, 20:55 UTC

What the next session needs to carry on: where the work stands, what to do
next and how to tell it is done, and the standing rules.

## Standing rules (from the user; they still hold)

- Answers to the user: bottom line first, then Situation / Background /
  Assessment / Recommendation, in plain words for someone who has never
  seen the code (user's global CLAUDE.md).
- Push only to `claude/confident-johnson-zcpmkk` in `andrejksi/EMI`,
  `andrejksi/emi-pilot` and `andrejksi/emi-drafting`. Open a pull request
  only when asked; never merge without being asked.
- Commit trailers: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  and `Claude-Session: <this session's link>`. No model names in commits,
  pull requests or files.
- Never ask for or accept an API key in chat.
- Never read a task's fix, hidden tests or anyone's attempts. Sessions that
  draft, attack or write questions get none of these and no EMI source.
- Gemini runs only through Antigravity, which the user operates.
- Numbers from experiments go in `emi-pilot` (or the validation lab), not
  in EMI. EMI's own rules are in `EMI/CLAUDE.md`: `scripts/check.sh --fast`
  before a commit that changes code, evals stay, and so on.
- The user's email stays private.

## The three repositories (all cloned under /home/user)

- `EMI`: the product. Branch at 9ab84be; pull request
  https://github.com/andrejksi/EMI/pull/27 is open with this week's work
  (speed-ups, guard judging, the parallel-command and laws-dir fixes, new
  README, CI skipping tests on documentation-only pushes via
  `ci/code-changed.sh`). Its CI for 9ab84be was running at handoff.
- `emi-pilot`: the studies. Plans, results, harness, this file.
- `emi-drafting`: the drafting and adversary workspace (tasks' starting
  code, drafting instructions, drafts, tries).

## Round 3: running now

Plan, committed before drafting: `emi-pilot/results/adversary-round3/PREREG.md`.
In short: 12 fresh tasks (`emi-drafting/round3/tasks.txt`), each drafted
twice with the same instructions (`emi-drafting/DRAFTING_ROUND3.md`): arm
`old` uses emicode 0.1.1, arm `new` the build of EMI 9ab84be in
`emi-drafting/emi-builds/`. Both rule sets are attacked blind under labels
(`emi-drafting/round3/labels.json`). Pass line: tasks with a gap only under
old rules minus tasks with a gap only under new rules ≥ 3.

State at handoff:

| | old arm | new arm |
|---|---|---|
| session | `session_01MWwBLBM3d3vRBYXky9ppz8` | `session_01MWwBLDQzKR67EFENMV5RFD` |
| branch (emi-drafting) | `claude/round3-old` | `claude/round3-new` |
| phase 1 | done 20:41, 12 tasks, 25 questions; openmdao and yt-dlp finished without questions | task 10 of 12 at 20:46, 42 questions so far; about 4–5 min a task |

The new arm is slower because the new brief asks for more (ANSWERS record,
varied inputs, guards in their own files, more questions). That is expected
and is reported as drafting cost (PREREG measure 4).

The question page is published and empty:
https://claude.ai/artifact/5h1pJuuWtTWTjUbSCkwNsJ (source:
`results/adversary-round3/page/index.html`, capability `db`). It reads three
collections and writes one:

- `tasks/{task id}`: `{name, report}` (report = the task's `prompt`).
- `questions/{qid}`: `{task, order, situation, question, options, suggested}`.
- `answers/{qid}`: written by the page: `{answer, how: option|own|doesnt_matter, seconds, at, changes}`.

### Next steps, in order

1. **Wait for the new arm's "phase 1 done"** (`list_sessions` with
   `children: true`, or its branch). Done when both sessions are idle with
   that reply.
2. **Fill the page.** Fetch both branches; for each task gather both arms'
   `questions.json`; give every question a neutral id (`q001`…); shuffle
   within each task with `random.Random(20261118)`; write `tasks` and
   `questions` with `ArtifactData` `batch`. Do not copy the `from` field
   (its question numbers differ between briefs and would reveal the arm).
   Keep the qid → (arm, task, Q-id) map in the scratchpad until the user
   has answered; then commit it as
   `results/adversary-round3/question-map.json`. Done when the page lists
   every question (one `ArtifactData list` of `questions`), and the user is
   told it is ready.
3. **Return the answers.** When `answers` covers every question: map them
   back and send each drafting session its answers with `send_message`
   (the JSON per task as `DRAFTING_ROUND3.md` phase 2 describes, asking it
   to write `drafts3/ARM/<task>/answers.json` itself and run phase 2). This
   session may not push to the drafters' branches. Record the user's total
   and per-question time (sum of `seconds`) in
   `results/adversary-round3/answers.json`. Done when both sessions reply
   "phase 2 done".
4. **Merge the drafts.** Fetch `claude/round3-old` and `claude/round3-new`
   into emi-drafting's `claude/confident-johnson-zcpmkk` and push. Check:
   every task has `checked/` or `last/` in both arms, and no file outside
   `drafts3/ARM/` changed.
5. **The attack (the user's step).** Give the user, as separate commands:
   `git pull` in emi-drafting, then
   `EMI_ADVERSARY_ROUND=3 python3 setup_adversary.py --all`, which makes
   `../emi-adversary-r3/r3-01` … `r3-24`. They run each label in
   Antigravity with `ADVERSARY_PROMPT.md`, a fresh sub-agent per label, in
   label order, and collect with
   `EMI_ADVERSARY_ROUND=3 python3 setup_adversary.py --collect --all --by "Antigravity, MODEL, DATE"`.
   Done when `adversary3/` holds 24 labels, each with `about.json`.
6. **Score.** `harness/score_adversary.py --task TASK --tries emi-drafting/adversary3/LABEL --out results/adversary-round3/out/LABEL.json`
   for each label (the task comes from `about.json`; three at a time, as
   `results/adversary-round2/run.sh` does). Still to write: measure 1, the
   real fix against each arm's final rules, each rule run twice (the gold
   fix is in `tasks/<id>/replay/`; run it, do not read it).
7. **Report** against the PREREG: primary measure d, then measures 1–5,
   then deviations (at least: litellm dropped for size, decided before
   drafting).

## EMI bug audit: findings waiting on the user

Full table: `results/bug-audit-2026-11-18/README.md`. Of the user's list,
most were already fixed. Three small gaps and one decision remain; none
affects round 3 (the drafters use only the rules check, on a pinned build).

Proposed, waiting for the user's yes:

1. Tests ignore the machine-wide git settings: set `GIT_CONFIG_NOSYSTEM=1`
   in the test environment (the private home already hides the user's
   config, and the cleared environment hides `GIT_*`).
2. `emi done` ignores `__pycache__` and `.pyc` files when listing changed
   files.
3. A rule that fails on the change quotes the failing line beside the
   failing input (today: the input only).
4. **Decision needed:** let an old test listed in the approved
   `EXPECTED-CHANGES` change without asking the person again, only when its
   new version passes on the change and fails on the old code. This
   changes the decision table: it needs an ADR, a `POLICY` bump and
   characterisation-table updates (`EMI/CLAUDE.md`).

Also seen: renaming an old test file asks the person (counted as a
deletion). Safe, but a click for a harmless rename; could be recognised
when every old test still exists and passes.

## Other decisions the user has not made

- Merge https://github.com/andrejksi/EMI/pull/27 once CI passes
  (recommended before more EMI changes).
- Rerun anta and meltano in Antigravity (round 2's two Gemini tasks).
- Keep or drop codegraph; retro item 2 (orchestrator file); architecture
  review candidates 2–6 (recommended: defer).
- Older open items: the `laws.yml` workflow on Actions, the approval page
  with timing (the round-3 question page is a start on it).

## Things that will not carry over

- This session's scheduled check-ins (`send_later`) wake this session, not
  the next one: do the checks above directly.
- The scratchpad (the wheel build venvs, the bug-audit projects) is gone
  with this machine; everything needed is committed.
