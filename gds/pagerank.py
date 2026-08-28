from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "fingraph123")

GRAPH_NAME = "fingraph-accounts"


def run_pagerank_unweighted(session):
    """Pure structural importance -- every edge counts equally."""
    session.run(f"""
        CALL gds.pageRank.write('{GRAPH_NAME}', {{
            writeProperty: 'pagerank_unweighted'
        }})
        YIELD ranIterations, didConverge
    """)
    print("Unweighted PageRank written to 'pagerank_unweighted'")


def run_pagerank_weighted(session):
    """Amount-weighted -- a $9,800 transfer contributes more than a $50 one."""
    session.run(f"""
        CALL gds.pageRank.write('{GRAPH_NAME}', {{
            writeProperty: 'pagerank_weighted',
            relationshipWeightProperty: 'amount'
        }})
        YIELD ranIterations, didConverge
    """)
    print("Amount-weighted PageRank written to 'pagerank_weighted'")


def top_by_pagerank(session, property_name, top_n=15):
    result = session.run(f"""
        MATCH (a:Account)
        WHERE a.{property_name} IS NOT NULL
        RETURN a.account_id AS account_id, a.{property_name} AS score
        ORDER BY score DESC
        LIMIT $top_n
    """, top_n=top_n)
    print(f"\nTop {top_n} accounts by {property_name}:")
    for r in result:
        print(dict(r))


def blended_risk_view(session, top_n=15):
    """
    Combines yesterday's structural signals with today's PageRank into one
    view -- this is what a real risk dashboard would actually show: not one
    metric in isolation, but several signals corroborating each other.
    """
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
        LIMIT $top_n
    """, top_n=top_n)
    print(f"\nBlended risk view (fan-in + WCC + Louvain + weighted PageRank):")
    for r in result:
        print(dict(r))


def main():
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            run_pagerank_unweighted(session)
            run_pagerank_weighted(session)
            top_by_pagerank(session, "pagerank_unweighted")
            top_by_pagerank(session, "pagerank_weighted")
            blended_risk_view(session)


if __name__ == "__main__":
    main()