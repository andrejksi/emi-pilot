"""Rules for Git.get_remote_url parsing the output of `git remote -v`."""

from conan.test.utils.mocks import ConanFileMock
from conan.tools.scm import Git

TREELESS = (
    "origin  ssh://git@devstack.vwgroup.com:7999/e3swcdep/googletest.git (fetch) [tree:0]\n"
    "origin  ssh://git@devstack.vwgroup.com:7999/e3swcdep/googletest.git (push)"
)
PLAIN = (
    "origin  ssh://git@devstack.vwgroup.com:7999/e3swcdep/googletest.git (fetch)\n"
    "origin  ssh://git@devstack.vwgroup.com:7999/e3swcdep/googletest.git (push)"
)


def _git_answering(output):
    """A Git whose `git remote -v` prints the given output."""
    git = Git(ConanFileMock())
    git.run = lambda cmd, hidden_output=None: output if cmd == "remote -v" else ""
    return git


def test_treeless_clone_remote_url_drops_fetch_and_filter_tokens():
    """New: in a treeless clone, where `git remote -v` adds "[tree:0]" after "(fetch)", the origin URL is returned without "(fetch)" or "[tree:0]"."""
    assert _git_answering(TREELESS).get_remote_url() == "ssh://git@devstack.vwgroup.com:7999/e3swcdep/googletest.git"


def test_plain_clone_remote_url_is_still_parsed():
    """Guard: in an ordinary clone, where `git remote -v` prints three tokens per line, the origin URL is returned without "(fetch)"."""
    assert _git_answering(PLAIN).get_remote_url() == "ssh://git@devstack.vwgroup.com:7999/e3swcdep/googletest.git"
