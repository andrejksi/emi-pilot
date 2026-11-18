"""The person's page for an adversary round: per try, one situation and two
outcomes (the fix's, and the one its claim says the bug report means), to
pick which should happen. And the comparison of the picks with the hidden
tests afterwards.

    python3 harness/review_page.py build --drafting DIR --out PAGE --order ORDER
        [--title T] [--collection NAME]
    python3 harness/review_page.py compare --answers DIR --order ORDER --scores DIR
        [--unclear ID...] --out TABLE

build reads emi-drafting adversary/<task>/<try>/question.md (ADVERSARY.md's
format) and writes the page and ORDER, which records for each card which of
A and B is the fix's outcome. The page never says: the order comes from a
hash of the card's id, so neither position means anything and it is the
same on every build. What the program did before the fix is left off the
page: an outcome equal to it would mark the fix's.

compare reads the answers saved from the page (one JSON per card, as the
Artifact tool's ArtifactData list writes them with out_dir), ORDER, and the
scores (score_adversary.py's JSON per task). A pick of the fix's outcome
calls the fix fine; a pick of the other calls it wrong.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "review_page.tmpl.html"
FIELDS = ("Situation", "With this fix", "The other outcome", "Before the fix")


def short(task_id):
    """A card id's project part: the repository name without the PR number."""
    return task_id.split("__", 1)[1].rsplit("-", 1)[0]


def read_question(path):
    lines = dict(l.split(": ", 1) for l in path.read_text().strip().splitlines() if ": " in l)
    missing = [f for f in FIELDS if not lines.get(f, "").strip()]
    if missing:
        raise SystemExit(f"{path}: missing {', '.join(missing)}")
    return lines


def fix_first(card_id):
    return hashlib.sha256(card_id.encode()).digest()[0] % 2 == 0


def cards(drafting):
    items, reports, order = [], {}, {}
    for task_dir in sorted((drafting / "adversary").iterdir()):
        if not task_dir.is_dir():
            continue
        task = json.loads((drafting / "tasks" / task_dir.name / "task.json").read_text())
        prompt = task["prompt"].strip()
        project = short(task_dir.name)
        for q in sorted(task_dir.glob("*/question.md")):
            card_id = f"{project}-{q.parent.name}"
            f = read_question(q)
            pair = [f["With this fix"], f["The other outcome"]]
            keys = ["fix", "other"]
            if not fix_first(card_id):
                pair.reverse()
                keys.reverse()
            order[card_id] = {"task": task_dir.name, "try": q.parent.name,
                              "A": keys[0], "B": keys[1], "before_fix": f["Before the fix"]}
            reports[project] = prompt[:6000]
            items.append({"id": card_id, "project": project, "try": q.parent.name,
                          "bug": prompt.splitlines()[0], "situation": f["Situation"],
                          "shown": pair})
    return items, reports, order


def build(args):
    items, reports, order = cards(args.drafting)
    if not items:
        raise SystemExit(f"no question.md under {args.drafting / 'adversary'}")
    data = {"items": items, "reports": reports, "collection": args.collection}
    page = (TEMPLATE.read_text().replace("__TITLE__", args.title)
            .replace("__DATA__", json.dumps(data).replace("</", "<\\/")))
    args.out.write_text(page)
    args.order.write_text(json.dumps(order, indent=1) + "\n")
    print(f"{len(items)} cards; fix's outcome shown first on "
          f"{sum(o['A'] == 'fix' for o in order.values())}")


def hidden(scores, unclear):
    verdicts = {}
    for f in sorted(scores.glob("*.json")):
        d = json.loads(f.read_text())
        if "tries" not in d or ".again-" in f.name:
            continue
        for k, v in d["tries"].items():
            card_id = f"{short(d['task'])}-{k}"
            verdicts[card_id] = "unclear" if card_id in unclear else v["verdict"]
    return verdicts


def call(answers, order, card_id):
    p = answers / f"{card_id}.json"
    if not p.exists():
        return "unanswered"
    pick = json.loads(p.read_text())["pick"]
    if pick == "unsure":
        return "can't tell"
    return "fine" if order[card_id][pick] == "fix" else "wrong"


def compare(args):
    order = json.loads(args.order.read_text())
    verdicts = hidden(args.scores, set(args.unclear))
    rows, cross = [], Counter()
    for card_id in sorted(order):
        c = call(args.answers, order, card_id)
        h = verdicts.get(card_id, "not scored")
        cross[(h, c)] += 1
        rows.append(f"| {card_id} | {c} | {h} |")
    calls = ("wrong", "fine", "can't tell", "unanswered")
    lines = ["| card | person's call | hidden tests |", "|---|---|---|", *rows, "",
             "| hidden tests \\ person | " + " | ".join(calls) + " |", "|---|---|---|---|---|"]
    for h in sorted({h for h, _ in cross}):
        lines.append(f"| {h} | " + " | ".join(str(cross[(h, c)]) for c in calls) + " |")
    args.out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[len(rows) + 3:]))


def main():
    a = argparse.ArgumentParser()
    sub = a.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--drafting", required=True, type=Path)
    b.add_argument("--out", required=True, type=Path)
    b.add_argument("--order", required=True, type=Path)
    b.add_argument("--title", default="Which Should Happen")
    b.add_argument("--collection", default="picks")
    c = sub.add_parser("compare")
    c.add_argument("--answers", required=True, type=Path)
    c.add_argument("--order", required=True, type=Path)
    c.add_argument("--scores", required=True, type=Path)
    c.add_argument("--unclear", nargs="*", default=[])
    c.add_argument("--out", required=True, type=Path)
    args = a.parse_args()
    build(args) if args.cmd == "build" else compare(args)


if __name__ == "__main__":
    main()
