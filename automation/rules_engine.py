import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "fingraph123")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
ALERT_LOG_PATH = "alerts.log"

POLL_INTERVAL_SECONDS = 15
FAN_IN_THRESHOLD = 20
PAGERANK_THRESHOLD = 5.0
ALERT_COOLDOWN_MINUTES = 60

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

RECENT_ALERT_CHECK = """
MATCH (a:Account {account_id: $account_id})-[:HAS_ALERT]->(alert:Alert)
WHERE alert.created_at > datetime() - duration({minutes: $cooldown_minutes})
RETURN count(alert) AS recent_alert_count
"""

CREATE_ALERT = """
MATCH (a:Account {account_id: $account_id})
CREATE (alert:Alert {
    alert_id: randomUUID(),
    reason: $reason,
    fan_in: $fan_in,
    pagerank_weighted: $pagerank_weighted,
    created_at: datetime()
})
CREATE (a)-[:HAS_ALERT]->(alert)
RETURN alert.alert_id AS alert_id
"""


def format_reason(account: dict) -> str:
    reasons = []
    if account["fan_in"] and account["fan_in"] >= FAN_IN_THRESHOLD:
        reasons.append(f"fan_in={account['fan_in']} (>= {FAN_IN_THRESHOLD})")
    if account["pagerank_weighted"] and account["pagerank_weighted"] >= PAGERANK_THRESHOLD:
        reasons.append(f"pagerank={account['pagerank_weighted']:.2f} (>= {PAGERANK_THRESHOLD})")
    return " and ".join(reasons)


def send_alert(message: str):
    if SLACK_WEBHOOK_URL:
        try:
            resp = requests.post(SLACK_WEBHOOK_URL, json={"text": message}, timeout=5)
            resp.raise_for_status()
            print(f"[sent to Slack] {message}")
            return
        except requests.RequestException as e:
            print(f"[Slack send failed, falling back to log] {e}")

    print(f"[ALERT - no Slack configured] {message}")
    with open(ALERT_LOG_PATH, "a") as f:
        f.write(message + "\n")


def already_alerted_recently(session, account_id: str) -> bool:
    result = session.run(
        RECENT_ALERT_CHECK, account_id=account_id, cooldown_minutes=ALERT_COOLDOWN_MINUTES
    )
    return result.single()["recent_alert_count"] > 0


def record_alert(session, account: dict, reason: str):
    session.run(
        CREATE_ALERT,
        account_id=account["account_id"],
        reason=reason,
        fan_in=account["fan_in"],
        pagerank_weighted=account["pagerank_weighted"],
    )


def poll_once(session) -> int:
    result = session.run(
        RISK_QUERY,
        fan_in_threshold=FAN_IN_THRESHOLD,
        pagerank_threshold=PAGERANK_THRESHOLD,
    )
    accounts = [dict(r) for r in result]

    new_alerts = 0
    for account in accounts:
        if already_alerted_recently(session, account["account_id"]):
            continue

        reason = format_reason(account)
        message = (f"🚨 FinGraph risk alert: {account['account_id']} exceeded threshold "
                   f"({reason}) at {datetime.now(timezone.utc).isoformat()}")
        send_alert(message)
        record_alert(session, account, reason)
        new_alerts += 1

    print(f"Poll complete: {len(accounts)} accounts over threshold, "
          f"{new_alerts} new alert(s) fired (cooldown: {ALERT_COOLDOWN_MINUTES}min).")
    return new_alerts


def main():
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        print(f"Rules engine started. Polling every {POLL_INTERVAL_SECONDS}s. "
              f"Slack: {'configured' if SLACK_WEBHOOK_URL else 'NOT configured (using log fallback)'}")
        with driver.session() as session:
            while True:
                poll_once(session)
                time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()