from isort import code


def test_empty_comment_prefix_leaves_section_region_markers_unchanged():
    """New: An empty comment prefix leaves both configured region marker lines unchanged around the import (A1)."""
    assert [
        line
        for line in code(
            "import sys\n",
            comment_prefix="",
            import_heading_stdlib="#region Standard Library",
            import_footer_stdlib="#endregion Standard Library",
        ).splitlines()
        if line
    ] == ["#region Standard Library", "import sys", "#endregion Standard Library"]
