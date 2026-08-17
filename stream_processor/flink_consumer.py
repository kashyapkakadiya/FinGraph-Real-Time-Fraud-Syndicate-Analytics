import os

from pyflink.table import EnvironmentSettings, TableEnvironment

KAFKA_BROKER = "localhost:9092"
TOPIC = "fingraph.transactions"
GROUP_ID = "fingraph-flink-processor"

JAR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jars",
                         "flink-sql-connector-kafka-3.2.0-1.19.jar")


def main():
    settings = EnvironmentSettings.in_streaming_mode()
    t_env = TableEnvironment.create(settings)
    t_env.get_config().set("pipeline.jars", f"file:///{JAR_PATH}")

    # Define the Kafka topic as a SQL table. The JSON format maps fields by
    # name automatically; any missing field (e.g. syndicate_id on a normal
    # transaction) just comes through as NULL.
    t_env.execute_sql(f"""
        CREATE TABLE transactions (
            transaction_id     STRING,
            `timestamp`        STRING,
            sender_account      STRING,
            sender_person       STRING,
            sender_ip           STRING,
            receiver_account    STRING,
            receiver_person     STRING,
            receiver_ip         STRING,
            amount               DOUBLE,
            sender_bank          STRING,
            receiver_bank        STRING,
            is_synthetic_fraud   BOOLEAN,
            syndicate_id         STRING
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

    # Pure SQL transformation — no Python UDF, so no Beam harness subprocess.
    result_table = t_env.sql_query("""
        SELECT
            transaction_id,
            sender_account,
            receiver_account,
            amount,
            CASE WHEN is_synthetic_fraud THEN 'FRAUD' ELSE 'normal' END AS flag
        FROM transactions
    """)

    # .execute().print() streams results to the console as they arrive.
    result_table.execute().print()


if __name__ == "__main__":
    main()