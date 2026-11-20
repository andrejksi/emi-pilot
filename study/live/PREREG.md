# With and without EMI: does the patch that lands get better?

**Status: DRAFT, 20 Nov 2026. Not signed. It takes effect when the person
running the study signs it below, after the plan review of
`study/EVAL_CHECKLIST.md` stage 1. Decisions marked OPEN are made before
signing.**

## The question

When a coding agent works on a real task with EMI in its loop (EMI checks
the change when the agent says it is done, and sends it back with what it
found), is the patch that finally lands right more often than when the
same agent works without EMI, and at what cost?

This is the question the product rests on. The offline studies measure
whether a check can tell right from wrong; this one measures whether an
agent, told what the check found, ends with a better patch.

## Design: one run, forked where the agent first says "done"

A plain comparison (run the agent once with EMI, once without) needs 150 to
300 runs per arm to see a 10-point difference, because two runs of the same
agent on the same task differ a lot on their own: pilot run 9 compared four
arms at 15 runs each and could not separate them.

So each run is shared until the moment it matters:

1. The agent works on the task with no gate until it first says it is done.
   That patch, and the conversation that produced it, is saved.
2. **Arm A (without EMI):** that patch lands.
3. **Arm B (with EMI):** EMI checks the same patch. If EMI answers `stop`,
   the same patch lands (A and B are identical for that run). If EMI sends it
   back, the saved conversation continues with EMI's message, as the Stop
   hook would deliver it, for at most 3 rounds; the patch the agent leaves
   lands.
4. **Arm C (with EMI and a scenario)**, only if the development-set
   scenario run (`study/scenario/`) passes its line: as B, and the task's
   scenario finding, answered from the merged fix as the simulated person
   would ("on this input it should give Y"), is sent back as well.

Every run then gives a matched pair (or triple): same task, same agent,
same work up to "done". The difference between arms is only what EMI and
the scenario did. Continuations cost tokens only when a check sends the
patch back.

The patch that lands in each arm is judged by the task's hidden tests
(`harness/oracle.py`), run twice.

## The agent

- **OPEN: the model**, its endpoint, and the `MODEL_API_KEY` secret.
- **OPEN: the agent harness.** Either
  - (a) the pilot's own agent (`harness/agent.py`, `chat` backend: any
    OpenAI-compatible endpoint, a fixed tool set, sealed commands); or
  - (b) Claude Code headless with `emi hook install --harness claude-code`,
    which is how EMI ships. Recommended if the model is a Claude model: it
    tests the product as a person would run it, hook message and all.
- `max_steps` 150 before the first "done"; at most 3 repair rounds of 50
  steps each after it.
- Every run is scripted and headless and commits its transcript, step and
  token counts, the model id and the saved conversation at the fork.

## Tasks

- The 7 fresh tasks of `batches/scenario.txt` (merged after 24 Oct 2026,
  sound), and **OPEN**: about 25 older tasks (sound pilot tasks or unused
  SWE-rebench-V2 rows), reported separately, so the result on fresh tasks
  is never mixed with tasks a model may have seen.
- Not the 28 held-out tasks: EMI's harness and the scenario work were
  developed on them.
- **Seeds: 5 per task.** About 32 tasks x 5 = 160 forked runs.

## What is measured

Per run, each arm's landed patch is right or wrong. Over the matched pairs:

- **Repaired:** wrong at "done", right after EMI sent it back (B right, A
  wrong).
- **Harmed:** right at "done", wrong or abandoned after EMI sent it back
  (A right, B wrong).
- **Primary measure: the net gain**, repaired minus harmed, as a share of
  runs. Interval: 95% percentile interval from 10,000 resamples of tasks
  (`random.Random(20261120)`).
- **Cost:** right patches sent back (the agent's time spent for nothing),
  extra tokens and minutes per run, runs that ended `incomplete` or
  `ask_person`, and runs where the agent, sent back, edited tests or laws
  instead of the code (EMI reports these; counted, not hidden).
- The same for C against B, if C runs.

`ask_person` and `incomplete` at the end of the rounds: the patch lands as
the agent left it (that is what happens when nobody answers) and the run
is counted under cost.

## The decision

**OPEN** (proposed): EMI in the loop is worth it when the net gain of B
over A is at least 8 points of runs and harmed is at most 2 points, at no
more than 30% extra tokens. It is not when the net gain is under 3 points
or harmed exceeds 5. Between: no claim, and the per-task table is read for
where the gain came from.

With 160 pairs, a net gain of 8 points has a 95% interval of roughly 4
points either side when only a third of runs are sent back, which is the
reason for 5 seeds. Fewer runs can only see a large effect.

## What a result leads to

- **B beats A:** EMI's completion check, as shipped, makes agents land
  better patches. C against B then says whether scenarios add to it.
- **B ties A, C beats B:** the gain is the scenario's; EMI's completion
  check alone is not enough, and the scenario becomes the product's core.
- **Neither beats A:** checking finished work and sending it back does not
  change what lands, for this agent. EMI takes the validator branch of the
  November plan.

## Cost estimate

Pilot run 9: median 116,000 tokens a run, mean about 460,000, largest 1.5
million. 160 runs to "done" at the mean: about 74 million tokens.
Continuations only where EMI or the scenario sends the patch back (a third
to a half of runs, at most 3 rounds of 50 steps): about 15 to 30 million
more. **About 90 to 105 million tokens in all**, plus the Actions minutes to
check and judge each landed patch twice.

## Before the run

- `study/EVAL_CHECKLIST.md`, all four stages; `study/check_harness.py`
  passes on the replays of the landed patches (the ceiling and the
  oracle's known answers).
- **Rehearsal:** 3 tasks x 2 seeds end to end, including one fork that EMI
  sends back, before the rest. The resumed conversation is checked to hold
  the original one unchanged plus EMI's message, and nothing else.
- The scenario run on the development set comes first; arm C runs only if
  it passes.

## Sign-off

Signed: ______  Date: ______
