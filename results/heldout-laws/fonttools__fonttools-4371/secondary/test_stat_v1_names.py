from pathlib import Path

import pytest

from fontTools.ttLib import TTFont, newTable
from fontTools.varLib.instancer import instantiateVariableFont


@pytest.fixture
def font_with_stat_v1():
    font = TTFont()
    fixture = (
        Path(__file__).resolve().parents[2]
        / "Tests/varLib/instancer/data/PartialInstancerTest-VF.ttx"
    )
    font.importXML(fixture)
    font["STAT"].table.Version = 0x00010000
    stat_v1 = newTable("STAT")
    stat_v1.decompile(font["STAT"].compile(font), font)
    font["STAT"] = stat_v1
    return font


def test_stat_v1_updates_instance_names(font_with_stat_v1):
    """New: a version 1.0 STAT table yields corrected names for a Black instance (A1)."""
    instance = instantiateVariableFont(
        font_with_stat_v1, {"wght": 900, "wdth": 100}, updateFontNames=True
    )

    assert instance["name"].getName(4, 3, 1, 0x409).toUnicode() == "Test Variable Font Black"


def test_stat_v1_uses_the_fonts_subfamily_as_fallback(font_with_stat_v1):
    """New: a version 1.0 STAT table uses the font's subfamily when all axis names are elided (A2)."""
    font_with_stat_v1["name"].setName("Bold", 2, 3, 1, 0x409)
    for axis_value in font_with_stat_v1["STAT"].table.AxisValueArray.AxisValue:
        axis_value.Flags |= 0x0002

    instance = instantiateVariableFont(
        font_with_stat_v1, {"wght": 400, "wdth": 100}, updateFontNames=True
    )

    assert instance["name"].getName(4, 3, 1, 0x409).toUnicode() == "Test Variable Font Bold"
