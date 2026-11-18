#!/usr/bin/env bash
# Score every task's adversary tries (emi-drafting adversary/<task>/) with
# harness/score_adversary.py, three tasks at a time.
#   results/adversary-2026-11-18/run.sh /path/to/emi-drafting
set -u
here=$(cd "$(dirname "$0")" && pwd)
drafting=$(cd "$1" && pwd)
ls "$drafting/adversary" | xargs -P 3 -I{} sh -c \
  "python3 '$here/../../harness/score_adversary.py' --task {} --tries '$drafting/adversary/{}' \
     --out '$here/out/{}.json' > '$here/out/{}.log' 2>&1; echo \"{} exit \$?\""
