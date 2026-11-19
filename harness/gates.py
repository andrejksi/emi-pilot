"""What each arm does when the agent says it is finished.

A gate returns (verdict, feedback, record):
  verdict  "accepted"  the agent may stop
           "repair"    send the agent back with `feedback`
           "flagged"   the run ends without a pass: a person must look
                       (EMI's ask_person and incomplete)
"""

import json
from pathlib import Path

import reviewer
from common import run
from trees import code_env, test_command

REPAIR_ROUNDS = 3  # the same budget for the naive hook and EMI's default


def control(work, ctx):
    return "accepted", None, {"gate": "none"}


def naive(work, ctx):
    """The cheapest stop hook there is: the visible tests must pass."""
    code, out = run(test_command(ctx["task"], work), cwd=work, env=code_env(ctx["task"], work),
                     timeout=1200)
    record = {"gate": "pytest", "exit": code}
    if code == 0:
        return "accepted", None, record
    return "repair", "The tests fail. Fix this, then finish again:\n" + out[-4000:], record


def check(work, ctx, approve=()):
    """One `emi done`; returns (exit code, receipt or None, raw output)."""
    state = Path(work).parent / (Path(work).name + ".emi-state")
    cmd = [ctx["emi"], "done", "--format", "json"]
    for item in approve:
        cmd += ["--approve", item]
    code, out = run(cmd, cwd=work, env={"XDG_STATE_HOME": str(state)}, timeout=1200)
    try:
        receipt = json.loads(out[out.index("{"):])
    except ValueError:
        return code, None, out
    n = len(ctx.setdefault("receipts", []))
    receipt_path = Path(ctx["out_dir"]) / f"receipt-{n}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    ctx["receipts"].append(receipt_path.name)
    return code, receipt, receipt_path.name


def emi(work, ctx):
    code, receipt, name = check(work, ctx)
    if receipt is None:
        return "flagged", None, {"gate": "emi", "exit": code, "error": name[-2000:]}
    record = {"gate": "emi", "exit": code, "action": receipt["action"],
              "rule": receipt.get("rule"), "receipt": name}
    if receipt["action"] == "ask_person":
        # the person's part, played by the reviewer's fixed rule
        items = reviewer.decide(work, receipt)
        record["reviewer"] = {"approved": items} if items else {"refused": True}
        if items:
            code, receipt, name = check(work, ctx, approve=items)
            if receipt is None:
                return "flagged", None, {**record, "error": name[-2000:]}
            record.update({"exit": code, "action": receipt["action"],
                           "rule": receipt.get("rule"), "receipt": name})
    action = receipt["action"]
    if action == "stop":
        return "accepted", None, record
    if action == "repair":
        lines = "\n".join(f"- {line}" for line in receipt.get("repair", []))
        return "repair", "EMI: this change is not done. Fix this, then finish again:\n" + lines, record
    return "flagged", None, record


GATES = {"control": control, "naive": naive, "cooperative": emi, "strict": emi}
