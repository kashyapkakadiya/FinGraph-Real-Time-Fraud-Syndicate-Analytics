MATCH (a:Account)
WHERE a.account_id IN $candidate_ids
MATCH path = (a)-[:TRANSFERRED_TO*3..5]->(a)
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
