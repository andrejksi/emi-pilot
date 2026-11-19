from mpmath import mp, mpc, mpf, zeta


def test_zeta_50_plus_5j_imaginary_part_is_accurate():
    """New: zeta(50+5j) has imaginary part 2.82881957300551842714082e-16 to about 14 significant digits (A1)."""
    mp.dps = 15
    expected = mpf('2.82881957300551842714082e-16')
    assert abs(zeta(mpc(50, 5)).imag - expected) < expected * mpf(10) ** -13


def test_zeta_50_plus_5j_matches_direct_summation():
    """New: zeta(50+5j) agrees with direct summation 1+1/2**x+...+1/5**x in both parts to about 14 digits (A2)."""
    mp.dps = 15
    x = mpc(50, 5)
    direct = 1 + 1 / mpf(2) ** x + 1 / mpf(3) ** x + 1 / mpf(4) ** x + 1 / mpf(5) ** x
    z = zeta(x)
    assert abs(z.real - direct.real) < mpf(10) ** -14
    assert abs(z.imag - direct.imag) < abs(direct.imag) * mpf(10) ** -13
