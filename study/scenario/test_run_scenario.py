#!/usr/bin/env python3
"""Tests for study/scenario/run_scenario.py. The sealed runs need
bubblewrap; those tests are skipped without it, and say so."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_scenario as rs  # noqa: E402

HAVE_BWRAP = shutil.which("bwrap") is not None
MADE: list[Path] = []


def tearDownModule():
    for d in MADE:
        shutil.rmtree(d, ignore_errors=True)


def tree_with(module_src: str) -> Path:
    """A tiny project: `calc.py` and a .venv whose python is this one."""
    root = Path(tempfile.mkdtemp())
    MADE.append(root)
    (root / "calc.py").write_text(module_src, encoding="utf-8")
    (root / ".venv" / "bin").mkdir(parents=True)
    os.symlink(sys.executable, root / ".venv" / "bin" / "python")
    return root


def scenario(src: str) -> Path:
    d = Path(tempfile.mkdtemp())
    MADE.append(d)
    f = d / "s.py"
    f.write_text(src, encoding="utf-8")
    return f


OBSERVE_HALF = (
    "import json, sys\nsys.path.insert(0, '.')\nfrom calc import half\n"
    "print('EMI-OBSERVATION ' + json.dumps({'name': 'half of 5', 'value': half(5)}))\n"
)


class TestParse(unittest.TestCase):
    def test_reads_only_marked_lines_and_checks_shape(self):
        self.assertEqual(rs.parse_observations('noise\nEMI-OBSERVATION {"name": "a", "value": 1}\n'),
                         [{"name": "a", "value": 1}])
        self.assertIsInstance(rs.parse_observations("EMI-OBSERVATION {not json"), str)
        self.assertIsInstance(rs.parse_observations('EMI-OBSERVATION {"value": 1}'), str)


@unittest.skipUnless(HAVE_BWRAP, "bubblewrap is not installed: sealed runs not tested")
class TestObserve(unittest.TestCase):
    def test_same_code_same_observation_twice(self):
        tree = tree_with("def half(n):\n    return n // 2\n")
        res = rs.observe(tree, scenario(OBSERVE_HALF), None)
        self.assertEqual(res, {"status": "observed",
                               "observations": [{"name": "half of 5", "value": 2}]})
        self.assertFalse((tree / rs.SCENARIO_DIR).exists())

    def test_runs_that_differ_observe_nothing(self):
        tree = tree_with("import time\ndef half(n):\n    return time.perf_counter_ns()\n")
        self.assertEqual(rs.observe(tree, scenario(OBSERVE_HALF), None)["status"], "nondeterministic")

    def test_a_crash_is_a_crash_not_an_observation(self):
        tree = tree_with("def half(n):\n    raise RuntimeError('no')\n")
        res = rs.observe(tree, scenario(OBSERVE_HALF), None)
        self.assertEqual(res["status"], "crashed")
        self.assertIn("RuntimeError", res["stderr"])

    def test_the_network_is_sealed(self):
        tree = tree_with("def half(n):\n    return n\n")
        src = ("import json, socket\ntry:\n    socket.create_connection(('1.1.1.1', 53), timeout=3)\n"
               "    ok = True\nexcept OSError:\n    ok = False\n"
               "print('EMI-OBSERVATION ' + json.dumps({'name': 'net', 'value': ok}))\n")
        res = rs.observe(tree, scenario(src), None)
        self.assertEqual(res["observations"], [{"name": "net", "value": False}])

    def test_pins_hold(self):
        tree = tree_with("def half(n):\n    return n\n")
        src = ("import json, os\nprint('EMI-OBSERVATION ' + json.dumps({'name': 'pins', 'value': "
               "[os.environ['PYTHONHASHSEED'], os.environ['TZ']]}))\n")
        self.assertEqual(rs.observe(tree, scenario(src), None)["observations"][0]["value"], ["0", "UTC"])


class TestAdmit(unittest.TestCase):
    TEXT = "half(5) should return 2.5, not 2"
    OK = {"status": "observed", "observations": [{"name": "x", "value": 2}]}

    def test_public_scenario_that_names_the_task_is_admitted(self):
        self.assertEqual(rs.admit(OBSERVE_HALF, self.TEXT, self.OK), {"admitted": True, "why": []})

    def test_private_names_are_refused_and_listed(self):
        for src in ("import calc\ncalc._cache.clear()\nfrom calc import half\n",
                    "from calc import _helper, half\n",
                    "from unittest import mock\nfrom calc import half\nmock.patch('calc.Engine._request')\n"):
            res = rs.admit(src, self.TEXT, self.OK)
            self.assertFalse(res["admitted"], src)
            self.assertIn("it uses the project's private names", res["why"])
            self.assertTrue(res["private"])

    def test_dunders_are_not_private(self):
        src = "from calc import half\nprint(half.__name__)\n"
        self.assertTrue(rs.admit(src, self.TEXT, self.OK)["admitted"])

    def test_a_scenario_that_names_nothing_in_the_task_is_refused(self):
        res = rs.admit("from calc import double\n", self.TEXT, self.OK)
        self.assertIn("it calls no public name the task text names", res["why"])

    def test_baseline_outcomes(self):
        crashed = {"status": "crashed", "observations": []}
        self.assertTrue(rs.admit(OBSERVE_HALF, self.TEXT, crashed)["admitted"])
        for status in ("nondeterministic", "timeout", "no_observation", "unreadable"):
            self.assertFalse(rs.admit(OBSERVE_HALF, self.TEXT, {"status": status})["admitted"], status)

    def test_unparseable_scenario_is_refused_with_why(self):
        res = rs.admit("def (:\n", self.TEXT, self.OK)
        self.assertFalse(res["admitted"])
        self.assertTrue(res["why"][0].startswith("it does not parse"))


class TestAnswer(unittest.TestCase):
    def obs(self, v):
        return {"status": "observed", "observations": [{"name": "x", "value": v}]}

    def test_agree_finding_either(self):
        self.assertEqual(rs.answer(self.obs(1), self.obs(1)), {"answer": "agree"})
        f = rs.answer(self.obs(2), self.obs(1))
        self.assertEqual(f["answer"], "finding")
        self.assertEqual(f["merged"]["observations"][0]["value"], 1)
        self.assertEqual(rs.answer(self.obs(2), {"status": "nondeterministic"})["answer"], "either")

    def test_a_crash_where_the_merged_fix_observes_is_a_finding(self):
        crashed = {"status": "crashed", "observations": [], "stderr": "boom"}
        self.assertEqual(rs.answer(crashed, self.obs(1))["answer"], "finding")

    def test_stderr_does_not_decide(self):
        a = {"status": "crashed", "observations": [], "stderr": "at 0x1"}
        b = {"status": "crashed", "observations": [], "stderr": "at 0x2"}
        self.assertEqual(rs.answer(a, b), {"answer": "agree"})


if __name__ == "__main__":
    unittest.main()
