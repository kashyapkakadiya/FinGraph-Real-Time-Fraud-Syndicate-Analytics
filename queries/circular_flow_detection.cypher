// Circular Flow Detection
// Finds money laundering cycles: A -> B -> C -> ... -> A
// Hop range 3..5 requires a genuine multi-account cycle, not just two accounts
// bouncing money back and forth (which would be a 2-hop "cycle" and isn't
// the laundering pattern we care about).

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
