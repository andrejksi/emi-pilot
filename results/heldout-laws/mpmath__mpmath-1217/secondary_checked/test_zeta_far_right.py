from mpmath import mp, zeta


def test_zeta_far_right_imaginary_part():
    """New: The imaginary part of zeta at 50 + 5j matches 2.82881957300551842714082e-16 at default precision (A1)."""
    with mp.workdps(15):
        assert mp.almosteq(
            zeta(50 + 5j).imag,
            mp.mpf("2.82881957300551842714082e-16"),
            rel_eps=mp.mpf("2e-15"),
            abs_eps=0,
        )


def test_zeta_far_right_real_part():
    """Guard: The real part of zeta at 50 + 5j rounds to 0.9999999999999991 at default precision (A2)."""
    with mp.workdps(15):
        assert zeta(50 + 5j).real == mp.mpf("0.9999999999999991")
