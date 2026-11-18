. ./lib.sh
base $PWD/renamed; configure
python3 - <<'P'
p="calc.py"; s=open(p).read().replace("    return sum(xs) / len(xs)","    if not xs:\n        return 0\n    return sum(xs) / len(xs)"); open(p,"w").write(s)
P
mv tests/test_calc.py tests/test_calculator.py
printf '\n\ndef test_mean_empty():\n    assert mean([]) == 0\n' >> tests/test_calculator.py
git status --short | grep -v pycache
.venv/bin/python -m pytest -q tests 2>&1 | tail -1
done_check
