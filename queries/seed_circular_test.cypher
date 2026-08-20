// Test seed data: a synthetic circular flow (X -> Y -> Z -> X).
// Your simulator doesn't currently generate this pattern (it only produces
// Starburst/smurfing), so run this once to prove circular_flow_detection.cypher
// actually fires correctly. Safe to delete afterward -- see cleanup query below.

MERGE (x:Account {account_id: 'TEST-CYCLE-X'})
MERGE (y:Account {account_id: 'TEST-CYCLE-Y'})
MERGE (z:Account {account_id: 'TEST-CYCLE-Z'})

MERGE (x)-[:TRANSFERRED_TO {
    transaction_id: 'TEST-TXN-XY', amount: 5000.0,
    timestamp: '2026-08-20T00:00:00Z', is_synthetic_fraud: true
}]->(y)

MERGE (y)-[:TRANSFERRED_TO {
    transaction_id: 'TEST-TXN-YZ', amount: 4950.0,
    timestamp: '2026-08-20T00:05:00Z', is_synthetic_fraud: true
}]->(z)

MERGE (z)-[:TRANSFERRED_TO {
    transaction_id: 'TEST-TXN-ZX', amount: 4900.0,
    timestamp: '2026-08-20T00:10:00Z', is_synthetic_fraud: true
}]->(x);

// --- Cleanup (run separately, after you've confirmed the query works) ---
// MATCH (n:Account) WHERE n.account_id STARTS WITH 'TEST-CYCLE-'
// DETACH DELETE n;
