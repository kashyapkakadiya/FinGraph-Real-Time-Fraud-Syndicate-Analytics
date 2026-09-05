# FinGraph — Real-Time Fraud Syndicate Analytics

A streaming graph-analytics pipeline that detects "smurfing" / money-laundering syndicates in
real time, using Kafka -> PyFlink -> Neo4j, extended with GDS algorithms, a live dashboard,
and automated alerting.

See [PIPELINE_AUDIT.md](./PIPELINE_AUDIT.md) for the Week 1-2 review (query-optimization
story: 188ms -> 4ms) and [WEEK3_4_AUDIT.md](./WEEK3_4_AUDIT.md) for Weeks 3-4 (GDS algorithms,
dashboard, automation).

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
Neo4j (real-time MERGE upsert) -- GDS: WCC, Louvain, PageRank
        |
        v
FastAPI backend  --->  React dashboard (live graph, risk table, alerts)
        |
        v
Automation rules engine -- Slack/log alerts on threshold breach
```

## Stack
Kafka, Zookeeper, Neo4j (+ GDS, constraints/indexes), PyFlink (Table API/SQL), Python,
FastAPI, React (Vite, react-force-graph-2d), Docker Compose

## Repo layout
```
docker-compose.yml          Kafka, Zookeeper, Neo4j (+ GDS plugin)
requirements.txt
simulator/
  entities.py                Person/Account/Bank data model
  generator.py                 Baseline + mixed transaction generator
  syndicate.py                   Starburst/smurfing pattern generator
  producer.py                      Kafka producer (real-time streaming)
neo4j/
  schema.cypher                Constraints and indexes
  apply_schema.py
stream_processor/
  flink_consumer.py            PyFlink Table API job: clean, dedup, Neo4j sink
  jars/                        (not committed -- see Setup)
queries/
  risk_scoring.cypher                      Baseline (naive) version
  risk_scoring_optimized.cypher             Production version
  circular_flow_detection.cypher            Baseline (naive) version
  circular_flow_detection_optimized.cypher   Production version
  seed_circular_test.cypher                  Synthetic cycle for testing
  run_queries.py                              Runs optimized queries, chained, with timing
gds/
  setup_gds.py                GDS plugin verification + graph projection
  wcc.py                        Weakly Connected Components
  louvain.py                     Louvain community detection
  pagerank.py                     PageRank centrality (unweighted + amount-weighted)
backend/
  main.py                     FastAPI: /api/stats, /api/risk-scores, /api/graph,
                                /api/account/{id}, /api/account/{id}/edges
dashboard/
  src/App.jsx                 React dashboard: live graph, risk table, interactivity
automation/
  rules_engine.py             Polls risk scores, fires Slack/log alerts, durable dedup
  test_rules_engine.py         Integration test for alert cooldown logic
PIPELINE_AUDIT.md            Week 1-2 review (ingestion, schema, streaming, query optimization)
WEEK3_4_AUDIT.md             Week 3-4 review (GDS, dashboard, automation)
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

**5. Install the dashboard's frontend dependencies:**
```bash
cd dashboard
npm install
```

## Running the full pipeline

Open five terminals:

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

**Terminal 3 — GDS algorithms (after some data has flowed):**
```bash
cd gds
python setup_gds.py   # re-run any time data has changed, to refresh the projection
python wcc.py
python louvain.py
python pagerank.py
```

**Terminal 4 — backend API:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```
Interactive docs: http://localhost:8000/docs

**Terminal 5 — dashboard:**
```bash
cd dashboard
npm run dev
```
Open http://localhost:5173 — click any node to trace its connections, use the fan-in
slider to filter the risk table, and use "Reset view" to return to the initial graph.

**Automation (optional, separate terminal):**
```bash
cd automation
python rules_engine.py
```
Set `SLACK_WEBHOOK_URL` in a `.env` file for real Slack alerts; otherwise alerts log to
console and `automation/alerts.log`.

## Neo4j Browser queries

Open http://localhost:7474 — login `neo4j` / `fingraph123`.

Basic fraud-edge view (fast, but always shows the same ~100 edges regardless of what's
new -- Neo4j's default scan order is roughly creation order, and `LIMIT 100` with no
`ORDER BY` just takes the first 100 it finds every time):
```cypher
MATCH (shell:Account)<-[t:TRANSFERRED_TO]-(smurf:Account)
WHERE t.is_synthetic_fraud = true
RETURN shell, smurf, t
LIMIT 100
```

Recency-ordered view (shows the newest fraud edges -- use this to demonstrate the graph
is live and updating, not a static snapshot):
```cypher
MATCH (shell:Account)<-[t:TRANSFERRED_TO]-(smurf:Account)
WHERE t.is_synthetic_fraud = true
RETURN shell, smurf, t
ORDER BY t.timestamp DESC
LIMIT 100
```

Live-ness proof (run before and after `producer.py`, watch the count change):
```cypher
MATCH ()-[t:TRANSFERRED_TO]->() RETURN count(t) AS total_edges;
```

Alert audit trail (Week 4):
```cypher
MATCH (a:Account)-[:HAS_ALERT]->(alert:Alert)
RETURN a.account_id, alert.reason, alert.created_at
ORDER BY alert.created_at DESC
```

## Notes on real engineering problems solved along the way

- **PyFlink + Windows**: the DataStream API's Python UDFs rely on an Apache Beam subprocess
  that reliably fails to boot on Windows (`Process died with exit code 0`). Worked around by
  using the Table API/SQL exclusively (JVM-only execution) -- see PIPELINE_AUDIT.md.
- **Query performance**: naive Cypher queries measured 188-209ms against the 100ms target.
  Root-caused via `PROFILE` to full-graph scans, fixed by anchoring on an index and narrowing
  the search space, then further fixed a flawed *benchmark* (cold query-plan compilation was
  being counted as steady-state performance) -- final result: 1-4ms server-side. Full story in
  PIPELINE_AUDIT.md.
- **API cartesian-product bug**: `/api/stats` inflated transaction_count by ~2,846x due to two
  unrelated `MATCH` clauses multiplying instead of adding. Fixed with `CALL {}` subqueries.
- **WCC over-merging / Louvain partial success**: root-caused to the simulator's account reuse
  creating cross-syndicate bridges -- a real, explainable AML-adjacent finding, not just an
  imperfect result. Full story in WEEK3_4_AUDIT.md.

## Progress Log
- Day 1: Environment scaffold (Docker Compose: Kafka, Zookeeper, Neo4j), repo structure
- Day 2: Core data model (Person, Account, Bank) + baseline random transaction generator
- Day 3: Syndicate/smurfing pattern generator -- "Starburst" (N accounts -> 1 shell account),
  mixed into normal traffic
- Day 4: Kafka producer -- simulator streams transactions (incl. syndicate bursts) into
  `fingraph.transactions` topic in real time
- Day 5: Neo4j graph schema -- constraints/indexes for Person, Account, Bank, IPAddress nodes
  and TRANSFERRED_TO edges
- Day 6: PyFlink stream processor (Table API/SQL) -- switched from DataStream+Python UDF to
  work around a known PyFlink-on-Windows Beam-harness bug
- Day 7: Data cleaning/validation -- SQL-based filtering + dedup on transaction_id
- Day 8: Real-time Neo4j sink -- Flink's `table_result.collect()` streams cleaned
  transactions to the Python client, which upserts them into Neo4j via MERGE
- Day 9: Cypher analysis queries -- risk scoring, circular flow detection
- Day 10: Query optimization -- 188-209ms down to 1-4ms server-side (index anchoring,
  candidate narrowing, corrected benchmark methodology). Mid-project review complete
- Day 11: Neo4j GDS setup -- verified plugin, projected in-memory graph catalog
- Day 12: Weakly Connected Components -- auto-grouped clusters; found "giant component"
  limitation motivating Louvain
- Day 13: Louvain community detection -- partial separation success, root-caused remaining
  mixing to simulator account reuse
- Day 14: PageRank centrality -- top accounts independently matched Day 9's circular-flow
  cycle, cross-algorithm validation
- Day 15: FastAPI backend -- found and fixed a cartesian-product bug in /api/stats
- Day 16: React dashboard scaffold -- live graph, stats, risk table, confirmed rendering
- Day 17: Dashboard interactivity -- click-to-expand money trail, account detail panel,
  risk filter, responsive canvas
- Day 18: Automation rules engine -- Slack/log alerts on threshold breach
- Day 19: Durable alert dedup -- Neo4j-backed cooldown window, integration test
- Day 20: Dashboard visualizes Louvain community (node color) + PageRank (node size),
  legend, reset-view button. Final Week 3-4 review complete.

## Scope note
This is a complete implementation of all four weeks of the original Infotact Solutions
project spec: Week 1 (Ingestion Setup, Graph Schema), Week 2 (Stream Processing, Cypher
Queries), Week 3 (Graph Data Science, Dashboard UI), and Week 4 (Automation, Refine &
Polish) -- delivered as 20 days / 20 commits.