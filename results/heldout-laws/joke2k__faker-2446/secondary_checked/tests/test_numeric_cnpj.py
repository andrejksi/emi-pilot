from collections import Counter
from itertools import combinations, cycle, product

from faker import Faker


def test_numeric_cnpj_root_digits_are_sampled_independently():
    """New: Each of the eight numeric CNPJ root positions independently samples a decimal digit and can repeat digits (A1)."""
    fake = Faker("pt_BR")
    fake.seed_instance(2446)
    roots = [fake.company_id()[:8] for _ in range(10_000)]

    for first, second in combinations(range(8), 2):
        pair_counts = Counter((root[first], root[second]) for root in roots)
        for digit_pair in product("0123456789", repeat=2):
            # Independent decimal draws yield about 100 of each pair, with wide sampling tolerance.
            assert 40 <= pair_counts[digit_pair] <= 170, (first, second, digit_pair)


def test_numeric_cnpj_checksum_stays_valid():
    """Guard: Numeric CNPJs carry valid check digits (A2)."""
    fake = Faker("pt_BR")
    fake.seed_instance(2446)

    for _ in range(20):
        digits = [int(digit) for digit in fake.company_id()]
        for check_position in (12, 13):
            weights = cycle(range(2, 10))
            total = sum(digit * weight for digit, weight in zip(reversed(digits[:check_position]), weights))
            remainder = total % 11
            assert digits[check_position] == (11 - remainder if remainder >= 2 else 0)
