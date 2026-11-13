from ledger import balance


def test_balance():
    assert balance([3, -1, 4]) == 6


def test_balance_of_nothing():
    assert balance([]) == 0
