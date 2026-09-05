from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "fingraph123")

app = FastAPI(title="FinGraph API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

driver = GraphDatabase.driver(URI, auth=AUTH)


@app.on_event("shutdown")
def shutdown():
    driver.close()


@app.get("/api/stats")
def get_stats():
    with driver.session() as session:
        result = session.run("""
            CALL {
                MATCH (a:Account) RETURN count(a) AS account_count
            }
            CALL {
                MATCH ()-[t:TRANSFERRED_TO]->()
                RETURN count(t) AS transaction_count,
                       sum(CASE WHEN t.is_synthetic_fraud THEN 1 ELSE 0 END) AS fraud_count
            }
            RETURN account_count, transaction_count, fraud_count
        """)
        record = result.single()
        return {
            "account_count": record["account_count"],
            "transaction_count": record["transaction_count"],
            "fraud_count": record["fraud_count"],
        }


@app.get("/api/risk-scores")
def get_risk_scores(limit: int = 25):
    with driver.session() as session:
        result = session.run("""
            MATCH (receiver:Account)
            OPTIONAL MATCH (sender:Account)-[t:TRANSFERRED_TO]->(receiver)
            WHERE t.amount >= 9000 AND t.amount < 10000
            WITH receiver,
                 count(DISTINCT sender) AS fan_in,
                 receiver.wcc_component_id AS wcc_component,
                 receiver.louvain_community_id AS louvain_community,
                 receiver.pagerank_weighted AS pagerank_weighted
            WHERE fan_in >= 3
            RETURN receiver.account_id AS account_id,
                   fan_in,
                   wcc_component,
                   louvain_community,
                   round(pagerank_weighted, 4) AS pagerank_weighted
            ORDER BY pagerank_weighted DESC
            LIMIT $limit
        """, limit=limit)
        return [dict(r) for r in result]


@app.get("/api/graph")
def get_graph(limit: int = 150):
    with driver.session() as session:
        result = session.run("""
            MATCH (sender:Account)-[t:TRANSFERRED_TO]->(receiver:Account)
            RETURN sender.account_id AS source,
                   receiver.account_id AS target,
                   t.amount AS amount,
                   t.is_synthetic_fraud AS is_fraud,
                   t.timestamp AS timestamp
            ORDER BY t.timestamp DESC
            LIMIT $limit
        """, limit=limit)
        edges = [dict(r) for r in result]

        node_ids = set()
        for e in edges:
            node_ids.add(e["source"])
            node_ids.add(e["target"])

        if node_ids:
            node_result = session.run("""
                MATCH (a:Account) WHERE a.account_id IN $ids
                RETURN a.account_id AS id,
                       a.louvain_community_id AS louvain_community,
                       a.pagerank_weighted AS pagerank_weighted
            """, ids=list(node_ids))
            nodes = [dict(r) for r in node_result]
        else:
            nodes = []

        return {"nodes": nodes, "edges": edges}


@app.get("/api/account/{account_id}")
def get_account(account_id: str):
    with driver.session() as session:
        result = session.run("""
            MATCH (a:Account {account_id: $account_id})
            OPTIONAL MATCH (sender:Account)-[t_in:TRANSFERRED_TO]->(a)
            OPTIONAL MATCH (a)-[t_out:TRANSFERRED_TO]->(receiver:Account)
            RETURN a.account_id AS account_id,
                   a.wcc_component_id AS wcc_component,
                   a.louvain_community_id AS louvain_community,
                   a.pagerank_weighted AS pagerank_weighted,
                   count(DISTINCT sender) AS distinct_senders,
                   count(DISTINCT receiver) AS distinct_receivers,
                   count(DISTINCT t_in) AS incoming_txn_count,
                   count(DISTINCT t_out) AS outgoing_txn_count
        """, account_id=account_id)
        record = result.single()
        if record is None or record["account_id"] is None:
            raise HTTPException(status_code=404, detail="Account not found")
        return dict(record)


@app.get("/api/account/{account_id}/edges")
def get_account_edges(account_id: str, limit: int = 50):
    with driver.session() as session:
        result = session.run("""
            MATCH (a:Account {account_id: $account_id})
            OPTIONAL MATCH (sender:Account)-[t_in:TRANSFERRED_TO]->(a)
            OPTIONAL MATCH (a)-[t_out:TRANSFERRED_TO]->(receiver:Account)
            WITH
                collect(DISTINCT {source: sender.account_id, target: a.account_id,
                                  amount: t_in.amount, is_fraud: t_in.is_synthetic_fraud,
                                  timestamp: t_in.timestamp}) AS incoming,
                collect(DISTINCT {source: a.account_id, target: receiver.account_id,
                                  amount: t_out.amount, is_fraud: t_out.is_synthetic_fraud,
                                  timestamp: t_out.timestamp}) AS outgoing
            RETURN incoming + outgoing AS edges
        """, account_id=account_id)
        record = result.single()
        edges = [e for e in (record["edges"] if record else []) if e["source"] and e["target"]]
        edges.sort(key=lambda e: e["timestamp"] or "", reverse=True)
        return edges[:limit]