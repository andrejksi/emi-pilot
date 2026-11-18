"""Set the person's answers beside the fixes and the hidden tests.

    python3 compare.py   (from this directory; writes table.md)
"""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
fix = json.loads((HERE / "fix_answers.json").read_text())
# trino 2 and 3: their only hidden failure also fails a fix the hidden
# tests passed before (see ../README.md), so the hidden tests do not decide them
UNCLEAR = {"trino-2", "trino-3"}


def hidden():
    verdicts = {}
    for f in sorted(OUT.glob("*.json")):
        if ".again-" in f.name:
            continue
        d = json.loads(f.read_text())
        short = d["task"].split("__")[1].rsplit("-", 1)[0]
        short = {"trino-python-client": "trino", "python-markdownify": "markdownify",
                 "sdk": "meltano"}.get(short, short)
        for k, v in d["tries"].items():
            tid = f"{short}-{k}"
            verdicts[tid] = "unclear" if tid in UNCLEAR else v["verdict"]
    return verdicts


def person(tid):
    p = HERE / "answers" / f"{tid}.json"
    if not p.exists():
        return "unanswered", None
    a = json.loads(p.read_text())
    a = a.get("data", a)["answer"]
    if a == "unsure":
        return "can't tell", a
    return ("fine" if a == fix[tid] else "wrong"), a


def main():
    h = hidden()
    rows, cross = [], Counter()
    for tid in sorted(h):
        call, ans = person(tid)
        cross[(h[tid], call)] += 1
        rows.append(f"| {tid} | {ans or '-'} | {fix[tid]} | {call} | {h[tid]} |")
    lines = ["| try | person answered | fix gives | person's call | hidden tests |",
             "|---|---|---|---|---|", *rows, "",
             "| hidden tests \\ person | wrong | fine | can't tell | unanswered |",
             "|---|---|---|---|---|"]
    for hv in ("gap", "not_wrong", "unclear"):
        lines.append(f"| {hv} | " + " | ".join(str(cross[(hv, c)]) for c in
                     ("wrong", "fine", "can't tell", "unanswered")) + " |")
    (HERE / "table.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-5:]))


if __name__ == "__main__":
    main()
