from io import BytesIO

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.psCharStrings import T2CharString
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont


@pytest.fixture
def otf():
    builder = FontBuilder(1000, isTTF=False)
    builder.setupGlyphOrder([".notdef", "period"])
    builder.setupCharacterMap({ord("."): "period"})
    builder.setupHorizontalMetrics({".notdef": (500, 0), "period": (500, 60)})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": "CFF2 Test", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    builder.setupFvar([("wght", 100, 400, 1000, "Weight")], [])

    # The default rectangle starts at x=60, is 50 units wide, and is 120 tall.
    # Each blend applies the following delta at the maximum weight.
    period = T2CharString(program=[
        60, -30, 1, "blend", "hmoveto",
        50, 140, 1, "blend", "hlineto",
        120, 180, 1, "blend", "vlineto",
        -50, -140, 1, "blend", "hlineto",
    ])
    builder.setupCFF2(
        {".notdef": T2CharString(program=[]), "period": period},
        regions=[{"wght": (0, 1, 1)}],
    )
    binary = BytesIO()
    builder.save(binary)
    binary.seek(0)
    with TTFont(binary) as font:
        yield font


@pytest.fixture
def ttx(otf):
    xml = BytesIO()
    otf.saveXML(xml)
    xml.seek(0)
    font = TTFont()
    font.importXML(xml)
    return font


def period_bounds(font, location):
    pen = BoundsPen(None)
    font.getGlyphSet(location=location)["period"].draw(pen)
    return pen.bounds


def test_period_varies_at_weight_1000_after_ttx_import(ttx):
    """New: getGlyphSet draws the CFF2 period with bounds (30.0, 0, 220.0, 300.0) at weight 1000 after TTX import (A1)."""
    assert period_bounds(ttx, {"wght": 1000}) == (30.0, 0, 220.0, 300.0)


def test_period_keeps_default_bounds_after_ttx_import(ttx):
    """Guard: getGlyphSet draws the CFF2 period with bounds (60, 0, 110, 120) at the default location after TTX import (A3)."""
    assert period_bounds(ttx, {}) == (60, 0, 110, 120)


@pytest.mark.parametrize(
    ("location", "expected"),
    [({}, (60, 0, 110, 120)), ({"wght": 1000}, (30.0, 0, 220.0, 300.0))],
)
def test_period_keeps_bounds_from_binary_otf(otf, location, expected):
    """Guard: getGlyphSet draws the CFF2 period with the reported bounds at both locations when loaded from binary OTF (A2)."""
    assert period_bounds(otf, location) == expected
