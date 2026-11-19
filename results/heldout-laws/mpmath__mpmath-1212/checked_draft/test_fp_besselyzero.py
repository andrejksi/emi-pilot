from mpmath import fp, mp, mpf


def test_fp_besselyzero_2_1_matches_mp():
    """New: fp.besselyzero(2, 1) returns about 3.3842417671495935 instead of raising ZeroDivisionError (A1)."""
    assert abs(fp.besselyzero(2, 1) - 3.3842417671495935) < 1e-9


def test_mp_besselyzero_2_1_unchanged():
    """Guard: mp.besselyzero(2, 1) still returns 3.3842417671495935 (A2)."""
    mp.dps = 15
    assert abs(mp.besselyzero(2, 1) - mpf('3.3842417671495935')) < mpf(10) ** -14
