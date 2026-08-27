from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "fingraph123")

GRAPH_NAME = "fingraph-accounts"


def run_wcc(session):
    """
    Runs WCC and writes the result as a 'wcc_component_id' property on every
    Account node -- this makes the grouping queryable afterward without
    re-running the algorithm, and is what the dashboard (Day 16-17) will
    color-code by.
    """
    result = session.run(f"""
        CALL gds.wcc.write('{GRAPH_NAME}', {{
            writeProperty: 'wcc_component_id'
        }})
        YIELD componentCount, componentDistribution
        RETURN componentCount, componentDistribution
    """)
    record = result.single()
    print(f"WCC found {record['componentCount']} components")
    dist = record["componentDistribution"]
    print(f"Largest component size: {dist['max']}, "
          f"mean size: {dist['mean']:.2f}, p99: {dist['p99']}")


def largest_components(session, top_n=10):
    """Which components are actually big enough to be interesting."""
    result = session.run("""
        MATCH (a:Account)
        WITH a.wcc_component_id AS component_id, collect(a.account_id) AS members
        WHERE size(members) > 1
        RETURN component_id, size(members) AS member_count, members[0..5] AS sample_members
        ORDER BY member_count DESC
        LIMIT $top_n
    """, top_n=top_n)
    print(f"\nTop {top_n} components by size:")
    for r in result:
        print(dict(r))


def component_fraud_ratios(session, top_n=10):
    """
    For each component: how many of its internal transactions were flagged
    fraud. A component that's both LARGE and HIGH fraud ratio is exactly
    what a syndicate cluster looks like.
    """
    result = session.run("""
        MATCH (a:Account)-[t:TRANSFERRED_TO]->(b:Account)
        WHERE a.wcc_component_id = b.wcc_component_id
        WITH a.wcc_component_id AS component_id,
             count(t) AS txn_count,
             sum(CASE WHEN t.is_synthetic_fraud THEN 1 ELSE 0 END) AS fraud_count
        WHERE txn_count > 1
        RETURN component_id, txn_count, fraud_count,
               round(1.0 * fraud_count / txn_count, 2) AS fraud_ratio
        ORDER BY txn_count DESC
        LIMIT $top_n
    """, top_n=top_n)
    print(f"\nTop {top_n} components by transaction volume (with fraud ratio):")
    for r in result:
        print(dict(r))


def main():
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            run_wcc(session)
            largest_components(session)
            component_fraud_ratios(session)


if __name__ == "__main__":
    main()