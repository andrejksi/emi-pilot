"""A scripted OpenAI-compatible endpoint, to test the harness without a
model or a key. It plays one fixed agent on calc-median: it writes a median
with no test and says it is done; sent back, it adds the test and finishes.

    python3 harness/stub_model.py 8765 &
    MODEL_API_KEY=stub python3 harness/agent.py ... --backend chat \
        --base-url http://127.0.0.1:8765/v1 --model stub
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPLAY = Path(__file__).resolve().parent.parent / "tasks" / "calc-median" / "replay"


def call(i, name, **args):
    return {"id": f"call_{i}", "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}


def script():
    return [
        [call(0, "write_file", path="calc.py",
              content=(REPLAY / "right-no-test" / "calc.py").read_text())],
        [call(1, "finish", summary="median added")],
        [call(2, "write_file", path="tests/test_median.py",
              content=(REPLAY / "right-with-test" / "tests" / "test_median.py").read_text())],
        [call(3, "run", command=".venv/bin/python -m pytest -q")],
        [call(4, "finish", summary="median added, with tests")],
    ]


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        turn = sum(1 for m in body["messages"] if m["role"] == "assistant")
        steps = script()
        calls = steps[min(turn, len(steps) - 1)]
        reply = {"choices": [{"message": {"role": "assistant", "content": None,
                                          "tool_calls": calls}}],
                 "usage": {"prompt_tokens": 100, "completion_tokens": 20}}
        data = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
