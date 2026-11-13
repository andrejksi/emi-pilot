from shop import discounted, total


def test_total():
    assert total([1, 2, 3]) == 6


def test_discounted():
    assert discounted(200, 50) == 100
