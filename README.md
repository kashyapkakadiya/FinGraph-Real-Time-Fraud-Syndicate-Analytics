# FinGraph — Real-Time Fraud Syndicate Analytics

A streaming graph-analytics pipeline that detects "smurfing" / money-laundering syndicates in
real time, using Kafka -> PyFlink -> Neo4j.

See [PIPELINE_AUDIT.md](./PIPELINE_AUDIT.md) for the full mid-project review, including the
query-optimization story (188ms -> 4ms).

## Problem
Standard fraud rules (e.g. "flag transactions over $10,000") miss coordinated syndicates where
many unrelated-looking accounts each send small amounts through intermediary accounts to evade
detection ("smurfing" / structuring).

## Architecture
```
Transaction Simulator (Python/Faker)
        |
        v
   Kafka topic: fingraph.transactions
        |
        v
PyFlink (Table API/SQL) -- clean, validate, dedup
        |
        v
Neo4j (real-time MERGE upsert)
        |
        v
Cypher analysis: risk scoring + circular flow detection
```

## Stack
Kafka, Zookeeper, Neo4j (+ constraints/indexes), PyFlink (Table API/SQL), Python, Docker Compose

## Repo layout
```
docker-compose.yml          Kafka, Zookeeper, Neo4j
requirements.txt
simulator/
  entities.py                Person/Account/Bank data model
  generator.py                Baseline + mixed transaction generator
  syndicate.py                 Starburst/smurfing pattern generator
  producer.py                   Kafka producer (real-time streaming)
neo4j/
  schema.cypher                Constraints and indexes
  apply_schema.py
stream_processor/
  flink_consumer.py            PyFlink Table API job: clean, dedup, Neo4j sink
  jars/                        (not committed -- see note below)
queries/
  risk_scoring.cypher                    Baseline (naive) version
  risk_scoring_optimized.cypher           Production version
  circular_flow_detection.cypher          Baseline (naive) version
  circular_flow_detection_optimized.cypher Production version
  seed_circular_test.cypher               Synthetic cycle for testing
  run_queries.py                           Runs optimized queries, chained, with timing
PIPELINE_AUDIT.md            Mid-project review
```

## Setup

**1. Start the infrastructure:**
```bash
docker compose up -d
docker compose ps   # confirm kafka, zookeeper, neo4j are all Up
```

**2. Install Python dependencies:**
```bash
pip install -r requirements.txt
```

**3. Download the Flink Kafka connector JAR** (not committed -- it's a binary):
https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.2.0-1.19/flink-sql-connector-kafka-3.2.0-1.19.jar
Place it in `stream_processor/jars/`.

**4. Apply the Neo4j schema:**
```bash
cd neo4j
python apply_schema.py
```

## Running the pipeline

Open three terminals:

**Terminal 1 — stream processor (start first, it's the consumer):**
```bash
cd stream_processor
python flink_consumer.py
```

**Terminal 2 — transaction simulator (produces to Kafka):**
```bash
cd simulator
python producer.py
```

**Terminal 3 — analysis queries (after some data has flowed):**
```bash
cd queries
python run_queries.py
```

**Neo4j Browser** (visualize the graph): http://localhost:7474 — login `neo4j` / `fingraph123`

Basic view (fast, but always shows the same ~100 edges regardless of what's new --
Neo4j's default scan order returns matches in roughly creation order, and LIMIT 100
with no ORDER BY just takes the first 100 it finds every time):
```cypher
MATCH (shell:Account)<-[t:TRANSFERRED_TO]-(smurf:Account)
WHERE t.is_synthetic_fraud = true
RETURN shell, smurf, t
LIMIT 100
```

Recency-ordered view (shows the newest fraud edges -- use this to demonstrate the
graph is live and updating, not a static snapshot):
```cypher
MATCH (shell:Account)<-[t:TRANSFERRED_TO]-(smurf:Account)
WHERE t.is_synthetic_fraud = true
RETURN shell, smurf, t
ORDER BY t.timestamp DESC
LIMIT 100
```

Live-ness proof (run before and after producer.py, watch the count change):
```cypher
MATCH ()-[t:TRANSFERRED_TO]->() RETURN count(t) AS total_edges;
```

## Note on PyFlink + Windows
PyFlink's DataStream API Python UDFs rely on an Apache Beam subprocess that reliably fails to
boot on Windows. This project uses the Table API/SQL exclusively instead (JVM-only execution) --
see PIPELINE_AUDIT.md for details.

## Progress Log
- Day 1: Environment scaffold (Docker Compose: Kafka, Zookeeper, Neo4j), repo structure
- Day 2: Core data model (Person, Account, Bank) + baseline random transaction generator
- Day 3: Syndicate/smurfing pattern generator -- "Starburst" (N accounts -> 1 shell account),
  mixed into normal traffic
- Day 4: Kafka producer -- simulator streams transactions (incl. syndicate bursts) into
  `fingraph.transactions` topic in real time
- Day 5: Neo4j graph schema -- constraints/indexes for Person, Account, Bank, IPAddress nodes
  and TRANSFERRED_TO edges
- Day 6: PyFlink stream processor (Table API/SQL) -- reads and flags fingraph.transactions from
  Kafka. Switched from DataStream+Python UDF to Table API to work around a known PyFlink-on-
  Windows Beam-harness bug (`Process died with exit code 0`)
- Day 7: Data cleaning/validation -- SQL-based filtering (null accounts, invalid amounts,
  self-transfers) + dedup on transaction_id via ROW_NUMBER()
- Day 8: Real-time Neo4j sink -- Flink's `table_result.collect()` streams cleaned transactions
  to the Python client, which upserts them into Neo4j via MERGE (Person, Account, Bank,
  IPAddress nodes; OWNS, HELD_AT, USED_IP, TRANSFERRED_TO edges)
- Day 9: Cypher analysis queries -- risk_scoring.cypher ranks shell accounts correctly against
  real simulator data; circular_flow_detection.cypher validated against seeded synthetic cycle
  and organically-occurring real cycles
- Day 10: Query optimization -- index-anchored risk scoring + candidate-narrowed circular flow
  detection + warm/server-side timing methodology, bringing both queries from 188-209ms down to
  1-4ms server-side. Mid-project review complete -- see PIPELINE_AUDIT.md
- Day 11: Neo4j GDS setup — verified plugin, projected in-memory graph catalog
  (Account nodes, TRANSFERRED_TO relationships) for Week 3 algorithm work
- Day 12: Weakly Connected Components (GDS) — auto-groups syndicate clusters via
  gds.wcc.write, writing wcc_component_id onto Account nodes. Components combining
  high transaction volume with a high fraud_ratio are algorithmically-discovered
  syndicates, replacing manual per-hub Cypher queries.

## Scope note
This covers Week 1 (Ingestion Setup, Graph Schema) and Week 2 (Stream Processing, Cypher
Queries) of the original project spec. Week 3 (Neo4j GDS algorithms -- Louvain, PageRank) and
Week 4 (automation/alerting) are out of scope for this 10-day sprint.