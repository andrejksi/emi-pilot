# Practice harvest on the tuning tasks

Live runs of two models on the ten tuning tasks (`batches/tuning.txt`), with
no checker (`control`): the agent says it is done and nothing checks it.
These are the saved attempts the laws trial replays, so every checker is
judged on the same files.

| Set | Tasks | Workflow runs |
|---|---|---|
| `a` | the five run-9 tasks: eodag-1717, markdownify-230, meltano-3091, more-itertools-1028, narwhals-2864 | [44063535976](https://github.com/andrejksi/emi-pilot/actions/runs/44063535976), [44063542160](https://github.com/andrejksi/emi-pilot/actions/runs/44063542160) |
| `b` | the five drawn on 17 Nov: anta-1250, bluesky-1932, conan-18444, huggingface_hub-3180, trino-564 | [44068135737](https://github.com/andrejksi/emi-pilot/actions/runs/44068135737), [44068141060](https://github.com/andrejksi/emi-pilot/actions/runs/44068141060) |

Each set ran once per model, three seeds a task. A run directory is
`<task>.<model>.<set><seed>` and holds `run.json` (its `model` field names
the model), the final `candidate.diff` and the hidden tests' verdict in
`oracle.json`. 10 of the 60 planned attempts are missing: the model
provider refused them (HTTP 402, then 429) and they were not re-run.

Of the 50: 35 said done and were right, 10 said done and were wrong, 5 gave
up (one of those had the right change). Six of the ten wrong ones are on
anta-1250, two on eodag-1717, one each on markdownify-230 and meltano-3091;
the other six tasks have none. See `table.md`.
