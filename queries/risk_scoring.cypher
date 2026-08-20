// Node Risk Scoring
// Scores each Account on how "Starburst-shell-like" it looks:
//   fan_in            -- how many DISTINCT accounts send it money (a real customer
//                         gets paid by a handful of people; a shell collects from dozens)
//   structuring_ratio  -- what fraction of its incoming transactions land in the
//                         $9,000-$9,999.99 band, just under the $10k reporting threshold
//   risk_score         -- fan_in weighted by structuring_ratio, so an account only
//                         scores high if BOTH signals are present together

MATCH (sender:Account)-[t:TRANSFERRED_TO]->(receiver:Account)
WITH receiver,
     count(DISTINCT sender)                                              AS fan_in,
     count(t)                                                            AS txn_count,
     sum(t.amount)                                                       AS total_received,
     avg(t.amount)                                                       AS avg_amount,
     sum(CASE WHEN t.amount >= 9000 AND t.amount < 10000 THEN 1 ELSE 0 END) AS structuring_count
WITH receiver, fan_in, txn_count, total_received, avg_amount, structuring_count,
     1.0 * structuring_count / txn_count AS structuring_ratio
RETURN receiver.account_id           AS account_id,
       fan_in,
       txn_count,
       round(total_received, 2)      AS total_received,
       round(avg_amount, 2)          AS avg_amount,
       structuring_count,
       round(structuring_ratio, 2)   AS structuring_ratio,
       round(fan_in * structuring_ratio, 2) AS risk_score
ORDER BY risk_score DESC
LIMIT 25;
