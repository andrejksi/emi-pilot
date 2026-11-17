"""Have a model draft a task's laws before any code is written, the way
`emi rules brief` tells an agent to, and keep the draft twice: as first
written, and as it stood when `emi rules check` last passed it.

The model is the proposer. The person it would ask is played by the task
text: what the text says is the answer, and anything it does not say is
"doesn't matter". The model reads the code at the baseline, as any agent
does, and writes only under the laws directory; nothing else it changes is
kept. A person approves the checked draft afterwards, outside this script.

    python3 harness/draft_laws.py --task T --work DIR --out DIR --emi EMI \
        --base-url URL --model NAME --api-key-env MODEL_API_KEY --seed 1

DIR is a repository prepare.py laid out for the `cooperative` arm. Writes,
in --out:
  draft.json        what happened: each check's exit, the outcome, usage
  laws/first/       the laws directory at the first check
  laws/checked/     the laws directory at the last check that passed
  checks/<n>.txt    what each check printed, as the model and the person see it
  transcript.json   the conversation
"""

import argparse
import json
import os
import shutil
import time
from pathlib import Path

from agent import TOOLS, chat, inside, tool
from common import load_task, run, write_json
from trees import code_env, test_command

LAWS = ".emi/laws"

SYSTEM = (
    "You are a coding agent working in a git repository. Before anyone writes "
    "code for the task you are given, its rules are agreed and written as tests. "
    "In this job you write only the rules: read any file and run any command, "
    "but write files only under " + LAWS + ". The project's tests run with `{tests}`."
)

STAND_IN = (
    "The person cannot answer questions in this job. Their answers are the task "
    "text below: take what it states as their answer, and where it says nothing, "
    "the answer is \"doesn't matter\". In place of running `emi rules check` "
    "yourself, call the `check_rules` tool: it runs the check and shows what it "
    "printed. Fix what it sends back and call it again. When it exits 0, call "
    "`finish`. Do not write code for the task itself."
)

CHECK_TOOL = {"type": "function", "function": {
    "name": "check_rules",
    "description": "Run `emi rules check` on the rules drafted in " + LAWS + " and show what it printed.",
    "parameters": {"type": "object", "properties": {}}}}

FINISH_UNCHECKED = (
    "The rules as they stand have not passed `check_rules`. This is what it "
    "prints for them; fix it, then call `finish` again:\n"
)


def tools():
    """The agent's tools, with writing confined to the laws directory."""
    out = []
    for t in TOOLS:
        if t["function"]["name"] == "write_file":
            t = json.loads(json.dumps(t))
            t["function"]["description"] = f"Write a whole file; only under {LAWS}."
        out.append(t)
    return out + [CHECK_TOOL]


def write_law(work, args):
    path = inside(work, args["path"])
    laws = (Path(work) / LAWS).resolve()
    if laws not in path.parents:
        raise ValueError(f"this job writes only under {LAWS}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args["content"])
    return f"wrote {args['path']}"


def laws_now(work):
    """Each file the draft adds or changes under the laws directory, and its
    content; laws the baseline already has are not the draft's."""
    _, out = run(["git", "status", "--porcelain", "--untracked-files=all", "--", LAWS],
                 cwd=work, check=True)
    root = Path(work) / LAWS
    files = {}
    for line in out.splitlines():
        path = Path(work) / line[3:]
        if path.is_file() and "__pycache__" not in path.parts:
            files[str(path.relative_to(root))] = path.read_text(errors="replace")
    return dict(sorted(files.items()))


def keep(files, dest):
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    for rel, text in files.items():
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        (dest / rel).write_text(text)


class Checks:
    """Every `emi rules check`, and the drafts it saw."""

    def __init__(self, work, out, emi):
        self.work, self.out, self.emi = work, Path(out), emi
        self.state = Path(work).parent / (Path(work).name + ".emi-state")
        self.rounds, self.passed = [], None

    def run(self):
        files = laws_now(self.work)
        if not self.rounds:
            keep(files, self.out / "laws" / "first")
        started = time.monotonic()
        code, text = run([self.emi, "rules", "check", "--format", "text"], cwd=self.work,
                         env={"XDG_STATE_HOME": str(self.state)}, timeout=3600)
        n = len(self.rounds)
        (self.out / "checks").mkdir(parents=True, exist_ok=True)
        (self.out / "checks" / f"{n}.txt").write_text(text)
        self.rounds.append({"exit": code, "files": sorted(files),
                            "seconds": round(time.monotonic() - started, 1)})
        if code == 0:
            self.passed = files
            keep(files, self.out / "laws" / "checked")
        return code, text

    def current(self):
        """Whether the drafts on disk are the ones the last passing check saw."""
        return self.passed is not None and self.passed == laws_now(self.work)


def call_tool(args, task, checks, name, fargs):
    if name == "check_rules":
        code, text = checks.run()
        return f"exit {code}\n{text[-12000:]}"
    if name == "write_file":
        return write_law(args.work, fargs)
    return tool(args.work, name, fargs, args.api_key_env, code_env(task, args.work))


def at_finish(checks, max_checks):
    """None when the agent may stop; else what to send it back with."""
    if checks.current():
        return None
    if not laws_now(checks.work):
        return "There are no rules under " + LAWS + " yet. Write them, check them, then finish."
    if len(checks.rounds) >= max_checks:
        return None
    code, text = checks.run()
    return None if code == 0 else FINISH_UNCHECKED + text[-12000:]


def draft(args, task, checks, usage):
    key = os.environ.get(args.api_key_env)
    if not key:
        raise SystemExit(f"{args.api_key_env} is not set: nothing would be measured")
    brief = run([args.emi, "rules", "brief"], cwd=args.work, check=True)[1]
    messages = [{"role": "system", "content": SYSTEM.format(tests=" ".join(test_command(task)))},
                {"role": "user", "content": f"{brief}\n{STAND_IN}\n\nThe task:\n\n{task['prompt']}"}]
    for _ in range(args.max_steps):
        body = {"model": args.model, "messages": messages, "tools": tools(),
                "temperature": args.temperature, "seed": args.seed}
        reply = chat(args.base_url, key, body)
        for k in ("prompt_tokens", "completion_tokens"):
            usage[k] += (reply.get("usage") or {}).get(k, 0)
        msg = reply["choices"][0]["message"]
        messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
        calls = msg.get("tool_calls") or []
        finished = not calls
        for call in calls:
            name = call["function"]["name"]
            try:
                fargs = json.loads(call["function"].get("arguments") or "{}")
                result = "ok" if name == "finish" else call_tool(args, task, checks, name, fargs)
            except Exception as e:  # the model sees its own tool errors
                result = f"error: {e}"
            finished = finished or name == "finish"
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
        if finished:
            back = at_finish(checks, args.max_checks)
            if back is None:
                return messages, "ready" if checks.current() else "not_ready"
            messages.append({"role": "user", "content": back})
    return messages, "gave_up"


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--task", required=True)
    a.add_argument("--work", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--emi", default="emi")
    a.add_argument("--base-url", required=True)
    a.add_argument("--model", required=True)
    a.add_argument("--api-key-env", default="MODEL_API_KEY")
    a.add_argument("--seed", type=int, default=1)
    a.add_argument("--temperature", type=float, default=0.2)
    a.add_argument("--max-steps", type=int, default=60)
    a.add_argument("--max-checks", type=int, default=8)
    args = a.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    task = load_task(args.task)
    checks = Checks(args.work, out, args.emi)
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    started = time.monotonic()
    messages, final = draft(args, task, checks, usage)
    if not checks.rounds and laws_now(args.work):
        keep(laws_now(args.work), out / "laws" / "first")  # finished without checking
    write_json(out / "transcript.json", messages)
    write_json(out / "draft.json", {
        "task": args.task, "model": args.model, "seed": args.seed, "final": final,
        "checks": checks.rounds, "usage": usage,
        "seconds": round(time.monotonic() - started, 1),
    })


if __name__ == "__main__":
    main()
