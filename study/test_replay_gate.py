#!/usr/bin/env python3
"""Unit tests for study/replay_gate.py and integration with study/score.py."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

STUDY = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY))

import replay_gate  # noqa: E402
import score  # noqa: E402


class TestReplayGate(unittest.TestCase):
    def test_classify_emi_cause(self):
        self.assertIsNone(replay_gate.classify_emi_cause({"action": "stop"}, {"action": "stop"}))
        self.assertEqual(
            replay_gate.classify_emi_cause(
                {"action": "repair", "rule": "laws"}, {"action": "repair"}
            ),
            "laws",
        )
        self.assertEqual(
            replay_gate.classify_emi_cause(
                {"action": "incomplete", "not_verified": [{"kind": "sandbox_unavailable"}]},
                {"action": "incomplete"},
            ),
            "incomplete:sandbox_unavailable",
        )
        self.assertEqual(
            replay_gate.classify_emi_cause(None, {"error": "crash"}),
            "error",
        )

    def test_infer_slipped_stage(self):
        self.assertEqual(
            replay_gate.infer_slipped_stage(has_approved=True, has_unapproved_primary=True),
            "law_in_force_still_stop",
        )
        self.assertEqual(
            replay_gate.infer_slipped_stage(has_approved=False, has_unapproved_primary=True),
            "dropped_by_rules_check",
        )
        self.assertEqual(
            replay_gate.infer_slipped_stage(has_approved=False, has_unapproved_primary=False),
            "no_law_drafted",
        )
        self.assertEqual(
            replay_gate.infer_slipped_stage(
                has_approved=False,
                has_unapproved_primary=True,
                override="dropped_at_approval",
            ),
            "dropped_at_approval",
        )

    def test_resolve_law_dirs(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            root = Path(tmp_str)
            tdir = root / "task-1"
            (tdir / "first").mkdir(parents=True)
            (tdir / "first" / "test_a.py").write_text("def test_a(): pass\n", encoding="utf-8")
            (tdir / "checked").mkdir(parents=True)
            # checked is empty -> should resolve to None
            dirs = replay_gate.resolve_law_dirs("task-1", laws_root=root)
            self.assertEqual(dirs["unapproved_primary"], tdir / "first")
            self.assertIsNone(dirs["approved"])
            self.assertIsNone(dirs["unapproved_secondary"])

            # Add a law to checked -> resolves
            (tdir / "checked" / "test_a.py").write_text("def test_a(): pass\n", encoding="utf-8")
            dirs = replay_gate.resolve_law_dirs("task-1", laws_root=root)
            self.assertEqual(dirs["approved"], tdir / "checked")

    def test_replay_task_emits_score_compatible_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            attempts = tmp / "attempts"
            for cid, right in [("t1.wrong", False), ("t1.right", True)]:
                d = attempts / cid
                d.mkdir(parents=True)
                (d / "run.json").write_text(
                    json.dumps({"task": "t1", "model": "moonshotai/Kimi-K3.1-Pro", "final": "accepted"}),
                    encoding="utf-8",
                )
                (d / "oracle.json").write_text(json.dumps({"passed": right}), encoding="utf-8")
                (d / "candidate.diff").write_text("", encoding="utf-8")

            laws_root = tmp / "laws"
            (laws_root / "t1" / "first").mkdir(parents=True)
            (laws_root / "t1" / "first" / "test_law.py").write_text("def test_x(): pass\n")
            (laws_root / "t1" / "checked").mkdir(parents=True)
            (laws_root / "t1" / "checked" / "test_law.py").write_text("def test_x(): pass\n")

            out_jsonl = tmp / "replays.jsonl"

            def fake_base(task, laws, dst, venv, emi_bin, *, ceiling=False):
                dst.mkdir(parents=True, exist_ok=True)
                return []

            def fake_restore(task, base, attempt_dir, work, before):
                return {"action": "stop", "cause": None, "seconds": 0.1}

            def fake_emi(task, base, attempt_dir, work, emi_bin, rdir, *, exclude_paths=None):
                is_wrong = attempt_dir.name.endswith(".wrong")
                if "approved" in base.name and is_wrong:
                    return {"action": "repair", "cause": "laws", "seconds": 0.2}
                return {"action": "stop", "cause": None, "seconds": 0.2}

            with (
                mock.patch.object(replay_gate, "load_task", return_value={"id": "t1", "kind": "dir"}),
                mock.patch.object(replay_gate, "build_base_tree", side_effect=fake_base),
                mock.patch.object(replay_gate.plain_check, "outcomes", return_value=({"a": "passed"}, "")),
                mock.patch.object(replay_gate, "eval_restore", side_effect=fake_restore),
                mock.patch.object(replay_gate, "eval_emi", side_effect=fake_emi),
            ):
                rows = replay_gate.replay_task(
                    "t1",
                    [attempts],
                    out_jsonl,
                    emi_bin="emi",
                    laws_root=laws_root,
                    conditions=["restore", "emi_default", "primary"],
                    runs=2,
                    include_gold=False,
                )

            self.assertEqual(len(rows), 2 * 3 * 2)  # 2 candidates x 3 conditions x 2 runs
            loaded = score.load_jsonl(out_jsonl)
            rep = score.score(loaded, [], resamples=200)
            self.assertEqual(rep["disagreed_replays_excluded"], 0)
            self.assertEqual(rep["primary"]["catch_rate"]["rate"], 1.0)
            self.assertEqual(rep["primary"]["false_block_rate"]["rate"], 0.0)
            self.assertEqual(rep["gate"]["verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
