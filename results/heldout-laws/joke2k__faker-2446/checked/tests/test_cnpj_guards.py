import re

from faker import Faker
from faker.providers.company.pt_BR import company_id_checksum


def _fake(seed):
    fake = Faker("pt_BR")
    fake.seed_instance(seed)
    return fake


def test_numeric_company_id_keeps_shape_and_valid_checksum():
    """Guard: numeric pt_BR company_id stays eight digits + 0001 + two valid check digits (A3)."""
    fake = _fake(1)
    for _ in range(500):
        cid = fake.company_id()
        assert re.fullmatch(r"\d{8}0001\d{2}", cid)
        values = [ord(c) - 48 for c in cid[:12]]
        assert cid[12:] == "".join(str(d) for d in company_id_checksum(values))


def test_numeric_cnpj_keeps_format():
    """Guard: numeric pt_BR cnpj stays formatted as NN.NNN.NNN/0001-NN (A3)."""
    fake = _fake(2)
    for _ in range(200):
        assert re.fullmatch(r"\d{2}\.\d{3}\.\d{3}/0001-\d{2}", fake.cnpj())


def test_alphanumeric_company_id_keeps_working():
    """Guard: alphanumeric pt_BR company_id stays twelve [0-9A-Z] chars plus two valid check digits (A4)."""
    fake = _fake(3)
    for _ in range(200):
        cid = fake.company_id(use_alphanumeric=True)
        assert re.fullmatch(r"[0-9A-Z]{12}\d{2}", cid)
        values = [ord(c) - 48 for c in cid[:12]]
        assert cid[12:] == "".join(str(d) for d in company_id_checksum(values))

