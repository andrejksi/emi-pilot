from ledger import fee


def test_one_percent():
    assert fee(1000) == 10


def test_rounded_down():
    assert fee(150) == 1
    assert fee(199) == 1
    assert fee(99) == 0


def test_nothing():
    assert fee(0) == 0
