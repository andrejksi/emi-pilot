"""Lay out round 3's questions for the question page, the same way every run.

Run in emi-drafting, with origin/claude/round3-old and -new fetched. For
each task in round3/tasks.txt it takes both arms' questions.json, shuffles
them together (random.Random(20261118), drawn task by task in that order)
and numbers them q001... Writes OUT/ops.json (the page's `tasks` and
`questions` documents) and OUT/question-map.json (qid -> arm, task,
drafter's id), which stays out of sight until the person has answered.
"""
import json, random, subprocess, sys
from collections import Counter

def show(ref, path):
    r = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None

def main(out):
    rng = random.Random(20261118)
    ops, mapping, n = [], {}, 0
    for t in open("round3/tasks.txt").read().split():
        prompt = json.load(open(f"tasks/{t}/task.json"))["prompt"]
        ops.append({"collection": "tasks", "doc_id": t,
                    "data": {"name": t.split("__", 1)[1], "report": prompt}})
        items = []
        for arm in ("old", "new"):
            s = show(f"origin/claude/round3-{arm}", f"drafts3/{arm}/{t}/questions.json")
            if s is None:
                sys.exit(f"no questions.json: {arm} {t}")
            items += [(arm, q) for q in json.loads(s)]
        rng.shuffle(items)
        for arm, q in items:
            n += 1
            qid = f"q{n:03d}"
            sug = q.get("suggested")
            ops.append({"collection": "questions", "doc_id": qid, "data": {
                "task": t, "order": n, "situation": q["situation"], "question": q["question"],
                "options": q["options"], "suggested": sug if sug in q["options"] else None}})
            mapping[qid] = {"arm": arm, "task": t, "q": q["id"]}
    json.dump(ops, open(f"{out}/ops.json", "w"))
    json.dump(mapping, open(f"{out}/question-map.json", "w"), indent=1)
    print(n, "questions", dict(Counter(m["arm"] for m in mapping.values())))

if __name__ == "__main__":
    main(sys.argv[1])
