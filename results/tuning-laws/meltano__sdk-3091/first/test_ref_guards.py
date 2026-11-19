"""Reference resolution that already holds and must keep holding."""

from __future__ import annotations

from singer_sdk.singerlib import resolve_schema_references


def test_a_single_reference_resolves():
    """Guard: a property using a reference once resolves to the referenced schema."""
    schema = {"type": "object", "properties": {"units": {"$ref": "components#/schemas/ComputeUnit"}}}
    refs = {"components": {"schemas": {"ComputeUnit": {"type": "number"}}}}
    assert resolve_schema_references(schema, refs) == {"type": "object", "properties": {"units": {"type": "number"}}}


def test_a_circular_reference_still_terminates():
    """Guard: a schema that refers to itself through array items still resolves, without endless recursion, to its first level."""
    schema = {"type": "object", "properties": {"filter": {"$ref": "components#/schemas/Filter"}}}
    refs = {
        "components": {
            "schemas": {
                "Filter": {
                    "properties": {
                        "name": {"type": "string"},
                        "clauses": {"type": "array", "items": {"$ref": "components#/schemas/Filter"}},
                    },
                },
            },
        },
    }
    result = resolve_schema_references(schema, refs)
    props = result["properties"]["filter"]["properties"]
    assert (props["name"], props["clauses"]["type"]) == ({"type": "string"}, "array")
