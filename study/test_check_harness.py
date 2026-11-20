#!/usr/bin/env python3
"""Unit tests for study/check_harness.py."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_harness  # noqa: E402


def row(cand, cond, action, right, run=0, task="t1", **extra):
    return {"candidate": cand, "condition": cond, "action": action, "right": right,
            "run": run, "task": task, **extra}


def sound():
    """A replay whose harness gives every known answer."""
    rows = []
    for run in (0, 1):
        rows += [
            row("t1.w", "ceiling", "repair", False, run, why=["hidden test fails"]),
            row("t1.r", "ceiling", "stop", True, run),
            row("t1.w", "pytest", "repair", False, run, baseline="pass"),
            row("t1.r", "pytest", "stop", True, run, baseline="pass"),
        ]
    return rows


class TestCheckHarness(unittest.TestCase):
    def test_sound_replay_passes_with_no_warnings(self):
        res = check_harness.run_checks(sound())
        self.assertEqual(res["failures"], [])
        self.assertEqual(res["warnings"], [])

    def test_ceiling_blocking_a_right_candidate_fails_and_names_the_task(self):
        rows = sound() + [row("t1.r2", "ceiling", "incomplete", True, 0, cause="incomplete:not_verified")]
        res = check_harness.run_checks(rows)
        self.assertTrue(any(f.startswith("ceiling_blocks") for f in res["failures"]))
        self.assertTrue(any("t1 incomplete incomplete:not_verified" in d for d in res["details"]))

    def test_ceiling_missing_a_wrong_candidate_fails(self):
        rows = [r for r in sound() if not (r["condition"] == "ceiling" and not r["right"])]
        rows.append(row("t1.w", "ceiling", "stop", False))
        res = check_harness.run_checks(rows)
        self.assertTrue(any(f.startswith("ceiling_catch") for f in res["failures"]))

    def test_no_ceiling_rows_is_a_failure_not_a_pass(self):
        rows = [r for r in sound() if r["condition"] != "ceiling"]
        self.assertTrue(check_harness.run_checks(rows)["failures"])

    def test_replays_that_disagree_fail(self):
        rows = sound() + [row("t1.r", "primary", "stop", True, 0), row("t1.r", "primary", "repair", True, 1)]
        res = check_harness.run_checks(rows)
        self.assertTrue(any(f.startswith("disagreement") for f in res["failures"]))

    def test_error_rows_fail(self):
        rows = sound() + [row("t1.r", "emi_default", "error", True, cause="timeout")]
        self.assertTrue(any(f.startswith("errors") for f in check_harness.run_checks(rows)["failures"]))

    def test_failing_or_unrecorded_pytest_baseline_warns(self):
        failing = [dict(r, baseline="fail") if r["condition"] == "pytest" else r for r in sound()]
        self.assertTrue(any("fail with no change" in w for w in check_harness.run_checks(failing)["warnings"]))
        unknown = [{k: v for k, v in r.items() if k != "baseline"} for r in sound()]
        self.assertTrue(any("not recorded" in w for w in check_harness.run_checks(unknown)["warnings"]))

    def test_unexplained_block_and_uniform_tasks_warn(self):
        rows = sound() + [
            row("t2.w", "primary", "repair", False, task="t2"),
            row("t2.w", "ceiling", "repair", False, task="t2", why=["x"]),
        ]
        warnings = check_harness.run_checks(rows, max_uniform=0.4)["warnings"]
        self.assertTrue(any(w.startswith("unexplained: 1") for w in warnings))
        self.assertTrue(any("all wrong" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
