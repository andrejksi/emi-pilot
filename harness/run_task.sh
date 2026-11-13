#!/usr/bin/env bash
# Every run of one task, one after another, sharing the task's environment
# (built once). Each run gets a fresh repository; a failed run is reported
# and the others still run.
#
#   harness/run_task.sh MODE SEEDS TASK OUT
#
# MODE is replay or chat. EMI (default `emi`) and VENV (the toy projects'
# virtualenv) come from the environment; chat also needs MODEL_BASE_URL,
# MODEL_NAME and MODEL_API_KEY. Exits 1 if any run failed.
set -uo pipefail

mode="${1:?usage: run_task.sh MODE SEEDS TASK OUT}"
seeds="${2:?}"
task="${3:?}"
out="${4:?}"
here="$(cd "$(dirname "$0")/.." && pwd)"
emi="${EMI:-emi}"
work="${WORK:-$(mktemp -d)}"
failed=0
mkdir -p "$out"

while read -r t arm which; do
  id="$t.$arm.$which"
  echo "::group::$id"
  if python3 "$here/harness/prepare.py" --task "$t" --arm "$arm" --work "$work/$id" \
      ${VENV:+--venv "$VENV"} --emi "$emi"; then
    if [ "$mode" = replay ]; then
      python3 "$here/harness/agent.py" --task "$t" --arm "$arm" --work "$work/$id" \
        --out "$out/$id" --emi "$emi" --backend replay --replay "$which"
    else
      python3 "$here/harness/agent.py" --task "$t" --arm "$arm" --work "$work/$id" \
        --out "$out/$id" --emi "$emi" --backend chat --seed "$which" \
        --base-url "${MODEL_BASE_URL:?}" --model "${MODEL_NAME:?}" --api-key-env MODEL_API_KEY
    fi
    status=$?
  else
    status=1
  fi
  echo "::endgroup::"
  if [ "$status" -ne 0 ]; then
    echo "::error::run $id failed"
    failed=1
  fi
  rm -rf "${work:?}/$id" "$work/$id.emi-state"
done < <(python3 "$here/harness/plan.py" "$mode" --seeds "$seeds" --tasks "$task")

exit "$failed"
