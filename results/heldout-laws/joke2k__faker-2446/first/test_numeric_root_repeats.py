from faker import Faker


def _roots(n, seed=2446):
    fake = Faker("pt_BR")
    fake.seed_instance(seed)
    return [fake.company_id()[:8] for _ in range(n)]


def test_numeric_roots_can_contain_repeated_digits():
    """New: among 10,000 numeric pt_BR company_id roots, some contain a repeated digit, so not all have eight distinct digits (A1, A2)."""
    roots = _roots(10_000)
    assert sum(len(set(root)) < 8 for root in roots) > 0
    assert not all(len(set(root)) == 8 for root in roots)


def test_most_numeric_roots_repeat_a_digit_like_independent_sampling():
    """New: with each root digit sampled independently, most numeric pt_BR roots (about 98%) contain a repeated digit (A2)."""
    roots = _roots(2_000, seed=7)
    assert sum(len(set(root)) < 8 for root in roots) > 1_800


def test_cnpj_root_can_repeat_digits():
    """New: formatted numeric pt_BR cnpj values also show roots with repeated digits (A1, A2)."""
    fake = Faker("pt_BR")
    fake.seed_instance(99)
    roots = [fake.cnpj().replace(".", "")[:8] for _ in range(500)]
    assert any(len(set(root)) < 8 for root in roots)
