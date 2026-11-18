. ./lib.sh
base $PWD/gitcfg
cat > tests/test_git_env.py <<'P'
import os, subprocess


def test_no_outside_git_settings():
    out = subprocess.run(["git", "config", "--list", "--show-origin"], capture_output=True, text=True).stdout
    env = sorted(k for k in os.environ if k.startswith("GIT_"))
    assert "insteadof" not in out.lower(), out
    assert env == [], env
    assert out.strip() == "", out
P
configure
printf '\n# a comment\n' >> calc.py
done_check
