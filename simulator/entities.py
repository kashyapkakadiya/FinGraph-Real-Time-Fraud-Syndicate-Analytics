import random
import uuid
from dataclasses import dataclass, field
from faker import Faker

fake = Faker()


@dataclass
class Bank:
    bank_id: str = field(default_factory=lambda: f"BANK-{uuid.uuid4().hex[:6].upper()}")
    name: str = field(default_factory=fake.company)
    country: str = field(default_factory=fake.country)


@dataclass
class Person:
    person_id: str = field(default_factory=lambda: f"PER-{uuid.uuid4().hex[:8].upper()}")
    name: str = field(default_factory=fake.name)
    ip_address: str = field(default_factory=fake.ipv4_public)


@dataclass
class Account:
    account_id: str = field(default_factory=lambda: f"ACC-{uuid.uuid4().hex[:10].upper()}")
    owner: Person = None
    bank: Bank = None
    balance: float = field(default_factory=lambda: round(random.uniform(500, 50000), 2))