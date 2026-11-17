"""Make pilot tasks from SWE-rebench-V2 rows (nebius/SWE-rebench-V2 on
Hugging Face), filtered for what the pilot can run.

    pip install pandas pyarrow
    python3 harness/import_swe.py rebench-v2.parquet --since 2025-06-01 --limit 30

Each task gets:
  task.json            repository, base commit, Python, install steps, the
                       visible test files, the prompt, the oracle's test ids
  hidden/test.patch    the tests the real fix added (the oracle)
  replay/gold.patch    the real fix, without its tests
  replay/gold-with-tests.patch  the real fix with its tests, as an agent
                       that also wrote them would leave it
  replay/nothing.patch no change: the oracle must fail it

A row is left out, with the reason counted, when the pilot cannot use it.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

from common import PILOT, TEST_PATH, changed_lines, files_in, write_json
from trees import test_files

def python_of(install_config):
    m = re.search(r"python_base_(\d)(\d+)", install_config.get("base_image_name") or "")
    return f"{m.group(1)}.{m.group(2)}" if m else None


def reason_to_skip(r, since):
    ic = r["install_config"]
    steps = [] if ic.get("install") is None else list(ic["install"])
    cmd = ic.get("test_cmd") or ""
    product = [f for f in files_in(r["patch"]) if not TEST_PATH.search(f)]
    llm = (r["meta"] or {}).get("llm_metadata") or {}
    checks = [
        (r["language"] == "python", "not Python"),
        (str(r["created_at"]) >= since, f"older than {since}"),
        (python_of(ic) is not None, "no Python version"),
        (all(s.strip().startswith("pip install") for s in steps), "install is more than pip"),
        (cmd.startswith("pytest") and " -n " not in cmd and "xdist" not in cmd,
         "tests are not plain serial pytest"),
        (bool(test_files(cmd)), "the test command names no files"),
        (1 <= len(r["FAIL_TO_PASS"]) <= 10, "FAIL_TO_PASS not 1..10"),
        (len(r["PASS_TO_PASS"]) >= 5, "fewer than 5 PASS_TO_PASS"),
        (1 <= len(product) <= 4 and all(f.endswith(".py") for f in product),
         "fix not 1..4 Python product files"),
        (changed_lines(r["patch"]) <= 150, "fix over 150 lines"),
        (llm.get("intent_completeness") == "complete"
         and not any((llm.get("detected_issues") or {}).values()),
         "issue judged incomplete or flawed"),
    ]
    return next((why for ok, why in checks if not ok), None)


def write_task(r):
    ic = r["install_config"]
    d = PILOT / "tasks" / r["instance_id"]
    (d / "hidden").mkdir(parents=True, exist_ok=True)
    (d / "replay").mkdir(parents=True, exist_ok=True)
    prompt = r["problem_statement"].strip()
    if (r.get("interface") or "").strip() not in ("", "No new interfaces are introduced."):
        prompt += "\n\nInterface the change must provide:\n" + r["interface"].strip()
    write_json(d / "task.json", {
        "kind": "git", "source": "nebius/SWE-rebench-V2", "repo": r["repo"],
        "base_commit": r["base_commit"], "created_at": str(r["created_at"]),
        "python": python_of(ic), "install": list(ic["install"]),
        "test_files": test_files(ic["test_cmd"]), "prompt": prompt,
        "oracle": {"fail_to_pass": list(r["FAIL_TO_PASS"]),
                   "pass_to_pass": list(r["PASS_TO_PASS"])},
        "license": r.get("license"),
    })
    (d / "hidden" / "test.patch").write_text(r["test_patch"])
    (d / "replay" / "gold.patch").write_text(r["patch"])
    (d / "replay" / "gold-with-tests.patch").write_text(r["patch"] + r["test_patch"])
    (d / "replay" / "nothing.patch").write_text("")


def main():
    a = argparse.ArgumentParser()
    a.add_argument("parquet")
    a.add_argument("--since", default="2025-06-01", help="oldest creation date to keep")
    a.add_argument("--limit", type=int, default=30, help="newest N usable tasks")
    a.add_argument("--ids", nargs="*", help="only these instance ids")
    a.add_argument("--dry-run", action="store_true")
    args = a.parse_args()
    df = pd.read_parquet(args.parquet)
    if args.ids:
        df = df[df.instance_id.isin(args.ids)]
    df = df.sort_values("created_at", ascending=False)
    skipped, kept = Counter(), []
    for _, r in df.iterrows():
        why = reason_to_skip(r, args.since)
        if why:
            skipped[why] += 1
        elif len(kept) < args.limit:
            kept.append(r)
    for why, n in skipped.most_common():
        print(f"{n:6d} left out: {why}")
    print(f"{len(kept):6d} imported" + (" (dry run)" if args.dry_run else ""))
    for r in kept:
        print(f"  {r['instance_id']}  {str(r['created_at'])[:10]}  {r['repo']}")
        if not args.dry_run:
            write_task(r)


if __name__ == "__main__":
    main()
