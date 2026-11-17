"""Find task candidates in pull requests merged after a date: fixes whose
models could not have seen them, because every model that writes changes or
drafts laws was released before that date. SWE-rebench-V2 has no Python task
newer than July 2025, so held-out tasks are mined here instead.

    GITHUB_TOKEN=... python3 harness/mine_prs.py --since 2026-10-24 \
        --repos @tasks --per-repo 3 --out candidates.jsonl

`@tasks` stands for the repositories of the pilot's git tasks: their install
steps are known to build. A candidate is a merged pull request that

  - closes an issue opened before the pull request, whose text says enough
    (at least --min-issue characters once templates and comments are cut),
  - was not opened by a bot,
  - changes tests, and 1 to 4 Python files that are not tests, in at most
    150 changed lines (the same limits as import_swe.py),

and its base is the first parent of its merge commit: the default branch
just before the fix landed. No language model judges anything here; what the
filters let through is checked by running it (validate_pr.py).

A pull request left out is counted with its reason, and nothing about its
fix is printed, so whoever runs this has not read the held-out answers.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

from common import PILOT, TEST_PATH, changed_lines, files_in, run
from trees import mirror

API = "https://api.github.com/graphql"
PAGE = 40
PAGES_MAX = 25  # 1000 pull requests per repository, newest first
FILES_MAX = 100

QUERY = """
query($owner: String!, $name: String!, $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: MERGED, first: %d, after: $after,
                 orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number title createdAt mergedAt updatedAt
        author { login __typename }
        mergeCommit { oid parents(first: 1) { nodes { oid } } }
        closingIssuesReferences(first: 5) {
          nodes { number title body createdAt repository { nameWithOwner } }
        }
        files(first: %d) { totalCount nodes { path } }
      }
    }
  }
}
""" % (PAGE, FILES_MAX)

TEMPLATE_NOISE = re.compile(r"<!--.*?-->|^#+ .*$|^\s*[-*] \[[ xX]\].*$", re.S | re.M)


def graphql(query, variables, token):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        "User-Agent": "emi-pilot-miner"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        out = json.loads(resp.read())
    if out.get("errors"):
        raise SystemExit(f"GitHub API: {out['errors']}")
    return out["data"]


def merged_since(repo, since, token):
    """Merged pull requests updated since `since`, newest first; a pull
    request merged before `since` but updated later is dropped by the caller."""
    owner, name = repo.split("/")
    after = None
    for _ in range(PAGES_MAX):
        conn = graphql(QUERY, {"owner": owner, "name": name, "after": after},
                       token)["repository"]["pullRequests"]
        for pr in conn["nodes"]:
            if pr["updatedAt"][:10] < since:
                return
            yield pr
        if not conn["pageInfo"]["hasNextPage"]:
            return
        after = conn["pageInfo"]["endCursor"]
    print(f"{repo}: stopped after {PAGES_MAX} pages", file=sys.stderr)


def issue_words(text):
    """An issue's text without its template: comments, headings, checkboxes."""
    return re.sub(r"\s+", " ", TEMPLATE_NOISE.sub(" ", text or "")).strip()


def the_issue(pr, repo):
    """The one issue in the same repository the pull request closes, or None."""
    issues = [i for i in pr["closingIssuesReferences"]["nodes"]
              if i["repository"]["nameWithOwner"].lower() == repo.lower()]
    return issues[0] if len(issues) == 1 else None


def reason_to_skip(pr, repo, since, min_issue):
    issue = the_issue(pr, repo)
    author = pr["author"] or {}
    files = [f["path"] for f in pr["files"]["nodes"]]
    product = [f for f in files if not TEST_PATH.search(f)]
    checks = [
        (pr["mergedAt"][:10] >= since, f"merged before {since}"),
        (author.get("__typename") != "Bot" and not author.get("login", "").endswith("[bot]"),
         "opened by a bot"),
        (pr["mergeCommit"] is not None and pr["mergeCommit"]["parents"]["nodes"],
         "no merge commit"),
        (pr["files"]["totalCount"] <= FILES_MAX, f"more than {FILES_MAX} files"),
        (any(TEST_PATH.search(f) for f in files), "changes no tests"),
        (1 <= len(product) <= 4 and all(f.endswith(".py") for f in product),
         "fix not 1..4 Python product files"),
        (issue is not None, "closes no single issue in the repository"),
        (issue is None or issue["createdAt"] <= pr["createdAt"],
         "issue opened after the pull request"),
        (issue is None or len(issue_words(issue["body"])) >= min_issue,
         f"issue text under {min_issue} characters"),
    ]
    return next((why for ok, why in checks if not ok), None)


def split_patch(git_dir, base, head):
    """The fix and its tests, as two patches from base to head."""
    code, out = run(["git", "--git-dir", str(git_dir), "diff", "--binary", "--no-renames",
                     base, head], cwd=PILOT, timeout=1800)
    if code != 0:
        raise RuntimeError(f"git diff {base}..{head} failed: {out[-1000:]}")
    pieces = re.split(r"(?m)^(?=diff --git )", out)
    fix, tests = [], []
    for piece in filter(None, pieces):
        path = files_in(piece)
        (tests if path and TEST_PATH.search(path[0]) else fix).append(piece)
    return "".join(fix), "".join(tests)


def candidate(pr, repo):
    issue = the_issue(pr, repo)
    base = pr["mergeCommit"]["parents"]["nodes"][0]["oid"]
    head = pr["mergeCommit"]["oid"]
    git_dir = mirror({"repo": repo, "base_commit": head})
    fix, tests = split_patch(git_dir, base, head)
    return {
        "instance_id": f"{repo.replace('/', '__')}-{pr['number']}",
        "repo": repo, "pull": pr["number"], "issue": issue["number"],
        "base_commit": base, "merge_commit": head, "merged_at": pr["mergedAt"],
        "problem_statement": f"{issue['title']}\n\n{(issue['body'] or '').strip()}\n",
        "patch": fix, "test_patch": tests,
    }


def task_repos():
    """The repositories of the pilot's git tasks."""
    repos = set()
    for f in (PILOT / "tasks").glob("*/task.json"):
        t = json.loads(f.read_text())
        if t.get("kind") == "git":
            repos.add(t["repo"])
    return sorted(repos)


def size_reason(c):
    if not c["test_patch"]:
        return "changes no tests"
    if changed_lines(c["patch"]) > 150:
        return "fix over 150 lines"
    return None


def seen():
    """Pull requests someone has read (batches/seen.txt): never held out."""
    f = PILOT / "batches" / "seen.txt"
    lines = f.read_text().splitlines() if f.exists() else []
    return {x.strip() for x in lines if x.strip() and not x.startswith("#")}


def mine_repo(repo, args, token, skipped):
    kept, read = [], seen()
    for pr in merged_since(repo, args.since, token):
        why = reason_to_skip(pr, repo, args.since, args.min_issue)
        if f"{repo.replace('/', '__')}-{pr['number']}" in read:
            why = "read while testing the miner (batches/seen.txt)"
        if why is None and len(kept) < args.per_repo:
            c = candidate(pr, repo)
            why = size_reason(c)
            if why is None:
                kept.append(c)
                continue
        skipped[why or "over the per-repository cap"] += 1
    return kept


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--since", required=True, help="YYYY-MM-DD: oldest merge date to keep")
    a.add_argument("--repos", nargs="+", default=["@tasks"])
    a.add_argument("--per-repo", type=int, default=3)
    a.add_argument("--min-issue", type=int, default=300)
    a.add_argument("--out", required=True)
    args = a.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("set GITHUB_TOKEN: the GitHub API reads the pull requests and issues")
    repos = [r for x in args.repos for r in (task_repos() if x == "@tasks" else [x])]
    skipped, rows = Counter(), []
    for repo in repos:
        kept = mine_repo(repo, args, token, skipped)
        rows += kept
        print(f"{len(kept):3d} kept  {repo}")
    for why, n in skipped.most_common():
        print(f"{n:6d} left out: {why}")
    print(f"{len(rows):6d} candidates")
    with open(args.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
