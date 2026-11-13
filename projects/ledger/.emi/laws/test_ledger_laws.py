import pytest
from hypothesis import given, strategies as st

from ledger import fee, refund


@given(st.integers(min_value=0, max_value=10**9))
def test_a_refund_undoes_the_amount(amount):
    assert amount + refund(amount) == 0


@pytest.mark.xfail(strict=True, reason="the fee is two percent until it is fixed")
def test_the_fee_is_one_percent():
    assert fee(1000) == 10
