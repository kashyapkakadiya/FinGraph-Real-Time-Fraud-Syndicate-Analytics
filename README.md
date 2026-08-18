# FinGraph — Real-Time Fraud Syndicate Analytics

A streaming graph-analytics pipeline that detects "smurfing" / money-laundering
syndicates in real time, using Kafka → (Flink/stream processor) → Neo4j.

## Problem
Standard fraud rules (e.g. "flag transactions over $10,000") miss coordinated
syndicates where many unrelated-looking accounts each send small amounts
through intermediary accounts to evade detection.

## Architecture
Transaction Simulator → Kafka → Stream Processor → Neo4j (Graph DB) → Cypher analysis

## Stack
Kafka, Neo4j, Python, (PyFlink)

## Progress Log
- Day 1: Environment scaffold (Docker Compose: Kafka, Zookeeper, Neo4j), repo structure
- Day 2: Core data model (Person, Account, Bank) + baseline random transaction generator
- Day 3: Syndicate/smurfing pattern generator — "Starburst" (N accounts -> 1 shell account), mixed into normal traffic
- Day 4: Kafka producer — simulator streams transactions (incl. syndicate bursts) into `fingraph.transactions` topic in real time
- Day 5: Neo4j graph schema — constraints/indexes for Person, Account, Bank, IPAddress nodes and TRANSFERRED_TO edges
- Day 6: PyFlink stream processor (Table API/SQL) — reads fingraph.transactions from Kafka, live-parses JSON, flags fraud. Note: switched from DataStream+Python UDF to Table API to work around a known PyFlink-on-Windows Beam-harness bug.
> Note: `stream_processor/jars/flink-sql-connector-kafka-3.2.0-1.19.jar` is not committed (binary,
> a few MB). Download it manually before running Day 6+ scripts:
> https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.2.0-1.19/flink-sql-connector-kafka-3.2.0-1.19.jar
> Place it in `stream_processor/jars/`.
- Day 7: Data cleaning/validation — SQL-based filtering (null accounts, invalid amounts, self-transfers) + dedup on transaction_id via ROW_NUMBER()