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


def median(values):
    if not values:
        raise ValueError("the median of nothing")
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2
