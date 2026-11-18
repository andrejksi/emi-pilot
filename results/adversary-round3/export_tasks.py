import json, sys
from pathlib import Path
sys.path.insert(0, "/home/user/emi-pilot/harness")
from trees import baseline_tree
out = Path(sys.argv[1])
for tid in sys.argv[2:]:
    t = json.loads(Path(f"/home/user/emi-pilot/tasks/{tid}/task.json").read_text())
    t["id"] = tid
    d = out / tid
    baseline_tree(t, d / "code")
    (d / "task.json").write_text(json.dumps({k: t[k] for k in ("prompt", "install", "test_files")}, indent=2) + "\n")
    print(tid, "ok", flush=True)
