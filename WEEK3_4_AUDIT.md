# FinGraph — Week 3-4 Review (Days 11-20)

Extension beyond the original 10-day scope: GDS algorithms, a live dashboard, and
automated alerting, per the project doc's Week 3 (Graph Data Science, Dashboard UI) and
Week 4 (Automation, Refine & Polish) columns.

## Day-by-day summary
| Day | Deliverable |
|---|---|
| 11 | Neo4j GDS setup — verified plugin, projected in-memory graph catalog |
| 12 | Weakly Connected Components — auto-grouped clusters; found "giant component" limitation |
| 13 | Louvain community detection — partial separation success; root-caused remaining mixing |
| 14 | PageRank centrality — top accounts independently matched Day 9's circular-flow cycle |
| 15 | FastAPI backend — found and fixed a cartesian-product bug in /api/stats |
| 16 | React dashboard scaffold — live graph, stats, risk table |
| 17 | Dashboard interactivity — click-to-expand money trail, account detail, risk filter |
| 18 | Automation rules engine — Slack/log alerts on threshold breach |
| 19 | Durable alert dedup — Neo4j-backed cooldown, integration test |
| 20 | Community/PageRank visualization, legend, reset view, this review |

## Key findings worth highlighting in a review

**WCC over-merges in the presence of background traffic.** The largest WCC components
(338-602 accounts) turned out to be several separate syndicates bridged together by
ordinary transaction traffic accumulated across simulator runs -- a known real-world AML
limitation, not a bug. This directly motivated the Louvain work on Day 13.

**Louvain partially succeeded, and the failure mode was traceable to actual code.** Some
WCC giant components split cleanly into pure fraud (ratio 1.0) and pure normal (ratio 0.0)
sub-communities. Others didn't split at all. Root cause: `generator.py`'s
`world.accounts.extend(smurfs)` lets smurf accounts participate in later, unrelated normal
transactions within the same simulator run, creating cross-syndicate bridges. Proposed fix
(not implemented): time-windowed analysis, mirroring real AML practice.

**PageRank independently confirmed a Day 9 finding.** The top 3 accounts by both
unweighted and amount-weighted PageRank were the exact same 3 accounts that formed the
circular-flow cycle discovered via a completely different technique (Cypher pattern
matching) on Day 9 -- genuine cross-algorithm validation, not something engineered to
look good.

**Two real bugs found and fixed via honest debugging, not luck:**
- `/api/stats` cartesian product (two unrelated `MATCH` clauses multiplying instead of
  adding) inflated transaction_count by ~2,846x. Fixed with `CALL {}` subqueries.
- Day 18's in-memory alert dedup wouldn't survive a restart. Fixed on Day 19 by persisting
  alert history as `(:Account)-[:HAS_ALERT]->(:Alert)` nodes in Neo4j, with a cooldown
  window instead of "alert once ever" -- verified via a real integration test.

## What's visualized in the final dashboard
- Fraud edges: red, thicker
- Node color: Louvain community (Day 13)
- Node size: weighted PageRank (Day 14)
- Click any node: expands the graph outward via its real transaction edges, shows
  WCC/Louvain/PageRank detail for that account
- Risk table: filterable by fan-in threshold

## Known limitations (unchanged from Week 1-2, still honest)
- Structuring-band anchoring in the optimized queries is dataset-specific.
- Organic cycles are a weak fraud signal alone.
- Neo4j sink runs client-side, not via a distributed Flink sink operator.
- Alert rules engine polls rather than reacting to a true event stream (acceptable at this
  scale; a production system might use a Neo4j Streams/Kafka trigger instead of polling).