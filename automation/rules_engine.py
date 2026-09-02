import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "fingraph123")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")  # unset -> console/file fallback
ALERT_LOG_PATH = "alerts.log"

POLL_INTERVAL_SECONDS = 15
FAN_IN_THRESHOLD = 20          # matches "several sub-threshold senders" pattern
PAGERANK_THRESHOLD = 5.0       # matches Day 14's centrality signal

RISK_QUERY = """
MATCH (receiver:Account)
OPTIONAL MATCH (sender:Account)-[t:TRANSFERRED_TO]->(receiver)
WHERE t.amount >= 9000 AND t.amount < 10000
WITH receiver,
     count(DISTINCT sender) AS fan_in,
     receiver.pagerank_weighted AS pagerank_weighted
WHERE fan_in >= $fan_in_threshold OR pagerank_weighted >= $pagerank_threshold
RETURN receiver.account_id AS account_id, fan_in, pagerank_weighted
ORDER BY fan_in DESC
"""


def format_alert(account: dict) -> str:
    reasons = []
    if account["fan_in"] and account["fan_in"] >= FAN_IN_THRESHOLD:
        reasons.append(f"fan_in={account['fan_in']} (>= {FAN_IN_THRESHOLD})")
    if account["pagerank_weighted"] and account["pagerank_weighted"] >= PAGERANK_THRESHOLD:
        reasons.append(f"pagerank={account['pagerank_weighted']:.2f} (>= {PAGERANK_THRESHOLD})")
    reason_str = " and ".join(reasons)
    return (f"🚨 FinGraph risk alert: {account['account_id']} exceeded threshold "
            f"({reason_str}) at {datetime.now(timezone.utc).isoformat()}")


def send_alert(message: str):
    if SLACK_WEBHOOK_URL:
        try:
            resp = requests.post(SLACK_WEBHOOK_URL, json={"text": message}, timeout=5)
            resp.raise_for_status()
            print(f"[sent to Slack] {message}")
            return
        except requests.RequestException as e:
            print(f"[Slack send failed, falling back to log] {e}")

    # Fallback: console + append to a local log file, so this is fully
    # demoable without any external service configured.
    print(f"[ALERT - no Slack configured] {message}")
    with open(ALERT_LOG_PATH, "a") as f:
        f.write(message + "\n")


def poll_once(session, already_alerted: set):
    result = session.run(
        RISK_QUERY,
        fan_in_threshold=FAN_IN_THRESHOLD,
        pagerank_threshold=PAGERANK_THRESHOLD,
    )
    accounts = [dict(r) for r in result]

    new_alerts = 0
    for account in accounts:
        if account["account_id"] in already_alerted:
            continue
        send_alert(format_alert(account))
        already_alerted.add(account["account_id"])
        new_alerts += 1

    print(f"Poll complete: {len(accounts)} accounts over threshold, "
          f"{new_alerts} new alert(s) fired.")


def main():
    already_alerted = set()
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        print(f"Rules engine started. Polling every {POLL_INTERVAL_SECONDS}s. "
              f"Slack: {'configured' if SLACK_WEBHOOK_URL else 'NOT configured (using log fallback)'}")
        with driver.session() as session:
            while True:
                poll_once(session, already_alerted)
                time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()