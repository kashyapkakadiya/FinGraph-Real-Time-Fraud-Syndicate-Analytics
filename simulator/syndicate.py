import random
import uuid
from datetime import datetime, timezone

from entities import Bank, Person, Account
from generator import World


def make_shell_account(world: World) -> Account:
    """A dedicated 'collector' account — the syndicate's destination."""
    owner = Person()
    bank = random.choice(world.banks)
    return Account(owner=owner, bank=bank, balance=round(random.uniform(0, 500), 2))


def make_smurf_accounts(world: World, count: int) -> list[Account]:
    """Distinct 'mule' accounts with no shared IPs — each funnels micro-transactions."""
    accounts = []
    for _ in range(count):
        owner = Person()
        bank = random.choice(world.banks)
        accounts.append(Account(owner=owner, bank=bank))
    return accounts


def generate_starburst_pattern(world: World, num_smurfs: int = 50) -> list[dict]:
    """
    Generates one full 'Starburst': num_smurfs accounts each send a sub-threshold
    amount ($9,000-$9,900) into a single shell account, staggered in time to look
    unrelated to a rules-based system.
    """
    shell = make_shell_account(world)
    smurfs = make_smurf_accounts(world, num_smurfs)

    transactions = []
    for smurf in smurfs:
        amount = round(random.uniform(9000, 9900), 2)
        transactions.append({
            "transaction_id": f"TXN-{uuid.uuid4().hex[:10].upper()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sender_account": smurf.account_id,
            "sender_person": smurf.owner.person_id,
            "sender_ip": smurf.owner.ip_address,
            "receiver_account": shell.account_id,
            "receiver_person": shell.owner.person_id,
            "receiver_ip": shell.owner.ip_address,
            "amount": amount,
            "sender_bank": smurf.bank.bank_id,
            "receiver_bank": shell.bank.bank_id,
            "is_synthetic_fraud": True,
            "syndicate_id": f"SYN-{uuid.uuid4().hex[:8].upper()}",
        })

    world.accounts.extend(smurfs)
    world.accounts.append(shell)
    return transactions


if __name__ == "__main__":
    world = World()
    starburst = generate_starburst_pattern(world, num_smurfs=50)
    print(f"Generated {len(starburst)} smurfing transactions into shell account "
          f"{starburst[0]['receiver_account']}")
    print(starburst[0])