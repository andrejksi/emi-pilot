"""One row per task and version of the rerun, beside the study's own check."""
import json, re, sys
from pathlib import Path
OUT = Path(sys.argv[1])
DRAFTS = Path("/home/user/emi-drafting/drafts")
times = {}
for line in (OUT / "times.tsv").read_text().splitlines():
    t, v, code, secs = line.split("\t")
    times[t, v] = (code, float(secs))
def study(t, which):
    files = sorted((DRAFTS / t / "checks").iterdir(), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    f = files[0] if which == "first" else files[-1]
    head = f.read_text()[:400]
    ex = re.search(r"exit (\d+)", head); took = re.search(r"took (\d+)s", head); act = re.search(r"check: (\w+)", head)
    return f"{act.group(1) if act else '?'} (exit {ex.group(1) if ex else '?'}{', ' + took.group(1) + ' s' if took else ''})"
print("| task | draft | study | now | s | send-backs | notes | not checked | reused |")
print("|---|---|---|---|---|---|---|---|---|")
for (t, v), (code, secs) in times.items():
    try:
        r = json.loads((OUT / f"{t}.{v}.json").read_text())
    except Exception as e:
        print(f"| {t} | {v} | | no JSON ({type(e).__name__}), exit {code} | {secs:.0f} | | | | |"); continue
    nm = len(r.get("not_measured") or []) + sum(len(f.get("not_measured") or []) for f in r["files"])
    notes = r.get("notes") or []
    reused = next((n for n in notes if "kept" in n or "reused" in n or "earlier" in n), "")
    m = re.search(r"(\d+)", reused)
    old = study(t, "first" if v == "first" else "last") if v != "final-again" else ""
    print(f"| {t.split('__')[1]} | {v} | {old} | {r['action']} (exit {code}) | {secs:.0f} | {len(r.get('repair') or [])} | {len(notes)} | {nm} | {m.group(1) if m else ''} |")
