import json
import time
import random

from kafka import KafkaProducer

from generator import World, make_transaction
from syndicate import generate_starburst_pattern

KAFKA_BROKER = "localhost:9092"
TOPIC = "fingraph.transactions"


def get_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )


def stream_transactions(
    world: World,
    producer: KafkaProducer,
    duration_seconds: int = 60,
    tx_per_second: float = 3.0,
    syndicate_chance: float = 0.02,
):
    """
    Continuously streams transactions to Kafka in real time.
    Every tick there's a small chance a whole syndicate burst fires at once,
    mimicking real fraud rings acting in a short window.
    """
    end_time = time.time() + duration_seconds
    sent = 0

    while time.time() < end_time:
        if random.random() < syndicate_chance:
            burst = generate_starburst_pattern(world, num_smurfs=random.randint(20, 50))
            for tx in burst:
                producer.send(TOPIC, key=tx["transaction_id"], value=tx)
                sent += 1
            print(f"[SYNDICATE BURST] sent {len(burst)} smurfing transactions "
                  f"into shell account {burst[0]['receiver_account']}")
        else:
            tx = make_transaction(world)
            producer.send(TOPIC, key=tx["transaction_id"], value=tx)
            sent += 1

        if sent % 10 == 0:
            producer.flush()
            print(f"sent {sent} transactions so far...")

        time.sleep(1 / tx_per_second)

    producer.flush()
    print(f"Done. Sent {sent} total transactions to topic '{TOPIC}'.")


if __name__ == "__main__":
    world = World()
    producer = get_producer()
    stream_transactions(world, producer, duration_seconds=120)