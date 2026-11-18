# An adversary against the drafting study's rules

An agent was given, per task, only the bug report, the code and the drafted
rules (emi-drafting `ADVERSARY.md`, laid out by `setup_adversary.py`; the
rules each task got are in emi-drafting `adversary/<task>/about.json`), and
asked for three fixes that pass every rule and every existing test but are
still wrong, each with one example input and a plain claim. It ran in
Antigravity, one orchestrated sub-agent per task, on 2026-11-18; the
model's name was recorded as "Argon". It never saw the fixes, the hidden
tests, any attempt or EMI.

`run.sh /path/to/emi-drafting` scores every try with
`harness/score_adversary.py`: the fix rebuilt on a fresh baseline, the rules
run twice, the existing tests that passed on the baseline, the hidden tests
(`oracle.py`), and the try's example on the fix and on the baseline. `out/`
holds each task's JSON and log. The whole run took 5 min 38 s, three tasks
at a time.

## Results

All 30 tries are valid: each passed the rules on both runs and every
existing test that passed on the baseline, and touched only product code.
None of the ten tasks ended with "found nothing".

| task | gap (hidden tests fail) | hidden tests pass | unclear |
|---|---|---|---|
| anta | 3 | 0 | 0 |
| bluesky | 1 | 2 | 0 |
| conan | 1 | 2 | 0 |
| eodag | 3 | 0 | 0 |
| huggingface_hub | 2 | 1 | 0 |
| markdownify | 3 | 0 | 0 |
| meltano | 0 | 3 | 0 |
| more-itertools | 1 | 2 | 0 |
| narwhals | 0 | 3 | 0 |
| trino | 1 | 0 | 2 |
| **all** | **15** (8 tasks) | **13** | **2** |

- **Trino 2 and 3 are unclear, not gaps.** Their only hidden failure is
  `test_token_retrieved_once_when_multithreaded`, which also fails, in this
  environment, for `harvest-tuning` kimi.b1, a fix the same hidden tests
  passed in that study (`out/*.json` says "gap" for both; the scorer is
  right on what it ran, the test is not a verdict here). Scored twice more
  alone (`out/trinodb__*.again-{1,2}.json`): the same. Trino 1 also fails a
  hidden test of the bug itself (port 443 on another host), so it stays a gap.
- **"Hidden tests pass" is not "right".** The hidden tests are the
  project's own, and most of the 13 special-case what the hidden tests
  do not exercise either. By the try's own example, for instance: narwhals 1
  returns a 13-item series unchanged; meltano 1 still resolves a second
  property sharing a reference to `{}`, as before the fix; more-itertools 2
  still returns the fallback for a two-key Mapping, as before; conan 1
  still returns the URL with ` (fetch)` attached for another filter tag, as
  before. Whether each is wrong is a person's call on the example; nobody
  has made it yet.
- **Where the examples show it.** For a gap, the example is meant to show
  the wrong behaviour to a person who does not read code. `example_on_fix`
  and `example_on_baseline` in `out/` are what they would see; equal values
  mean the fix leaves that input as broken as before.

## A person's answers (`review/`)

The person who runs this lab, who knows none of the ten projects, was asked
twice, on one page (`review/page.html`, published as a private claude.ai
artifact):

1. **Rule on each fix from its claim and its example's output before and
   after** (`review/rulings/`, 7 of 30). Abandoned: without the project in
   mind, raw output does not say what is right ("Where is the difference",
   on conan 1, whose output is the same before and after). Of the four
   rated that the hidden tests prove wrong, two were called wrong, one fine,
   one can't tell.
2. **Answer one yes/no question per fix about what the program should do**,
   from the bug report alone (`review/answers/`, 29 of 30). The questions
   were written by fresh sub-agents (emi-drafting `QUESTIONS_PROMPT.md`,
   `adversary/<task>/<try>/question.md`), which saw the task, the try and
   its claim, not the hidden tests. What the fix does was folded away on
   the page. `review/fix_answers.json` records the answer each fix gives,
   read off the question's own "With this fix" line; a person's answer
   that differs marks the fix wrong. `review/compare.py` writes
   `review/table.md`:

| hidden tests \ person | wrong | fine | can't tell | unanswered |
|---|---|---|---|---|
| gap (15) | 8 | 5 | 1 | 1 |
| hidden tests pass (13) | 9 | 1 | 3 | 0 |
| unclear (2, trino) | 2 | 0 | 0 | 0 |

- **Of the 15 fixes the hidden tests prove wrong, the person's answers
  catch 8** and pass 5. The 5 are markdownify 1 to 3 (how Markdown wraps
  backticks), anta 2 (which interfaces a VXLAN may use) and huggingface_hub
  1: questions that need the project's domain, which the person did not
  have and the project's owner would.
- **Of the 15 the hidden tests do not decide, the person's answers mark 11
  wrong**, 1 fine (conan 2) and 3 can't tell. Hidden tests and person
  together mark 26 of 30 wrong, on all ten tasks.
- **The questions lean one way, so these counts are weak evidence.** In 28
  of 30 the fix gives "no" to a question that names the sensible behaviour,
  so answering "yes" flags it; the person answered "yes" 20 times. On the
  only two questions where the fix gives "yes" (anta 2 and 3) the person
  flagged neither. The person did answer "no" 6 times, so did not answer
  "yes" throughout, but these answers cannot tell catching a wrong fix
  apart from agreeing with a question. A next round should ask which of two
  outcomes should happen, the fix's and the claimed one, in random order.
- One person, one sitting, on projects that are not theirs: not a rate.
