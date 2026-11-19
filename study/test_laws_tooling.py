#!/usr/bin/env python3
"""Unit tests for study/save_laws.py, study/approve_laws.py, and dropped_at_approval."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PILOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PILOT / "study"))

import approve_laws  # noqa: E402
import replay_gate  # noqa: E402
import save_laws  # noqa: E402


def _make_fake_emi(path: Path, *, check_exit: int = 0) -> Path:
    script = (
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "args = sys.argv[1:]\n"
        "if args[:2] == ['rules', 'brief']:\n"
        "    print('EMI rules brief (mock).')\n"
        "    sys.exit(0)\n"
        "if args[:2] == ['rules', 'check']:\n"
        "    code = int(os.environ.get('FAKE_EMI_EXIT', str(" + str(check_exit) + ")))\n"
        "    print('CHECK_OK' if code == 0 else 'CHECK_FAIL: fix rule')\n"
        "    sys.exit(code)\n"
        "sys.exit(0)\n"
    )
    path.write_text(script, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _init_git_repo(work: Path) -> None:
    work.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=work, check=True, env=env)
    (work / "app.py").write_text("x = 1\n", encoding="utf-8")
    (work / ".emi" / "laws").mkdir(parents=True, exist_ok=True)
    (work / ".emi" / "config.json").write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=work, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=work, check=True, env=env)


class SaveLawsTests(unittest.TestCase):
    def test_check_rejects_edits_outside_laws(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            work = tmp / "work"
            _init_git_repo(work)
            emi = _make_fake_emi(tmp / "emi")
            (work / ".emi" / "laws" / "test_rule.py").write_text("def test_a(): pass\n")
            (work / "app.py").write_text("x = 2\n")  # forbidden edit outside .emi/laws/

            with self.assertRaises(SystemExit) as ctx:
                save_laws.main(
                    [
                        "check",
                        "--task",
                        "demo-1",
                        "--work",
                        str(work),
                        "--role",
                        "primary",
                        "--model",
                        "m1",
                        "--out",
                        str(tmp / "out"),
                        "--emi",
                        str(emi),
                    ]
                )
            self.assertIn("outside `.emi/laws/`", str(ctx.exception))

    def test_check_snapshots_first_then_checked_draft(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            work = tmp / "work"
            out = tmp / "out"
            _init_git_repo(work)
            emi = _make_fake_emi(tmp / "emi")

            law_file = work / ".emi" / "laws" / "test_rule.py"
            law_file.write_text("def test_v1(): assert False\n")

            # Round 0 fails (exit 3) -> saved to first/, NOT checked_draft/
            with mock.patch.dict(os.environ, {"FAKE_EMI_EXIT": "3"}):
                rc0 = save_laws.main(
                    [
                        "check",
                        "--task",
                        "demo-1",
                        "--work",
                        str(work),
                        "--role",
                        "primary",
                        "--model",
                        "m1",
                        "--out",
                        str(out),
                        "--emi",
                        str(emi),
                    ]
                )
            self.assertEqual(rc0, 3)
            self.assertEqual(
                (out / "demo-1" / "first" / "test_rule.py").read_text(),
                "def test_v1(): assert False\n",
            )
            self.assertFalse((out / "demo-1" / "checked_draft").exists())

            # Round 1 passes (exit 0) -> first/ preserved, checked_draft/ updated
            law_file.write_text("def test_v2(): assert True\n")
            with mock.patch.dict(os.environ, {"FAKE_EMI_EXIT": "0"}):
                rc1 = save_laws.main(
                    [
                        "check",
                        "--task",
                        "demo-1",
                        "--work",
                        str(work),
                        "--role",
                        "primary",
                        "--model",
                        "m1",
                        "--out",
                        str(out),
                        "--emi",
                        str(emi),
                    ]
                )
            self.assertEqual(rc1, 0)
            self.assertEqual(
                (out / "demo-1" / "first" / "test_rule.py").read_text(),
                "def test_v1(): assert False\n",
            )
            self.assertEqual(
                (out / "demo-1" / "checked_draft" / "test_rule.py").read_text(),
                "def test_v2(): assert True\n",
            )
            meta = json.loads((out / "demo-1" / "draft_primary.json").read_text())
            self.assertTrue(meta["passed"])
            self.assertEqual([r["exit"] for r in meta["rounds"]], [3, 0])

    def test_secondary_role_writes_secondary_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            work = tmp / "work"
            out = tmp / "out"
            _init_git_repo(work)
            emi = _make_fake_emi(tmp / "emi", check_exit=0)
            (work / ".emi" / "laws" / "test_sec.py").write_text("def test_s(): pass\n")

            rc = save_laws.main(
                [
                    "check",
                    "--task",
                    "demo-2",
                    "--work",
                    str(work),
                    "--role",
                    "secondary",
                    "--model",
                    "m2",
                    "--out",
                    str(out),
                    "--emi",
                    str(emi),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue((out / "demo-2" / "secondary" / "test_sec.py").exists())
            self.assertTrue((out / "demo-2" / "secondary_checked" / "test_sec.py").exists())


class ApproveLawsTests(unittest.TestCase):
    def test_sample_outside_deterministic(self) -> None:
        tasks = [f"task-{i:02d}" for i in range(28)]
        s1 = approve_laws.sample_outside_tasks(tasks, n=10, seed=20261117)
        s2 = approve_laws.sample_outside_tasks(list(reversed(tasks)), n=10, seed=20261117)
        self.assertEqual(s1, s2)
        self.assertEqual(len(s1), 10)

    def test_review_approve_partial_and_reject(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            laws_root = tmp / "laws"
            approvals = laws_root / "approvals.jsonl"

            # Task A: partial approval (keep file 1 of 2)
            a_draft = laws_root / "task-a" / "checked_draft"
            a_draft.mkdir(parents=True)
            (a_draft / "test_one.py").write_text("def test_1(): pass\n")
            (a_draft / "test_two.py").write_text("def test_2(): pass\n")

            # Task B: reject all -> checked/ stays absent -> dropped_at_approval
            b_draft = laws_root / "task-b" / "checked_draft"
            b_draft.mkdir(parents=True)
            (b_draft / "test_b.py").write_text("def test_b(): pass\n")

            fake_task = {"id": "task-a", "prompt": "Fix bug X"}
            with mock.patch.object(approve_laws, "load_task", return_value=fake_task):
                answers_a = iter(["s", "1"])
                st_a = approve_laws.review_one(
                    "task-a", laws_root, "primary", approvals, input_fn=lambda _: next(answers_a)
                )
                self.assertEqual(st_a, "done")
                self.assertTrue((laws_root / "task-a" / "checked" / "test_one.py").exists())
                self.assertFalse((laws_root / "task-a" / "checked" / "test_two.py").exists())

                answers_b = iter(["r"])
                st_b = approve_laws.review_one(
                    "task-b", laws_root, "primary", approvals, input_fn=lambda _: next(answers_b)
                )
                self.assertEqual(st_b, "done")
                self.assertFalse((laws_root / "task-b" / "checked").exists())

            rows = approve_laws.load_approvals(approvals)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["decision"], "approve_partial")
            self.assertEqual(rows[0]["kept_files"], ["test_one.py"])
            self.assertEqual(rows[1]["decision"], "reject_all")

            # Verify replay_gate classifies task-b as dropped_at_approval
            dirs_b = replay_gate.resolve_law_dirs("task-b", laws_root=laws_root)
            self.assertIsNone(dirs_b["approved"])
            self.assertIsNotNone(dirs_b["checked_draft"])
            stage_b = replay_gate.infer_slipped_stage(
                has_approved=dirs_b["approved"] is not None,
                has_unapproved_primary=dirs_b["unapproved_primary"] is not None,
                has_checked_draft=dirs_b["checked_draft"] is not None,
            )
            self.assertEqual(stage_b, "dropped_at_approval")


if __name__ == "__main__":
    unittest.main()
