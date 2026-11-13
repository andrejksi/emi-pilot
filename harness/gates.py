"""What each arm does when the agent says it is finished.

A gate returns (verdict, feedback, record):
  verdict  "accepted"  the agent may stop
           "repair"    send the agent back with `feedback`
           "flagged"   the run ends without a pass: a person must look
                       (EMI's ask_person and incomplete)
"""

import json
from pathlib import Path

from common import run
from trees import test_command

REPAIR_ROUNDS = 3  # the same budget for the naive hook and EMI's default


def control(work, ctx):
    return "accepted", None, {"gate": "none"}


def naive(work, ctx):
    """The cheapest stop hook there is: the visible tests must pass."""
    code, out = run(test_command(ctx["task"]), cwd=work, timeout=1200)
    record = {"gate": "pytest", "exit": code}
    if code == 0:
        return "accepted", None, record
    return "repair", "The tests fail. Fix this, then finish again:\n" + out[-4000:], record


def emi(work, ctx):
    state = Path(work).parent / (Path(work).name + ".emi-state")
    code, out = run([ctx["emi"], "done", "--format", "json"], cwd=work,
                    env={"XDG_STATE_HOME": str(state)}, timeout=1200)
    try:
        receipt = json.loads(out[out.index("{"):])
    except ValueError:
        return "flagged", None, {"gate": "emi", "exit": code, "error": out[-2000:]}
    n = len(ctx.setdefault("receipts", []))
    receipt_path = Path(ctx["out_dir"]) / f"receipt-{n}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    ctx["receipts"].append(receipt_path.name)
    record = {"gate": "emi", "exit": code, "action": receipt["action"],
              "rule": receipt.get("rule"), "receipt": receipt_path.name}
    action = receipt["action"]
    if action == "stop":
        return "accepted", None, record
    if action == "repair":
        lines = "\n".join(f"- {line}" for line in receipt.get("repair", []))
        return "repair", "EMI: this change is not done. Fix this, then finish again:\n" + lines, record
    return "flagged", None, record


GATES = {"control": control, "naive": naive, "cooperative": emi, "strict": emi}
