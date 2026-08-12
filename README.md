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