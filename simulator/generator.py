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


def generate_mixed_stream(world: World, normal_count=200, fraud_ring_count=2, smurfs_per_ring=50):
    """A realistic batch: mostly normal transactions with occasional syndicate activity buried inside."""
    from syndicate import generate_starburst_pattern

    stream = [make_transaction(world) for _ in range(normal_count)]
    for _ in range(fraud_ring_count):
        stream.extend(generate_starburst_pattern(world, num_smurfs=smurfs_per_ring))
    random.shuffle(stream)
    return stream

if __name__ == "__main__":
    world = World()
    batch = generate_mixed_stream(world)
    fraud_count = sum(1 for t in batch if t["is_synthetic_fraud"])
    print(f"Generated {len(batch)} transactions, {fraud_count} are part of a smurfing syndicate")