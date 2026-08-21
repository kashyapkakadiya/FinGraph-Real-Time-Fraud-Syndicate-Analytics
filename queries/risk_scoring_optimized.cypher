MATCH (sender:Account)-[t:TRANSFERRED_TO]->(receiver:Account)
WHERE t.amount >= 9000 AND t.amount < 10000
WITH receiver,
     collect(DISTINCT sender) AS structuring_senders,
     count(t)                 AS structuring_count,
     sum(t.amount)            AS structuring_total,
     avg(t.amount)            AS structuring_avg
WITH receiver,
     size(structuring_senders) AS fan_in,
     structuring_count, structuring_total, structuring_avg
WHERE fan_in >= 3   // cheap early filter: a couple of coincidental $9k txns isn't a pattern
RETURN receiver.account_id      AS account_id,
       fan_in,
       structuring_count,
       round(structuring_total, 2) AS total_received,
       round(structuring_avg, 2)   AS avg_amount,
       fan_in                      AS risk_score
ORDER BY risk_score DESC
LIMIT 25;
