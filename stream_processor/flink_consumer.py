import os

from pyflink.table import EnvironmentSettings, TableEnvironment
from neo4j import GraphDatabase

KAFKA_BROKER = "localhost:9092"
TOPIC = "fingraph.transactions"
GROUP_ID = "fingraph-flink-processor"

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "fingraph123")

JAR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jars",
                         "flink-sql-connector-kafka-3.2.0-1.19.jar")

# Column order MUST match the final SELECT below -- we zip these together
# per row since PyFlink Row objects behave like tuples.
COLUMNS = [
    "transaction_id", "timestamp", "sender_account", "sender_person", "sender_ip",
    "receiver_account", "receiver_person", "receiver_ip", "amount",
    "sender_bank", "receiver_bank", "is_synthetic_fraud", "syndicate_id",
]

# Upserts the full sub-graph for one transaction: both people, both accounts,
# both banks, both IPs, and the TRANSFERRED_TO edge itself. MERGE means
# "create if missing, otherwise match" -- so re-running this is always safe
# and never creates duplicate nodes.
UPSERT_CYPHER = """
MERGE (sp:Person {person_id: $sender_person})
MERGE (rp:Person {person_id: $receiver_person})
MERGE (sip:IPAddress {address: $sender_ip})
MERGE (rip:IPAddress {address: $receiver_ip})
MERGE (sp)-[:USED_IP]->(sip)
MERGE (rp)-[:USED_IP]->(rip)
MERGE (sb:Bank {bank_id: $sender_bank})
MERGE (rb:Bank {bank_id: $receiver_bank})
MERGE (sa:Account {account_id: $sender_account})
MERGE (sa)-[:HELD_AT]->(sb)
MERGE (sp)-[:OWNS]->(sa)
MERGE (ra:Account {account_id: $receiver_account})
MERGE (ra)-[:HELD_AT]->(rb)
MERGE (rp)-[:OWNS]->(ra)
MERGE (sa)-[t:TRANSFERRED_TO {transaction_id: $transaction_id}]->(ra)
SET t.amount = $amount,
    t.timestamp = $timestamp,
    t.is_synthetic_fraud = $is_synthetic_fraud,
    t.syndicate_id = $syndicate_id
"""


def main():
    settings = EnvironmentSettings.in_streaming_mode()
    t_env = TableEnvironment.create(settings)
    t_env.get_config().set("pipeline.jars", f"file:///{JAR_PATH}")

    t_env.execute_sql(f"""
        CREATE TABLE transactions_raw (
            transaction_id      STRING,
            `timestamp`         STRING,
            sender_account       STRING,
            sender_person        STRING,
            sender_ip            STRING,
            receiver_account     STRING,
            receiver_person      STRING,
            receiver_ip          STRING,
            amount                DOUBLE,
            sender_bank           STRING,
            receiver_bank         STRING,
            is_synthetic_fraud    BOOLEAN,
            syndicate_id          STRING
        ) WITH (
            'connector' = 'kafka',
            'topic' = '{TOPIC}',
            'properties.bootstrap.servers' = '{KAFKA_BROKER}',
            'properties.group.id' = '{GROUP_ID}',
            'scan.startup.mode' = 'earliest-offset',
            'format' = 'json',
            'json.ignore-parse-errors' = 'true'
        )
    """)

    # Same cleaning/dedup logic from Day 7.
    t_env.create_temporary_view("transactions_clean", t_env.sql_query("""
        SELECT * FROM (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY transaction_id ORDER BY `timestamp`
                   ) AS row_num
            FROM transactions_raw
            WHERE transaction_id IS NOT NULL
              AND sender_account IS NOT NULL
              AND receiver_account IS NOT NULL
              AND sender_account <> receiver_account
              AND amount > 0 AND amount < 1000000
        ) WHERE row_num = 1
    """))

    final_table = t_env.sql_query(f"""
        SELECT {', '.join(f'`{c}`' if c == 'timestamp' else c for c in COLUMNS)}
        FROM transactions_clean
    """)

    table_result = final_table.execute()

    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    written = 0

    print("Listening for cleaned transactions and upserting into Neo4j... (Ctrl+C to stop)")
    try:
        with driver.session() as session, table_result.collect() as results:
            for row in results:
                params = dict(zip(COLUMNS, row))
                session.run(UPSERT_CYPHER, params)
                written += 1
                if written % 10 == 0:
                    print(f"upserted {written} transactions into Neo4j...")
    finally:
        driver.close()
        print(f"Done. Upserted {written} transactions into Neo4j.")


if __name__ == "__main__":
    main()