import io
import random

from hypothesis import given, settings, strategies as st

from Bio import bgzf


def _write_and_read(data):
    handle = io.BytesIO()
    w = bgzf.BgzfWriter(fileobj=handle, mode="wb")
    w.write(data)
    w.flush()
    raw = handle.getvalue()
    w._handle = io.BytesIO()  # avoid closing the BytesIO we read from
    w.close()
    r = bgzf.BgzfReader(fileobj=io.BytesIO(raw + bgzf._bgzf_eof), mode="rb")
    return r.read()


def test_random_65536_bytes_write_and_close_without_error():
    """New: writing random.Random(42).randbytes(65536) to a BgzfWriter and closing it raises no error (A1)."""
    w = bgzf.BgzfWriter(fileobj=io.BytesIO(), mode="wb")
    w.write(random.Random(42).randbytes(65536))
    w.close()


def test_random_65500_bytes_write_and_close_without_error():
    """New: writing random.Random(42).randbytes(65500) to a BgzfWriter and closing it raises no error (A2)."""
    w = bgzf.BgzfWriter(fileobj=io.BytesIO(), mode="wb")
    w.write(random.Random(42).randbytes(65500))
    w.close()


def test_random_65536_bytes_round_trip():
    """New: random.Random(42).randbytes(65536) written with BgzfWriter reads back unchanged (A1)."""
    data = random.Random(42).randbytes(65536)
    assert _write_and_read(data) == data


@settings(max_examples=25, deadline=None)
@given(
    size=st.integers(min_value=65491, max_value=65536),
    seed=st.integers(min_value=0, max_value=2**32 - 1),
)
def test_any_incompressible_block_size_round_trips(size, seed):
    """New: random data of any size from 65,491 to 65,536 bytes is written without error and reads back unchanged (A3)."""
    data = random.Random(seed).randbytes(size)
    assert _write_and_read(data) == data
