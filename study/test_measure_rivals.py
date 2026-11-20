#!/usr/bin/env python3
"""Unit tests for study/measure_rivals.py (Phase 1 a1 + Phase 2 a2)."""

import sys
import unittest
from pathlib import Path

STUDY = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY))

import measure_rivals as mr  # noqa: E402


class TestMeasureRivals(unittest.TestCase):
    def test_select_pairs_prefers_cross_model_and_handles_all_wrong(self):
        mixed = [
            {"id": "t.claude.1", "model": "claude", "right": True},
            {"id": "t.claude.2", "model": "claude", "right": False},
            {"id": "t.gpt.1", "model": "gpt", "right": False},
            {"id": "t.gpt.2", "model": "gpt", "right": True},
        ]
        pairs = mr.select_pairs(mixed, max_rw=2, max_rr=1)
        rw = [p for p in pairs if p["pair_kind"] == "right_vs_wrong"]
        rr = [p for p in pairs if p["pair_kind"] == "right_vs_right"]
        self.assertEqual(len(rw), 2)
        self.assertTrue(all(p["rival"]["model"] != p["candidate"]["model"] for p in rw))
        self.assertEqual(len(rr), 1)
        self.assertNotEqual(rr[0]["rival"]["model"], rr[0]["candidate"]["model"])

        all_wrong = [
            {"id": "t.claude.1", "model": "claude", "right": False},
            {"id": "t.gpt.1", "model": "gpt", "right": False},
        ]
        ww = mr.select_pairs(all_wrong)
        self.assertEqual(len(ww), 1)
        self.assertEqual(ww[0]["pair_kind"], "wrong_vs_wrong")

    def test_classify_fork_taxonomy(self):
        # Wording-only: same exception type
        self.assertEqual(
            mr.classify_fork(
                {"function": "f", "rival": {"raised": "ValueError: bad a"}, "candidate": {"raised": "ValueError: bad b"}}
            ),
            {"mechanism": "wording_only", "scope": "leaf_fork"},
        )
        # Unintended built-in crash vs value
        self.assertEqual(
            mr.classify_fork(
                {"function": "f", "rival": {"raised": "AttributeError: 'int'"}, "candidate": {"returned": "1"}}
            ),
            {"mechanism": "crash_unintended", "scope": "leaf_fork"},
        )
        # Explicit domain raise vs value -> interface fork
        self.assertEqual(
            mr.classify_fork(
                {"function": "f", "rival": {"raised": "ValidationError: bad"}, "candidate": {"returned": []}},
                explicit_raises={"ValidationError"},
            ),
            {"mechanism": "explicit_raise_vs_value", "scope": "interface_fork"},
        )
        # Different return shapes -> interface fork
        self.assertEqual(
            mr.classify_fork(
                {"function": "f", "rival": {"returned": "abc"}, "candidate": {"returned": [{"type": "text"}]}}
            ),
            {"mechanism": "value_diff", "scope": "interface_fork"},
        )
        # Same return shape -> leaf fork
        self.assertEqual(
            mr.classify_fork(
                {"function": "f", "rival": {"returned": "a"}, "candidate": {"returned": "b"}}
            ),
            {"mechanism": "value_diff", "scope": "leaf_fork"},
        )

    def test_detect_private_mocking(self):
        bad = "mock.patch('pkg.StacSearch._request')\nw._handle = io.BytesIO()\n"
        hits = mr.detect_private_mocking(bad)
        self.assertTrue(hits, "expected private mocking hits")
        good = "def probe():\n    return public_fn(1)\n"
        self.assertEqual(mr.detect_private_mocking(good), [])

    def test_summarize_rows_computes_reach_and_rates(self):
        rows = [
            {
                "arm": "a1",
                "task": "t1",
                "pair_kind": "right_vs_wrong",
                "status": "disagreed",
                "identical_code": False,
                "functions": [{"status": "compared"}],
                "not_checked": ["a.py::C.m: instance_method"],
                "disagreements": [{"mechanism": "value_diff", "scope": "leaf_fork"}],
            },
            {
                "arm": "a1",
                "task": "t2",
                "pair_kind": "right_vs_right",
                "status": "agreed",
                "identical_code": False,
                "functions": [{"status": "compared"}],
                "not_checked": [],
                "disagreements": [],
            },
        ]
        s = mr.summarize_rows(rows)
        a1 = s["arms"]["a1"]
        self.assertEqual(a1["reach"]["functions_compared"], 2)
        self.assertEqual(a1["reach"]["functions_not_checked"], 1)
        self.assertEqual(a1["by_pair_kind"]["right_vs_wrong"]["pair_disagree_rate"], 1.0)
        self.assertEqual(a1["by_pair_kind"]["right_vs_right"]["pair_disagree_rate"], 0.0)
        self.assertEqual(a1["fork_scopes"]["leaf_fork"], 1)


if __name__ == "__main__":
    unittest.main()
