# Rival versions: do attempts that pass the same rules disagree?

The two wrong attempts of the laws trial that got past both checkers
(`cs-si__eodag-1717.kimi.a2` and `matthewwithanm__python-markdownify-230.deepseek.a2`)
are run here against the rules drafted for their task, and side by side
with the task's other attempts on inputs the rules do not name. The
question is whether a person could have been shown the gap before the
hidden tests were run: an input on which two versions that pass every
rule give different answers.

Inputs: the harvest-tuning attempts (`../harvest-tuning/runs/*/candidate.diff`)
and the final drafted rules of `andrejksi/emi-drafting` (`drafts/<task>/checked`,
else `last`). Which attempts are right comes from `../harvest-tuning/table.md`.
No hidden test and no real fix was read for this.

## Scripts

- `try.sh TASK ATTEMPT`: a worktree of the task at its baseline, the
  attempt's diff applied, the rules copied to `.emi/laws`, and the rules
  run with plain pytest. The paths at its top are the session's scratch
  directory, as it ran.
- `md_diff.py WORKTREE`: `markdownify()` on 1,398 `<code>` inputs built
  from 11 pieces (backticks, spaces, `*`, `<b>`, nested `<code>`), one to
  three pieces each; prints each output.
- `eodag_probe.py LAWS zip`: `download_all(extract=False)` twice on the two
  products of the task's example, with the mocked server sending the zip
  under each of five file names (`.zip`, `.tar`, `.nc`, `.tif`, none), named in
  `content-disposition` or not; prints the requests made (2 means the second
  run downloaded nothing).

## Results

Rules (`out/rules.tsv`):

| task | attempt | right? | rules |
|---|---|---|---|
| eodag | deepseek.a1 | right | 8 pass |
| eodag | kimi.a1 | right | 8 pass |
| eodag | kimi.a2 | WRONG | 8 pass |
| eodag | deepseek.a2 | wrong (gave up) | 2 fail |
| eodag | deepseek.a3 | WRONG | 2 fail |
| markdownify | deepseek.a1, a3, kimi.a1, a2, a3 | right | 11 pass |
| markdownify | deepseek.a2 | WRONG | 11 pass |

Side by side, among the attempts that pass every rule:

- **eodag** (`out/eodag.*.json`): the two right attempts make 2 requests
  in all 10 variants. kimi.a2 makes 4 (downloads everything again) in 8 of
  the 10: whenever the server does not name the file `<id>.zip`. Its diff
  special-cases `.zip`. The rules serve only `<id>.zip`, so they cannot see it.
- **markdownify** (`out/md.*.json`): the six attempts disagree on 391 of
  1,398 inputs, and on every one of them the wrong attempt is the only one
  that differs. Grouped by hand, the 391 are four kinds of input:
  - code starting or ending with a backtick (the smallest, and what each
    side gives for it, is below);
  - nested code, as `<code>*<code>`q`</code>*</code>`;
  - both at once (317 of the 391);
  - code that is only a backtick.

  ```text
  input:            <code> `*</code>
  five attempts:     `` `* ``
  the wrong one:     ```*``
  ```

## What this does and does not show

Two tasks and two wrong attempts. It shows that in both cases the gap was
on the input side (cases the rules do not name), not the code side (no
stand-in would have found it, since the wrong attempt is right on every
named case), and that a disagreement between passing versions pointed at
it. It does not give a rate. The wrong version was the odd one out here,
but that is not a vote anyone may count: with two versions, one against one
says nothing about which is right. Only a person can say which output is
right.
