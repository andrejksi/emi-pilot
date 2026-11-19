import subprocess
import sys
from pathlib import Path


NO_TIMEZONE_DATABASE = """
import sys
import zoneinfo

sys.path.insert(0, sys.argv[1])
zoneinfo.reset_tzpath(())
sys.modules['tzdata'] = None
"""


def run_without_timezone_database(code):
    project_root = Path(__file__).resolve().parents[2]
    return subprocess.run(
        [sys.executable, '-I', '-B', '-c', NO_TIMEZONE_DATABASE + code, str(project_root)],
        capture_output=True,
        text=True,
    )


def test_import_asynchronous_without_timezone_database():
    """New: `import kombu.asynchronous` succeeds without a timezone database (A1)."""
    result = run_without_timezone_database('import kombu.asynchronous')
    assert result.returncode == 0, result.stderr


def test_naive_timer_datetime_defaults_to_utc_without_timezone_database():
    """New: the timer converts a naive datetime as UTC without a timezone database (A2)."""
    result = run_without_timezone_database("""
from datetime import datetime
from unittest.mock import patch

from kombu.asynchronous import timer

with patch.object(timer, '_time', return_value=100):
    assert timer.to_timestamp(datetime(1970, 1, 1, 0, 0, 30), time=lambda: 100) == 30
""")
    assert result.returncode == 0, result.stderr
