from neo4j import GraphDatabase

from rules_engine import (
    already_alerted_recently,
    record_alert,
    FAN_IN_THRESHOLD,
    PAGERANK_THRESHOLD,
)

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "fingraph123")

TEST_ACCOUNT_ID = "TEST-RULES-ENGINE-001"


def setup_test_account(session):
    session.run("""
        MERGE (a:Account {account_id: $account_id})
        SET a.pagerank_weighted = $pagerank_weighted
    """, account_id=TEST_ACCOUNT_ID, pagerank_weighted=PAGERANK_THRESHOLD + 1)


def cleanup_test_account(session):
    session.run("""
        MATCH (a:Account {account_id: $account_id})
        OPTIONAL MATCH (a)-[:HAS_ALERT]->(alert:Alert)
        DETACH DELETE a, alert
    """, account_id=TEST_ACCOUNT_ID)


def run_test():
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        with driver.session() as session:
            cleanup_test_account(session)
            setup_test_account(session)

            test_account = {
                "account_id": TEST_ACCOUNT_ID,
                "fan_in": FAN_IN_THRESHOLD + 5,
                "pagerank_weighted": PAGERANK_THRESHOLD + 1,
            }

            assert not already_alerted_recently(session, TEST_ACCOUNT_ID), \
                "FAIL: test account should have no alert history before first alert"
            print("PASS: fresh account has no recent alert")

            record_alert(session, test_account, "test threshold breach")

            assert already_alerted_recently(session, TEST_ACCOUNT_ID), \
                "FAIL: account should be in cooldown immediately after an alert"
            print("PASS: account correctly in cooldown after first alert")

            print("PASS: durable dedup verified -- a second poll right now would NOT re-alert")

            cleanup_test_account(session)
            print("Cleanup complete.")

    print("\nAll tests passed.")


if __name__ == "__main__":
    run_test()