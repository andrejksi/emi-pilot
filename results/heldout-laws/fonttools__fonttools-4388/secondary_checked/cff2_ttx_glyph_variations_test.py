from io import BytesIO
from pathlib import Path

import pytest
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont


@pytest.fixture
def otf():
    # This repository fixture has a CFF2 glyph whose outline varies with weight.
    path = Path(__file__).parents[2] / "Tests" / "ttLib" / "data" / "I.otf"
    with TTFont(path) as font:
        yield font


@pytest.fixture
def ttx(otf):
    xml = BytesIO()
    otf.saveXML(xml)
    xml.seek(0)
    font = TTFont()
    font.importXML(xml)
    return font


def glyph_outline(font, location):
    pen = RecordingPen()
    font.getGlyphSet(location=location)["I"].draw(pen)
    return pen.value


def test_cff2_glyph_varies_at_weight_1000_after_ttx_import(ttx, otf):
    """New: at weight 1000, getGlyphSet draws the same CFF2 outline after TTX import as from the binary OTF (A1)."""
    assert glyph_outline(ttx, {"wght": 1000}) == glyph_outline(otf, {"wght": 1000})


def test_cff2_glyph_keeps_default_outline_after_ttx_import(ttx, otf):
    """Guard: at the default location, getGlyphSet draws the same CFF2 outline after TTX import as from the binary OTF (A3)."""
    assert glyph_outline(ttx, {}) == glyph_outline(otf, {})


@pytest.mark.parametrize(
    ("location", "first_contour", "stem_curve"),
    [
        (
            {},
            [(175, 55), (45, 40), (45, 0), (325, 0), (325, 40), (195, 55), (175, 55)],
            ((140, 205), (140, 101), (137, 0)),
        ),
        (
            {"wght": 1000},
            [(179, 74), (28, 59), (28, 0), (367, 0), (367, 59), (212, 74), (179, 74)],
            ((98, 205), (98, 101), (95, 0)),
        ),
    ],
)
def test_cff2_glyph_keeps_outline_from_binary_otf(otf, location, first_contour, stem_curve):
    """Guard: the binary OTF keeps the CFF2 glyph's serif contour and stem curve at both reported locations (A2)."""
    outline = glyph_outline(otf, location)
    expected_contour = [
        ("moveTo", (first_contour[0],)),
        *(("lineTo", (point,)) for point in first_contour[1:]),
        ("closePath", ()),
    ]
    assert outline[:len(expected_contour)] == expected_contour
    assert ("curveTo", stem_curve) in outline
