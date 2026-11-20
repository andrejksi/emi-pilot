#!/usr/bin/env python3
"""Unit tests for harness bug fixes (oracle, trees, mine_prs, validate_pr, replay_gate)."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "study"))

import mine_prs  # noqa: E402
import oracle  # noqa: E402
import replay_gate  # noqa: E402
import trees  # noqa: E402
import validate_pr  # noqa: E402


class TestOracleNodeIdParsing(unittest.TestCase):
    def test_outcomes_preserves_spaces_and_dashes_in_parametrize_ids(self):
        out = "\n".join([
            "PASSED tests/test_req.py::TestReq::test_arb[===arbitrarystring, >=1.0]",
            "FAILED tests/test_req.py::TestReq::test_arb[a - b] - AssertionError: boom",
            "SKIPPED [3] tests/test_req.py:42: platform only",
            "ERROR tests/test_req.py::test_setup - RuntimeError: bad fixture",
        ])
        seen = oracle.outcomes(out)
        self.assertEqual(
            seen,
            {
                "tests/test_req.py::TestReq::test_arb[===arbitrarystring, >=1.0]": "PASSED",
                "tests/test_req.py::TestReq::test_arb[a - b]": "FAILED",
                "tests/test_req.py::test_setup": "ERROR",
            },
        )

    def test_test_passed_supports_exact_and_legacy_truncated_ids(self):
        seen = {
            "tests/test_req.py::test_arb[===arbitrarystring, >=1.0]": "PASSED",
            "tests/test_req.py::test_arb[===arbitrarystring, <2.0]": "FAILED",
            "tests/test_req.py::test_ok[a, b]": "PASSED",
        }
        self.assertTrue(oracle.test_passed(seen, "tests/test_req.py::test_arb[===arbitrarystring, >=1.0]"))
        self.assertFalse(oracle.test_passed(seen, "tests/test_req.py::test_arb[===arbitrarystring, <2.0]"))
        # Legacy truncated ID matching a mix of PASSED and FAILED must fail
        self.assertFalse(oracle.test_passed(seen, "tests/test_req.py::test_arb[===arbitrarystring,"))
        # Legacy truncated ID matching only PASSED must pass
        self.assertTrue(oracle.test_passed(seen, "tests/test_req.py::test_ok[a,"))


class TestBaselineTestFilesFilter(unittest.TestCase):
    def test_test_command_omits_nonexistent_files_when_work_given(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            work = Path(tmp_str)
            (work / "tests").mkdir()
            (work / "tests" / "test_existing.py").write_text("def test_ok(): pass\n")
            task = {
                "kind": "git",
                "test_files": ["tests/test_existing.py", "tests/test_new_hidden.py"],
            }
            cmd = trees.test_command(task, work)
            self.assertIn("tests/test_existing.py", cmd)
            self.assertNotIn("tests/test_new_hidden.py", cmd)


class TestMinePrePrComments(unittest.TestCase):
    def test_format_problem_statement_includes_only_pre_pr_human_comments(self):
        issue = {
            "title": "IUP optimisation should compare points as ints",
            "body": "Should we reject floats or round internally?",
            "comments": {
                "nodes": [
                    {
                        "author": {"login": "behdad", "__typename": "User"},
                        "body": "Round internally when comparing for equality.",
                        "createdAt": "2026-10-20T10:00:00Z",
                    },
                    {
                        "author": {"login": "github-actions[bot]", "__typename": "Bot"},
                        "body": "Stale bot notice",
                        "createdAt": "2026-10-21T10:00:00Z",
                    },
                    {
                        "author": {"login": "reviewer", "__typename": "User"},
                        "body": "Thanks for the PR fix!",
                        "createdAt": "2026-10-26T10:00:00Z",
                    },
                ]
            },
        }
        prompt = mine_prs.format_problem_statement(issue, "2026-10-25T00:00:00Z")
        self.assertIn("Round internally when comparing for equality.", prompt)
        self.assertIn("@behdad:", prompt)
        self.assertNotIn("Stale bot notice", prompt)
        self.assertNotIn("Thanks for the PR fix!", prompt)


class TestValidatePrSpecWarnings(unittest.TestCase):
    def test_spec_warnings_flags_whitebox_patterns(self):
        c = {
            "problem_statement": "Section headings should respect comment_prefix.",
            "patch": "+def format_section_comment(prefix, text):\n+    return prefix + text\n",
            "test_patch": (
                "-    assert old_behavior() == 1\n"
                "+    assert format_section_comment('#', 'hi') == '#hi'\n"
                "+    server._serving_future.cancel()\n"
            ),
        }
        warnings = validate_pr.spec_warnings(c)
        self.assertTrue(any("format_section_comment" in w for w in warnings))
        self.assertTrue(any("_serving_future" in w for w in warnings))
        self.assertIn("hidden_tests_modify_existing_assertions", warnings)


class TestReplayGateCeiling(unittest.TestCase):
    def test_ceiling_writes_import_roots_and_normalizes_truncated_ids(self):
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            dst = tmp / "base"
            dst.mkdir()
            task = {
                "id": "demo-task",
                "kind": "git",
                "oracle": {
                    "fail_to_pass": [
                        "tests/test_req.py::TestReq::test_arb[===arbitrarystring,",
                        "tests/test_req.py::TestReq::test_arb[===arbitrarystring,>=",
                        "tests/test_req.py::test_clean[ok]",
                    ]
                },
            }
            with (
                mock.patch.object(replay_gate, "prepare"),
                mock.patch.object(replay_gate, "import_roots", return_value=["src"]),
                mock.patch.object(replay_gate, "git"),
            ):
                replay_gate.build_base_tree(task, None, dst, None, "emi", ceiling=True)
            law_file = dst / ".emi" / "laws" / "test_ceiling_hidden.py"
            self.assertTrue(law_file.exists())
            src = law_file.read_text(encoding="utf-8")
            self.assertIn("IMPORT_ROOTS = ['src']", src)
            self.assertIn("PYTHONPATH", src)
            # Legacy truncated IDs deduplicated to test function node; clean ID preserved
            self.assertIn("'tests/test_req.py::TestReq::test_arb'", src)
            self.assertIn("'tests/test_req.py::test_clean[ok]'", src)


class TestMinerSkipsImportedTasks(unittest.TestCase):
    def test_already_imported_task_is_skipped_and_does_not_fill_the_cap(self):
        prs = [{"number": 1}, {"number": 2}]
        args = mock.Mock(since="2026-10-24", min_issue=300, per_repo=1)
        skipped = mine_prs.Counter()
        with (
            mock.patch.object(mine_prs, "merged_since", return_value=prs),
            mock.patch.object(mine_prs, "reason_to_skip", return_value=None),
            mock.patch.object(mine_prs, "seen", return_value=set()),
            mock.patch.object(mine_prs, "imported", return_value={"o__r-1"}),
            mock.patch.object(mine_prs, "candidate", side_effect=lambda pr, repo: {"n": pr["number"]}),
            mock.patch.object(mine_prs, "size_reason", return_value=None),
        ):
            kept = mine_prs.mine_repo("o/r", args, "token", skipped)
        self.assertEqual(kept, [{"n": 2}])
        self.assertEqual(skipped["already a task (tasks/)"], 1)


class TestCodeEnvPath(unittest.TestCase):
    def test_task_virtualenv_comes_first_on_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / ".venv" / "bin").mkdir(parents=True)
            with mock.patch.object(trees, "import_roots", return_value=[]):
                env = trees.code_env({"kind": "git"}, work)
            first = env["PATH"].split(trees.os.pathsep)[0]
            self.assertEqual(first, str((work / ".venv" / "bin").resolve()))
            self.assertNotIn("PYTHONPATH", env)

    def test_no_virtualenv_leaves_path_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(trees, "import_roots", return_value=["src"]):
                env = trees.code_env({"kind": "git"}, Path(tmp))
            self.assertNotIn("PATH", env)
            self.assertTrue(env["PYTHONPATH"].endswith("/src"))


if __name__ == "__main__":
    unittest.main()
