#!/usr/bin/env bash
# try.sh TASK ATTEMPT: run the task's final drafted rules on one attempt with plain pytest
set -u
S=/tmp/claude-0/-home-user/5eb0ad45-fb5d-502b-baac-1e9e75db553c/scratchpad
t=$1; a=$2
R=/home/user/emi-pilot/results/harvest-tuning/runs
D=/home/user/emi-drafting/drafts/$t
final=$(ls -d $D/checked $D/last 2>/dev/null | head -1)
w=$S/adv/w/$t.$a
rm -rf $w; mkdir -p $S/adv/w; git -C $S/drafting-repo/work/$t worktree prune
git -C $S/drafting-repo/work/$t worktree add -q --detach $w main 2>/dev/null || { echo worktree failed; exit 2; }
ln -s $S/drafting-repo/envs/$t $w/.venv
if [ "$a" != baseline ]; then git -C $w apply --whitespace=nowarn $R/$t.$a/candidate.diff || { echo apply failed; exit 2; }; fi
mkdir -p $w/.emi/laws; cp -r $final/. $w/.emi/laws/
cd $w && timeout 900 .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts= .emi/laws 2>&1 | tail -25
