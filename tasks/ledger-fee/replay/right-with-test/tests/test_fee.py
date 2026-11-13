from ledger import fee


def test_fee_is_one_percent():
    assert fee(1000) == 10
    assert fee(200) == 2
