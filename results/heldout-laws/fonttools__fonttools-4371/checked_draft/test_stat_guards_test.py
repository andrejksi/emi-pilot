import os

from fontTools import ttLib
from fontTools.varLib import instancer

DATA = os.path.join(
    os.path.dirname(__file__), "..", "..", "Tests", "varLib", "instancer", "data"
)


def _font():
    f = ttLib.TTFont()
    f.importXML(os.path.join(DATA, "PartialInstancerTest-VF.ttx"))
    return f


def test_stat_with_elided_fallback_still_names_black():
    """Guard: with a STAT that has ElidedFallbackNameID, instancing at wght 900 still yields the Black names (A3)."""
    f = _font()
    instancer.names.updateNameTable(f, {"wght": 900})
    n = f["name"]
    assert (n.getName(1, 3, 1, 0x409).toUnicode(), n.getName(17, 3, 1, 0x409).toUnicode()) == (
        "Test Variable Font Black",
        "Black",
    )


def test_stat_elided_fallback_name_is_still_used():
    """Guard: when all axis values are elided and ElidedFallbackNameID points to Black, the typographic subfamily is still Black (A3)."""
    f = _font()
    stat = f["STAT"].table
    for v in stat.AxisValueArray.AxisValue:
        v.Flags |= instancer.names.ELIDABLE_AXIS_VALUE_NAME
    stat.ElidedFallbackNameID = 266
    instancer.names.updateNameTable(f, {"wght": 400})
    n = f["name"]
    assert (n.getName(2, 3, 1, 0x409).toUnicode(), n.getName(17, 3, 1, 0x409).toUnicode()) == (
        "Regular",
        "Black",
    )
