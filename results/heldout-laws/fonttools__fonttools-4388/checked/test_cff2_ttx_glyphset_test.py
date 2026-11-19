import io
import os

from hypothesis import given, settings, strategies as st

from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SRC = os.path.join(_REPO, "Tests", "varLib", "data", "master_ttx_varfont_otf", "TestCFF2VF.ttx")


def _fonts():
    src = TTFont()
    src.importXML(_SRC)
    b = io.BytesIO()
    src.save(b)
    b.seek(0)
    otf = TTFont(b)
    x = io.BytesIO()
    otf.saveXML(x)
    x.seek(0)
    ttx = TTFont()
    ttx.importXML(x)
    return otf, ttx


OTF, TTX = _fonts()


def _bounds(font, glyph, location):
    gs = font.getGlyphSet(location=location)
    pen = BoundsPen(gs)
    gs[glyph].draw(pen)
    return pen.bounds


def test_ttx_imported_cff2_draws_varied_outline_at_wght_900():
    """New: a CFF2 font imported from TTX draws glyph "A" at wght=900 with the varied bounds (0, 0, 600, 650), like the binary font (A1, A2)."""
    assert _bounds(TTX, "A", {"wght": 900}) == (0.0, 0, 600.0, 650.0)


def test_ttx_imported_cff2_draws_varied_outline_for_T():
    """New: a CFF2 font imported from TTX draws glyph "T" at wght=900 with the varied bounds (27, 0, 573, 650) (A1, A2)."""
    assert _bounds(TTX, "T", {"wght": 900}) == (27.0, 0, 573.0, 650.0)


@settings(max_examples=15, deadline=None)
@given(
    glyph=st.sampled_from(["A", "T", "glyph00003"]),
    wght=st.sampled_from([200.0, 300.0, 650.0, 900.0]),
)
def test_ttx_imported_cff2_matches_binary_at_any_location(glyph, wght):
    """New: for any glyph and wght location, a CFF2 font imported from TTX draws the same bounds as the same font loaded from binary (A1, A2)."""
    assert _bounds(TTX, glyph, {"wght": wght}) == _bounds(OTF, glyph, {"wght": wght})


def test_default_location_from_ttx_keeps_default_outline():
    """Guard: at the default location a CFF2 font imported from TTX still draws glyph "A" with default bounds (31, 0, 569, 656) (A3)."""
    assert _bounds(TTX, "A", {}) == (31, 0, 569, 656)


def test_binary_cff2_still_draws_varied_outline():
    """Guard: a CFF2 font loaded from binary still draws glyph "A" at wght=900 with bounds (0, 0, 600, 650) (A3)."""
    assert _bounds(OTF, "A", {"wght": 900}) == (0.0, 0, 600.0, 650.0)
