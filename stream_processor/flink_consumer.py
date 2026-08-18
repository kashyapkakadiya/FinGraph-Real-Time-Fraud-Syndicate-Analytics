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

    clean_table = t_env.sql_query("""
        SELECT *
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY transaction_id
                       ORDER BY `timestamp`
                   ) AS row_num
            FROM transactions_raw
            WHERE transaction_id IS NOT NULL
              AND sender_account IS NOT NULL
              AND receiver_account IS NOT NULL
              AND sender_account <> receiver_account
              AND amount > 0
              AND amount < 1000000
        )
        WHERE row_num = 1
    """)

    t_env.create_temporary_view("transactions_clean", clean_table)

    result = t_env.sql_query("""
        SELECT
            transaction_id,
            sender_account,
            receiver_account,
            amount,
            CASE WHEN is_synthetic_fraud THEN 'FRAUD' ELSE 'normal' END AS flag
        FROM transactions_clean
    """)
    result.execute().print()


if __name__ == "__main__":
    main()