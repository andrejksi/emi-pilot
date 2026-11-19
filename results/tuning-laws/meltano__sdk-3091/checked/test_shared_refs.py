"""Rules the task adds: a reference used by several properties is resolved for each of them."""

from __future__ import annotations

import string
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis.configuration import set_hypothesis_home_dir
from hypothesis import strategies as st

from singer_sdk.singerlib import resolve_schema_references

# This project sets norecursedirs (dropping pytest's default ignores) and turns warnings
# into errors, so a .hypothesis folder in the repository breaks the next collection.
# Keep Hypothesis' storage outside the repository.
set_hypothesis_home_dir(Path(tempfile.gettempdir()) / "emi-laws-hypothesis")

REFS = {"components": {"schemas": {"ComputeUnit": {"type": "number"}}}}


def test_two_properties_sharing_a_reference_both_resolve():
    """New: when min_compute_units and max_compute_units both use components#/schemas/ComputeUnit, both resolve to {"type": "number"}."""
    schema = {
        "type": "object",
        "properties": {
            "min_compute_units": {"$ref": "components#/schemas/ComputeUnit"},
            "max_compute_units": {"$ref": "components#/schemas/ComputeUnit"},
        },
    }
    assert resolve_schema_references(schema, {"components": {"schemas": {"ComputeUnit": {"type": "number"}}}}) == {
        "type": "object",
        "properties": {
            "min_compute_units": {"type": "number"},
            "max_compute_units": {"type": "number"},
        },
    }


@settings(database=None)
@given(st.lists(st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=8), min_size=1, max_size=6, unique=True))
def test_every_property_sharing_a_reference_resolves(names):
    """New: however many properties use the same reference, every one of them resolves to the referenced schema."""
    schema = {"type": "object", "properties": {n: {"$ref": "components#/schemas/ComputeUnit"} for n in names}}
    result = resolve_schema_references(schema, {"components": {"schemas": {"ComputeUnit": {"type": "number"}}}})
    assert result == {"type": "object", "properties": {n: {"type": "number"} for n in names}}
