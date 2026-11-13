"""A small shop: the project the rules cases change."""


def total(prices):
    if any(p < 0 for p in prices):
        raise ValueError("a negative price")
    return sum(prices)


def discounted(price, percent):
    return price - price * percent // 100
