import isort


def _sorted_lines():
    out = isort.code(
        "import sys\n",
        comment_prefix="",
        import_heading_stdlib="#region Standard Library",
        import_footer_stdlib="#endregion Standard Library",
    )
    return [line for line in out.splitlines() if line.strip()]


def test_stdlib_heading_uses_empty_comment_prefix():
    """New: with comment_prefix "" and import_heading_stdlib "#region Standard Library", the first output line is "#region Standard Library" (A1)."""
    assert _sorted_lines()[0] == "#region Standard Library"


def test_stdlib_footer_uses_empty_comment_prefix():
    """New: with comment_prefix "" and import_footer_stdlib "#endregion Standard Library", the last output line is "#endregion Standard Library" (A1)."""
    assert _sorted_lines()[-1] == "#endregion Standard Library"


def test_import_stays_between_region_heading_and_footer():
    """New: with comment_prefix "" the output is exactly the heading "#region Standard Library", then "import sys", then the footer "#endregion Standard Library", ignoring blank lines (A1)."""
    assert _sorted_lines() == ["#region Standard Library", "import sys", "#endregion Standard Library"]
