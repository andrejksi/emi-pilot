#!/usr/bin/env bash
# Replay the first drafting study's drafts through the new `emi rules check`:
# each task's first and final drafts, a fresh state directory each, and the
# final drafts once more with the state kept (remembered stand-in results).
set -u
D=/tmp/claude-0/-home-user/5eb0ad45-fb5d-502b-baac-1e9e75db553c/scratchpad
EMI=$D/replay/emi
DRAFTS=/home/user/emi-drafting/drafts
OUT=$D/replay/out
mkdir -p "$OUT"
for t in $(ls "$DRAFTS"); do
  w=$D/drafting-repo/work/$t
  final=$(ls -d "$DRAFTS/$t/checked" "$DRAFTS/$t/last" 2>/dev/null | head -1)
  for v in first final final-again; do
    case $v in
      first) src=$DRAFTS/$t/first ;;
      *) [ -n "$final" ] || continue; src=$final ;;
    esac
    state=$OUT/state-$t-${v%-again}
    [ "$v" = final-again ] || rm -rf "$state"
    rm -rf "$w/.emi/laws" && mkdir -p "$w/.emi/laws" && cp -r "$src"/. "$w/.emi/laws/"
    start=$(date +%s.%N)
    XDG_STATE_HOME=$state timeout 7200 "$EMI" rules check --repo "$w" --format json > "$OUT/$t.$v.json" 2> "$OUT/$t.$v.err"
    code=$?
    end=$(date +%s.%N)
    printf '%s\t%s\t%s\t%.1f\n' "$t" "$v" "$code" "$(echo "$end - $start" | bc)" | tee -a "$OUT/times.tsv"
  done
  rm -rf "$w/.emi/laws"
done
