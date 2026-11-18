import sys, importlib, itertools
sys.path.insert(0, sys.argv[1])
from markdownify import markdownify as md
atoms = ["x", "`", "``", " ", "a`b", "`a", "a`", "*", "<b>y</b>", "<code>z</code>", "<code>`q`</code>"]
cases = set()
for n in (1, 2, 3):
    for combo in itertools.product(atoms, repeat=n):
        cases.add("<code>" + "".join(combo) + "</code>")
for tag in ("kbd", "samp"):
    cases.add(f"<{tag}>a`b</{tag}>")
cases.add("<p>see <code>a`b</code> here</p>")
out = {}
for c in sorted(cases):
    try:
        out[c] = repr(md(c))
    except Exception as e:
        out[c] = "raised " + type(e).__name__
import json; print(json.dumps(out))
