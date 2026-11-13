"""A ledger: the project the law cases change. Its laws hold `refund`,
which no test covers, and `fee`, whose law is not held yet."""


def balance(entries):
    return sum(entries)


def refund(amount):
    return -amount


def fee(amount):
    # one percent is what the person wants; this takes two
    return amount // 50
