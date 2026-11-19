"""Unit tests for study/score.py against the rules in study/gate.md."""

from __future__ import annotations

import unittest

from score import BOOTSTRAP_SEED, DEFAULT_PRIMARY_DRAFTER, score


def _double(cand, task, model, right, cond, action, **extra):
    return [
        {"candidate": cand, "task": task, "model": model, "right": right, "condition": cond, "action": action, "run": 0, **extra},
        {"candidate": cand, "task": task, "model": model, "right": right, "condition": cond, "action": action, "run": 1, **extra},
    ]


class ScoreGateTests(unittest.TestCase):
    def test_pass_gate_and_bootstrap_determinism(self):
        rows = []
        for i in range(10):
            t = f"task-{i}"
            m = DEFAULT_PRIMARY_DRAFTER if i % 2 == 0 else "other/model"
            # restore accepts all 10 wrong changes; primary catches 6 (3/5 same-family = 60%)
            rows += _double(f"w{i}", t, m, False, "restore", "stop")
            action = "repair" if i < 6 else "stop"
            extra = {"stage": "law_in_force_still_stop"} if action == "stop" else {}
            rows += _double(f"w{i}", t, m, False, "primary", action, **extra)
            # 10 right changes; primary false-blocks 1 via incomplete (10% <= 10%)
            rows += _double(f"r{i}", t, m, True, "restore", "stop")
            r_action = "incomplete" if i == 0 else "stop"
            rows += _double(f"r{i}", t, m, True, "primary", r_action, cause="proving" if i == 0 else "")

        approvals = [
            {"task": f"task-{i}", "approver": "primary", "minutes": 3.5} for i in range(10)
        ] + [
            {"task": f"task-{i}", "approver": "outside", "minutes": 4.0} for i in range(5)
        ]

        r1 = score(rows, approvals, resamples=500)
        r2 = score(rows, approvals, resamples=500)
        self.assertEqual(r1, r2)
        self.assertEqual(r1["bootstrap"]["seed"], BOOTSTRAP_SEED)
        self.assertEqual(r1["gate"]["verdict"], "pass")
        self.assertEqual(r1["primary"]["catch_rate"]["hits"], 6)
        self.assertEqual(r1["primary"]["catch_rate"]["total"], 10)
        self.assertEqual(r1["primary"]["same_family_catch_rate"]["hits"], 3)
        self.assertEqual(r1["primary"]["same_family_catch_rate"]["total"], 5)
        self.assertEqual(r1["primary"]["false_block_rate"]["hits"], 1)
        self.assertEqual(r1["false_block_causes"], {"proving": 1})

    def test_disagreed_double_replay_excluded(self):
        rows = (
            _double("w1", "t1", DEFAULT_PRIMARY_DRAFTER, False, "restore", "stop")
            + [
                {"candidate": "w1", "task": "t1", "model": DEFAULT_PRIMARY_DRAFTER, "right": False, "condition": "primary", "action": "stop", "run": 0},
                {"candidate": "w1", "task": "t1", "model": DEFAULT_PRIMARY_DRAFTER, "right": False, "condition": "primary", "action": "repair", "run": 1},
            ]
            + _double("w2", "t2", DEFAULT_PRIMARY_DRAFTER, False, "restore", "stop")
            + _double("w2", "t2", DEFAULT_PRIMARY_DRAFTER, False, "primary", "repair")
            + _double("r1", "t1", DEFAULT_PRIMARY_DRAFTER, True, "primary", "stop")
        )
        rep = score(rows, [], resamples=100)
        self.assertEqual(rep["disagreed_replays_excluded"], 1)
        self.assertEqual(rep["primary"]["catch_rate"]["hits"], 1)
        self.assertEqual(rep["primary"]["catch_rate"]["total"], 1)

    def test_between_fixable_stage_vs_validator_branch(self):
        rows = []
        for i in range(10):
            t = f"t{i}"
            rows += _double(f"w{i}", t, DEFAULT_PRIMARY_DRAFTER, False, "restore", "stop")
            if i < 4:
                rows += _double(f"w{i}", t, DEFAULT_PRIMARY_DRAFTER, False, "primary", "repair")
            else:
                stage = "no_law_drafted" if i < 8 else "law_in_force_still_stop"
                rows += _double(f"w{i}", t, DEFAULT_PRIMARY_DRAFTER, False, "primary", "stop", stage=stage)
            rows += _double(f"r{i}", t, DEFAULT_PRIMARY_DRAFTER, True, "primary", "stop")

        rep = score(rows, [], resamples=100)
        # 4/6 = 66.7% >= 60% of slipped wrong changes are in no_law_drafted
        self.assertEqual(rep["gate"]["verdict"], "between_fixable_stage")
        self.assertEqual(rep["gate"]["fixable_stage"]["stage"], "no_law_drafted")

    def test_fail_gate_on_high_false_block(self):
        rows = (
            _double("w1", "t1", DEFAULT_PRIMARY_DRAFTER, False, "restore", "stop")
            + _double("w1", "t1", DEFAULT_PRIMARY_DRAFTER, False, "primary", "repair")
            + _double("r1", "t1", DEFAULT_PRIMARY_DRAFTER, True, "primary", "incomplete")
            + _double("r2", "t2", DEFAULT_PRIMARY_DRAFTER, True, "primary", "stop")
            + _double("r3", "t3", DEFAULT_PRIMARY_DRAFTER, True, "primary", "stop")
        )
        rep = score(rows, [], resamples=100)
        self.assertEqual(rep["gate"]["verdict"], "fail")


if __name__ == "__main__":
    unittest.main()
