"""Regression laws for writing incompressible BGZF data."""

import gzip
from random import Random

from Bio.bgzf import BgzfReader, BgzfWriter


def round_trip_bgzf(path, data):
    with path.open("wb") as stream:
        writer = BgzfWriter(fileobj=stream, mode="wb")
        writer.write(data)
        writer.close()

    with BgzfReader(filename=path, mode="rb") as reader:
        return reader.read(len(data) + 1)


def test_buffered_random_data_round_trips(tmp_path):
    """New: the 65,500-byte random sample writes and closes as BGZF and reads back byte for byte (A1)."""
    data = Random(42).randbytes(65500)

    assert round_trip_bgzf(tmp_path / "buffered.bgz", data) == data


def test_full_block_random_data_round_trips(tmp_path):
    """New: the 65,536-byte random sample writes and closes as BGZF and reads back byte for byte (A1)."""
    data = Random(42).randbytes(65536)

    assert round_trip_bgzf(tmp_path / "full-block.bgz", data) == data


def test_already_compressed_data_round_trips(tmp_path):
    """New: already-compressed input writes and closes as BGZF and reads back byte for byte (A1)."""
    data = gzip.compress(Random(42).randbytes(65536), mtime=0)

    assert round_trip_bgzf(tmp_path / "already-compressed.bgz", data) == data
