import os

import pytest
from fontTools import ttLib
from fontTools.varLib import instancer

DATA = os.path.join(
    os.path.dirname(__file__), "..", "..", "Tests", "varLib", "instancer", "data"
)


def _font(statV10=True):
    f = ttLib.TTFont()
    f.importXML(os.path.join(DATA, "PartialInstancerTest-VF.ttx"))
    if statV10:
        stat = f["STAT"].table
        stat.Version = 0x00010000
        del stat.ElidedFallbackNameID
    return f


def _names(f):
    n = f["name"]
    out = {}
    for i in (1, 2, 3, 6, 16, 17):
        r = n.getName(i, 3, 1, 0x409)
        out[i] = r.toUnicode() if r is not None else None
    return out


def test_v10_stat_regular_instance_gets_names():
    """New: with a version 1.0 STAT lacking ElidedFallbackNameID, instancing at wght 400 updates names to the Regular instance names (A1, A2)."""
    f = _font()
    instancer.names.updateNameTable(f, {"wght": 400})
    names = _names(f)
    assert (names[1], names[2], names[3], names[6]) == (
        "Test Variable Font",
        "Regular",
        "2.001;GOOG;TestVariableFont-Regular",
        "TestVariableFont-Regular",
    )


def test_v10_stat_black_instance_gets_names():
    """New: with a version 1.0 STAT lacking ElidedFallbackNameID, instancing at wght 900 updates names to the Black instance names (A1, A2)."""
    f = _font()
    instancer.names.updateNameTable(f, {"wght": 900})
    assert _names(f) == {
        1: "Test Variable Font Black",
        2: "Regular",
        3: "2.001;GOOG;TestVariableFont-Black",
        6: "TestVariableFont-Black",
        16: "Test Variable Font",
        17: "Black",
    }


def test_v10_stat_after_save_and_reload_gets_names():
    """New: a version 1.0 STAT font saved and reloaded from binary still gets its names updated when instancing at wght 900 (A1, A2)."""
    import io

    buf = io.BytesIO()
    _font().save(buf)
    buf.seek(0)
    f = ttLib.TTFont(buf)
    instancer.names.updateNameTable(f, {"wght": 900})
    names = _names(f)
    assert (names[1], names[6], names[17]) == (
        "Test Variable Font Black",
        "TestVariableFont-Black",
        "Black",
    )


def test_v10_stat_all_elided_falls_back_to_subfamily_name():
    """New: with a version 1.0 STAT whose axis values are all elided, the style falls back to the font's subFamilyName (nameID 2) (A2)."""
    f = _font()
    f["name"].setName("Bold", 2, 3, 1, 0x409)
    for v in f["STAT"].table.AxisValueArray.AxisValue:
        v.Flags |= instancer.names.ELIDABLE_AXIS_VALUE_NAME
    instancer.names.updateNameTable(f, {"wght": 400})
    names = _names(f)
    assert (names[1], names[2]) == ("Test Variable Font", "Bold")
