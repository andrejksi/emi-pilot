import contextlib
import gc
import io
import socket
import subprocess
import sys
import warnings


def test_circlerefs_suite_writes_nothing_to_stderr():
    """Guard: running tornado.test.circlerefs_test through tornado.test.runtests passes and logs no bytes to stderr (A1, A2)."""
    proc = subprocess.run(
        [sys.executable, "-m", "tornado.test.runtests", "tornado.test.circlerefs_test"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "bytes to stderr" not in proc.stderr


def test_leftover_unclosed_socket_garbage_is_not_written_to_stderr():
    """New: when an unclosed socket from an earlier test is still uncollected garbage, entering assert_no_cycle_garbage writes nothing to stderr (A1, A3)."""
    from tornado.test.circlerefs_test import assert_no_cycle_garbage

    class Holder:
        pass

    gc.collect()
    gc.disable()
    try:
        # Simulate the Windows case: a socket left unclosed inside a reference
        # cycle, so it is only freed (with a ResourceWarning) by gc.collect().
        h = Holder()
        h.self = h
        h.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        del h
        err = io.StringIO()
        with warnings.catch_warnings():
            warnings.simplefilter("default", ResourceWarning)
            with contextlib.redirect_stderr(err):
                old_hook = sys.unraisablehook
                sys.unraisablehook = sys.__unraisablehook__
                try:
                    with assert_no_cycle_garbage():
                        pass
                finally:
                    sys.unraisablehook = old_hook
    finally:
        gc.enable()
        gc.collect()
    assert err.getvalue() == ""
