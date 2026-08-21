import time, json
from kafka import KafkaProducer
from neo4j import GraphDatabase

producer = KafkaProducer(bootstrap_servers="localhost:9092",
                          value_serializer=lambda v: json.dumps(v).encode())
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "fingraph123"))

txn_id = "LATENCY-TEST-001"
tx = {"transaction_id": txn_id, "timestamp": "2026-08-21T00:00:00Z",
      "sender_account": "ACC-LATTEST-A", "sender_person": "P-A", "sender_ip": "1.1.1.1",
      "receiver_account": "ACC-LATTEST-B", "receiver_person": "P-B", "receiver_ip": "2.2.2.2",
      "amount": 100.0, "sender_bank": "BANK-A", "receiver_bank": "BANK-B",
      "is_synthetic_fraud": False, "syndicate_id": None}

send_time = time.time()
producer.send("fingraph.transactions", value=tx)
producer.flush()

with driver.session() as session:
    while True:
        result = session.run(
            "MATCH ()-[t:TRANSFERRED_TO {transaction_id: $id}]->() RETURN t",
            id=txn_id)
        if result.single():
            print(f"Edge appeared after {time.time() - send_time:.3f} seconds")
            break
        time.sleep(0.05)