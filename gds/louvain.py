from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "fingraph123")

GRAPH_NAME = "fingraph-accounts"

# The 6 giant WCC components from Day 12 that we suspect are over-merged.
GIANT_WCC_COMPONENT_IDS = [1385, 65, 958, 142, 2470, 0]


def run_louvain(session):
    """
    Writes 'louvain_community_id' onto every Account node. Louvain is
    iterative and hierarchical -- by default this writes the FINAL
    (most granular useful) level, which is what we want for splitting
    apart WCC's giant components.
    """
    result = session.run(f"""
        CALL gds.louvain.write('{GRAPH_NAME}', {{
            writeProperty: 'louvain_community_id'
        }})
        YIELD communityCount, modularity
        RETURN communityCount, modularity
    """)
    record = result.single()
    print(f"Louvain found {record['communityCount']} communities "
          f"(modularity: {record['modularity']:.4f})")


def louvain_top_communities(session, top_n=10):
    result = session.run("""
        MATCH (a:Account)-[t:TRANSFERRED_TO]->(b:Account)
        WHERE a.louvain_community_id = b.louvain_community_id
        WITH a.louvain_community_id AS community_id,
             count(t) AS txn_count,
             sum(CASE WHEN t.is_synthetic_fraud THEN 1 ELSE 0 END) AS fraud_count
        WHERE txn_count > 1
        RETURN community_id, txn_count, fraud_count,
               round(1.0 * fraud_count / txn_count, 2) AS fraud_ratio
        ORDER BY txn_count DESC
        LIMIT $top_n
    """, top_n=top_n)
    print(f"\nTop {top_n} Louvain communities by transaction volume:")
    for r in result:
        print(dict(r))


def compare_against_giant_wcc_components(session):
    """
    The real test: for each giant WCC component from Day 12, how many
    DISTINCT Louvain communities did it get split into? More than 1 means
    Louvain successfully separated sub-structure that WCC had merged.
    """
    print(f"\n{'=' * 60}\nWCC giant components -> Louvain sub-communities\n{'=' * 60}")
    for wcc_id in GIANT_WCC_COMPONENT_IDS:
        result = session.run("""
            MATCH (a:Account) WHERE a.wcc_component_id = $wcc_id
            WITH collect(DISTINCT a.louvain_community_id) AS sub_communities,
                 count(a) AS member_count
            RETURN sub_communities, member_count
        """, wcc_id=wcc_id)
        record = result.single()
        sub_communities = record["sub_communities"]
        print(f"WCC component {wcc_id} ({record['member_count']} accounts) "
              f"-> split into {len(sub_communities)} Louvain communities")

        for sub_id in sub_communities[:5]:
            sub_result = session.run("""
                MATCH (a:Account)-[t:TRANSFERRED_TO]->(b:Account)
                WHERE a.louvain_community_id = $sub_id
                  AND b.louvain_community_id = $sub_id
                RETURN count(t) AS txn_count,
                       sum(CASE WHEN t.is_synthetic_fraud THEN 1 ELSE 0 END) AS fraud_count
            """, sub_id=sub_id)
            sub_record = sub_result.single()
            txn_count = sub_record["txn_count"] or 0
            fraud_count = sub_record["fraud_count"] or 0
            ratio = round(fraud_count / txn_count, 2) if txn_count else 0.0
            print(f"    sub-community {sub_id}: {txn_count} txns, fraud_ratio {ratio}")


def main():
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            run_louvain(session)
            louvain_top_communities(session)
            compare_against_giant_wcc_components(session)


if __name__ == "__main__":
    main()