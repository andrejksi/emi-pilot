import os
import subprocess
import sys
from datetime import datetime, timezone

from kombu.asynchronous.timer import EPOCH, to_timestamp


def _run_without_tzdata(tmp_path, code):
    env = dict(os.environ)
    env['PYTHONTZPATH'] = str(tmp_path)
    return subprocess.run(
        [sys.executable, '-c', code],
        env=env, capture_output=True, text=True, timeout=60,
    )


def test_import_kombu_asynchronous_without_tz_data(tmp_path):
    """New: `import kombu.asynchronous` succeeds when PYTHONTZPATH points at an empty dir and no tzdata package is installed (A1)."""
    code = (
        "import sys; sys.modules['tzdata'] = None\n"
        "import kombu.asynchronous\n"
        "print('ok')\n"
    )
    proc = _run_without_tzdata(tmp_path, code)
    assert (proc.returncode, proc.stdout.strip()) == (0, 'ok'), proc.stderr


def test_to_timestamp_works_without_tz_data(tmp_path):
    """New: without any time zone data, to_timestamp(datetime(2030, 1, 1)) equals to_timestamp of the same datetime in UTC (A1, A2)."""
    code = (
        "import sys; sys.modules['tzdata'] = None\n"
        "from datetime import datetime, timezone\n"
        "import kombu.asynchronous.timer as tm\n"
        "from kombu.asynchronous.timer import to_timestamp\n"
        "tm._time = lambda: 0.0\n"
        "d = datetime(2030, 1, 1)\n"
        "t = lambda: 0.0\n"
        "print(to_timestamp(d, time=t) == to_timestamp(d.replace(tzinfo=timezone.utc), time=t))\n"
    )
    proc = _run_without_tzdata(tmp_path, code)
    assert (proc.returncode, proc.stdout.strip()) == (0, 'True'), proc.stderr


def test_epoch_is_unix_epoch_in_utc():
    """Guard: EPOCH is the Unix epoch in UTC (A2)."""
    assert EPOCH == datetime(1970, 1, 1, tzinfo=timezone.utc)


def test_naive_datetime_defaults_to_utc(monkeypatch):
    """Guard: to_timestamp(datetime(2030, 1, 1)) equals to_timestamp of the same datetime in UTC (A2)."""
    monkeypatch.setattr('kombu.asynchronous.timer._time', lambda: 0.0)
    d = datetime(2030, 1, 1)
    t = lambda: 0.0  # noqa: E731
    assert to_timestamp(d, time=t) == to_timestamp(d.replace(tzinfo=timezone.utc), time=t)


def test_naive_datetime_ten_seconds_after_epoch(monkeypatch):
    """Guard: with both clocks at 0, to_timestamp(datetime(1970, 1, 1, 0, 0, 10)) is 10.0, read as UTC (A2)."""
    monkeypatch.setattr('kombu.asynchronous.timer._time', lambda: 0.0)
    assert to_timestamp(datetime(1970, 1, 1, 0, 0, 10), time=lambda: 0.0) == 10.0
