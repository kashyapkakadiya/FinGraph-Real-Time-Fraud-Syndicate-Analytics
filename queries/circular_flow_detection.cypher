// BASELINE VERSION -- kept intentionally for comparison.
// See circular_flow_detection_optimized.cypher for the production version and
// PIPELINE_AUDIT.md for the full before/after performance analysis
// (this version: ~209ms; optimized version: ~1ms server-side).

MATCH path = (a:Account)-[:TRANSFERRED_TO*3..5]->(a)
WITH path,
     [n IN nodes(path) | n.account_id] AS account_chain,
     [r IN relationships(path) | r.amount] AS amounts,
     length(path) AS hops
RETURN account_chain,
       hops,
       amounts,
       reduce(total = 0.0, amt IN amounts | total + amt) AS total_cycled_amount
ORDER BY hops ASC
LIMIT 25;
