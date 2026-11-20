# Why right candidates were blocked: seven held-out tasks again

Workflow run [44652771171](https://github.com/andrejksi/emi-pilot/actions/runs/44652771171),
emi-pilot `5aaa106` (virtualenv on PATH, plain pytest's baseline recorded,
every blocking receipt kept with its reason), EMI `study-gate-v1`, the
held-out candidates and laws unchanged. The seven tasks are the ones where
the held-out replay (`results/gate-replay-heldout`, branch
`results/gate-replay-heldout`) blocked right candidates: the ceiling on
five, the approved laws on two.

`replays.jsonl` is the run's rows, `receipts/` every receipt that did not
answer stop, `oracles/` the hidden tests' verdicts. This is a development
result: the held-out set is spent.

## What blocked each right candidate

| task | where | cause | whose |
|---|---|---|---|
| packaging-1531 | ceiling | none now: the virtualenv was missing from PATH | harness, fixed in `5aaa106` |
| fonttools-4371, fonttools-4388 | ceiling | `incomplete`: pytest collected no law. fontTools collects `*_test.py` only (`setup.cfg`), and the ceiling's law was `test_ceiling_hidden.py` | harness, fixed after this run |
| faker-2446 | ceiling | `incomplete`, the same: Faker collects `tests/*.py` only | harness, fixed after this run |
| huggingface_hub-5287 | ceiling | `repair`: the hidden tests (`TestHfFileSystemRepositoryRO`) create repositories on the Hub's staging server; EMI's sandbox has no network, the oracle has | the task: listed in `batches/hidden-tests-need-network.txt` |
| biopython-5404 | approved laws | `repair`: two laws fail with `NotImplementedError: Don't be greedy, that could be massive!` | the laws: unsatisfiable |
| eodag-2441 | approved laws | `repair`: a right candidate filters out both mocked products (`assert [] == ['S2B_…']`) | the laws: their fixture |

**biopython's laws can never pass.** Their helper reads the written data
back with `BgzfReader.read()` and no size, which Biopython refuses on
purpose. Every implementation fails them, right or wrong. So the approved
laws' 2 "catches" on biopython in the held-out score are not catches, and
the primary arm's catch over restore is at most 10 of 63 (15.9%), not 12
of 63. The laws were drafted before any code existed and approved in about
two minutes; `emi rules check` showed them failing at the baseline, as a
law for new behaviour should, and nobody saw that they failed for a reason
the task does not mention.

**eodag's law rests on a fixture the drafter invented**: two STAC features
carrying only `datetime`, run through a mocked `StacSearch._request`. A
right fix filters on what real Planetary Computer results carry, and drops
both invented products.

Plain pytest: biopython's visible tests fail with no change
(`baseline: fail`), so plain pytest's blocks there are not catches either.

## What changed because of it

- EMI `1022358`: a listing that finds no tests now says pytest found none
  and that `python_files` or `testpaths` may not match.
- emi-pilot: the ceiling's law is written as
  `.emi/laws/tests/test_ceiling_hidden_test.py`, which every common
  collection pattern matches; `study/check_harness.py --network-tasks`
  names tasks whose hidden tests need the network instead of judging the
  ceiling there.
- Nothing in EMI's decision table is at fault in these seven tasks. Every
  `incomplete` was honest; every `repair` was a law or a test that
  really failed.

## Known answers on this run

`study/check_harness.py --network-tasks batches/hidden-tests-need-network.txt`
fails on fontTools and Faker, the harness bug fixed after the run. The next
replay must pass it before any held-out number is recomputed.
