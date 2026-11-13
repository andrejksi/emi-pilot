"""Run one agent on one prepared repository under one arm, and write the
run's record and its final diff.

Backends:
  replay  write a fixed candidate change (tasks/<task>/replay/<name>/) and
          ask the gate once. No model; this is the offline replay.
  chat    a model behind an OpenAI-compatible chat completions endpoint,
          with tools to list, read and write files, run commands and finish.

    python3 harness/agent.py --task calc-median --arm strict --work DIR \
        --out runs/calc-median.strict.1 --backend chat \
        --base-url https://... --model NAME --api-key-env MODEL_API_KEY --seed 1
"""

import argparse
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from common import ARMS, PILOT, candidate_diff, copy_tree, load_task, run, write_json
from gates import GATES, REPAIR_ROUNDS
from trees import CACHE, code_env, test_command

SYSTEM = (
    "You are a coding agent working in a git repository. Use the tools to read "
    "and change files and to run commands (the project's tests run with "
    "`{tests}`). When the task is done, call `finish`."
)

TOOLS = [
    {"type": "function", "function": {
        "name": "list_files", "description": "List the repository's files.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "read_file", "description": "Read a file.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                       "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file", "description": "Write a whole file.",
        "parameters": {"type": "object",
                       "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                       "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "run", "description": "Run a shell command in the repository.",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}},
                       "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "finish", "description": "Say the task is done.",
        "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}}}},
]


class Gate:
    """Counts claims of completion and repair rounds, and keeps the history."""

    def __init__(self, arm, work, ctx):
        self.arm, self.work, self.ctx = arm, work, ctx
        self.claims, self.repairs = [], 0

    def claim(self):
        verdict, feedback, record = GATES[self.arm](self.work, self.ctx)
        record["verdict"] = verdict
        self.claims.append(record)
        if verdict == "repair":
            self.repairs += 1
            if self.repairs > REPAIR_ROUNDS:
                return "not_verified", None
        return verdict, feedback


def inside(work, path):
    p = (Path(work) / path).resolve()
    if Path(work).resolve() not in p.parents and p != Path(work).resolve():
        raise ValueError(f"{path} is outside the repository")
    return p


def scrubbed_env(secret_name, extra=None):
    """The agent's commands do not see the model key or other credentials;
    `extra` (the project's import roots) is added."""
    words = ("KEY", "TOKEN", "SECRET", "PASSWORD")
    env = {k: v for k, v in os.environ.items()
           if k != secret_name and not any(w in k.upper() for w in words)}
    return {**env, **(extra or {})}


def sealed(work, command):
    """The agent's command with no network, and with the whole pilot hidden
    (the hidden tests, every run's records, the cached clones that hold the
    commits after the baseline), except its own repository and, read-only,
    the environment its tests run in."""
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise SystemExit("the chat backend needs bubblewrap to seal the agent's commands")
    w = Path(work).resolve()
    venv = (w / ".venv").resolve()
    cmd = [bwrap, "--dev-bind", "/", "/", "--unshare-net", "--die-with-parent"]
    for hidden in (PILOT, CACHE):
        if hidden.exists():
            cmd += ["--tmpfs", str(hidden)]
    if venv.exists() and any(h in venv.parents for h in (PILOT, CACHE)):
        env_home = venv.parent  # a git task's environment and the source it installed from
        cmd += ["--ro-bind", str(env_home), str(env_home)]
    cmd += ["--bind", str(w), str(w), "--chdir", str(w), "bash", "-c", command]
    return cmd


def tool(work, name, args, secret_name, extra_env=None):
    if name == "list_files":
        return run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=work)[1]
    if name == "read_file":
        return inside(work, args["path"]).read_text()[:20000]
    if name == "write_file":
        p = inside(work, args["path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(args["content"])
        return f"wrote {args['path']}"
    if name == "run":
        try:
            p = subprocess.run(sealed(work, args["command"]), cwd=work, capture_output=True,
                               text=True, timeout=300, env=scrubbed_env(secret_name, extra_env))
            return f"exit {p.returncode}\n{(p.stdout + p.stderr)[-8000:]}"
        except subprocess.TimeoutExpired:
            return "timed out after 300 s"
    raise ValueError(f"no tool {name}")


def chat(url, key, body):
    req = urllib.request.Request(
        url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise RuntimeError(f"model endpoint: HTTP {e.code}: {e.read()[:500]!r}")
        time.sleep(5 * 2 ** attempt)
    raise RuntimeError("unreachable")


def chat_backend(args, task, gate, usage):
    key = os.environ.get(args.api_key_env)
    if not key:
        raise SystemExit(f"{args.api_key_env} is not set: nothing would be measured")
    system = SYSTEM.format(tests=" ".join(test_command(task)))
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": task["prompt"]}]
    for _ in range(args.max_steps):
        body = {"model": args.model, "messages": messages, "tools": TOOLS,
                "temperature": args.temperature, "seed": args.seed}
        reply = chat(args.base_url, key, body)
        for k in ("prompt_tokens", "completion_tokens"):
            usage[k] += (reply.get("usage") or {}).get(k, 0)
        msg = reply["choices"][0]["message"]
        messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
        calls = msg.get("tool_calls") or []
        finished = not calls  # a reply with no tool call is a claim of completion
        for call in calls:
            name = call["function"]["name"]
            try:
                fargs = json.loads(call["function"].get("arguments") or "{}")
                result = "ok" if name == "finish" else tool(args.work, name, fargs, args.api_key_env,
                                                             code_env(task, args.work))
            except Exception as e:  # the model sees its own tool errors
                result = f"error: {e}"
            finished = finished or name == "finish"
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
        if finished:
            verdict, feedback = gate.claim()
            if verdict != "repair":
                return verdict
            messages.append({"role": "user", "content": feedback})
    return "gave_up"


def replay_backend(args, task, gate, usage):
    replay = PILOT / "tasks" / args.task / "replay"
    patch = replay / f"{args.replay}.patch"
    if patch.exists():
        if patch.stat().st_size:
            code, out = run(["git", "apply", "--binary", str(patch)], cwd=args.work)
            if code != 0:
                raise SystemExit(f"{patch.name} does not apply: {out[-1000:]}")
    else:
        copy_tree(replay / args.replay, args.work)
    verdict, _ = gate.claim()
    return "flagged" if verdict == "repair" else verdict  # no agent to go back to


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--task", required=True)
    a.add_argument("--arm", required=True, choices=ARMS)
    a.add_argument("--work", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--emi", default="emi")
    a.add_argument("--backend", choices=("replay", "chat"), required=True)
    a.add_argument("--replay")
    a.add_argument("--base-url")
    a.add_argument("--model")
    a.add_argument("--api-key-env", default="MODEL_API_KEY")
    a.add_argument("--seed", type=int, default=0)
    a.add_argument("--temperature", type=float, default=0.2)
    a.add_argument("--max-steps", type=int, default=150)
    args = a.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    task = load_task(args.task)
    ctx = {"emi": args.emi, "out_dir": str(out), "task": task}
    gate = Gate(args.arm, args.work, ctx)
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    started = time.monotonic()
    backend = replay_backend if args.backend == "replay" else chat_backend
    final = backend(args, task, gate, usage)
    (out / "candidate.diff").write_text(candidate_diff(args.work))
    write_json(out / "run.json", {
        "task": args.task, "arm": args.arm,
        "backend": args.backend, "replay": args.replay, "model": args.model,
        "seed": args.seed, "final": final, "claims": gate.claims,
        "repair_rounds": gate.repairs, "usage": usage,
        "seconds": round(time.monotonic() - started, 1),
    })


if __name__ == "__main__":
    main()
