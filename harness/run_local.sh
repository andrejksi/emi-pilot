#!/usr/bin/env bash
# Run the pilot on this machine: every task x arm, then the oracle and the table.
#
#   harness/run_local.sh replay                      # fixed candidate changes, no model
#   harness/run_local.sh chat SEEDS                  # a live model; needs MODEL_BASE_URL,
#                                                    # MODEL_NAME and MODEL_API_KEY set
#
# EMI (the `emi` binary, or $EMI), bubblewrap, and a virtualenv with
# pytest<9, coverage>=7.9 and hypothesis at $VENV are needed.
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
mode="${1:?usage: run_local.sh replay|chat [SEEDS]}"
seeds="${2:-1}"
emi="${EMI:-emi}"
venv="${VENV:?set VENV to a virtualenv with pytest, coverage and hypothesis}"
jobs="${JOBS:-2}"
out="${OUT:-$here/runs/$(date -u +%Y%m%dT%H%M%SZ)-$mode}"
mkdir -p "$out/work"

plan="$out/plan.txt"
python3 "$here/harness/plan.py" "$mode" --seeds "$seeds" ${TASKS:+--tasks $TASKS} >"$plan"

one() {
  read -r task arm which <<<"$1"
  id="$task.$arm.$which"
  work="$out/work/$id"
  python3 "$here/harness/prepare.py" --task "$task" --arm "$arm" --work "$work" \
    --venv "$venv" --emi "$emi"
  if [ "$mode" = replay ]; then
    python3 "$here/harness/agent.py" --task "$task" --arm "$arm" --work "$work" \
      --out "$out/$id" --emi "$emi" --backend replay --replay "$which"
  else
    python3 "$here/harness/agent.py" --task "$task" --arm "$arm" --work "$work" \
      --out "$out/$id" --emi "$emi" --backend chat --seed "$which" \
      --base-url "${MODEL_BASE_URL:?}" --model "${MODEL_NAME:?}" --api-key-env MODEL_API_KEY
  fi
  echo "done $id"
}
export -f one
export here out venv emi mode

# a failed run stops nothing else, and is reported at the end
xargs -P "$jobs" -I{} bash -c 'one "$@" || echo "FAILED {}"' _ {} <"$plan" | tee "$out/log.txt"

python3 "$here/harness/oracle.py" --venv "$venv" --run $(ls -d "$out"/*/ | grep -v '/work/$')
python3 "$here/harness/table.py" --by-run "$out"/*/ | tee "$out/table.md"
if grep -q '^FAILED' "$out/log.txt"; then
  echo "some runs failed (see $out/log.txt)" >&2
  exit 1
fi
