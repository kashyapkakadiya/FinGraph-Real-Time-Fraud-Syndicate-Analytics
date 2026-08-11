import random
import uuid
from datetime import datetime, timezone

from entities import Bank, Person, Account


class World:
    """Holds the pool of banks, people, and accounts transactions are drawn from."""

    def __init__(self, num_banks=5, num_people=200):
        self.banks = [Bank() for _ in range(num_banks)]
        self.people = [Person() for _ in range(num_people)]
        self.accounts = [
            Account(owner=p, bank=random.choice(self.banks)) for p in self.people
        ]

    def random_account(self, exclude=None):
        pool = [a for a in self.accounts if a is not exclude]
        return random.choice(pool)


def make_transaction(world: World) -> dict:
    """A single normal, non-suspicious transaction between two random accounts."""
    sender = world.random_account()
    receiver = world.random_account(exclude=sender)
    amount = round(random.uniform(10, 5000), 2)

    return {
        "transaction_id": f"TXN-{uuid.uuid4().hex[:10].upper()}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sender_account": sender.account_id,
        "sender_person": sender.owner.person_id,
        "sender_ip": sender.owner.ip_address,
        "receiver_account": receiver.account_id,
        "receiver_person": receiver.owner.person_id,
        "receiver_ip": receiver.owner.ip_address,
        "amount": amount,
        "sender_bank": sender.bank.bank_id,
        "receiver_bank": receiver.bank.bank_id,
        "is_synthetic_fraud": False,
    }


if __name__ == "__main__":
    world = World()
    for _ in range(10):
        print(make_transaction(world))