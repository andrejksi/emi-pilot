"""A small calculator: the project every eval case changes."""


def add(a, b):
    return a + b


def mean(values):
    if not values:
        raise ValueError("the mean of nothing")
    return sum(values) / len(values)


def clamp(x, low, high):
    if low > high:
        raise ValueError("low above high")
    return max(low, min(x, high))
