from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "fingraph123")

GRAPH_NAME = "fingraph-accounts"


def verify_gds(session):
    result = session.run("RETURN gds.version() AS version")
    version = result.single()["version"]
    print(f"GDS plugin active: version {version}")


def project_graph(session):
    # Drop any stale projection from a previous run first.
    session.run(f"""
        CALL gds.graph.exists('{GRAPH_NAME}') YIELD exists
        WITH exists WHERE exists
        CALL gds.graph.drop('{GRAPH_NAME}') YIELD graphName
        RETURN graphName
    """)

    # Project Account nodes and TRANSFERRED_TO relationships into GDS's
    # in-memory graph catalog. This is what WCC, Louvain, and PageRank
    # (Days 12-14) will actually run against -- much faster than querying
    # the transactional graph directly for iterative algorithms.
    result = session.run(f"""
        CALL gds.graph.project(
            '{GRAPH_NAME}',
            'Account',
            'TRANSFERRED_TO'
        )
        YIELD graphName, nodeCount, relationshipCount
        RETURN graphName, nodeCount, relationshipCount
    """)
    record = result.single()
    print(f"Projected graph '{record['graphName']}': "
          f"{record['nodeCount']} nodes, {record['relationshipCount']} relationships")


def main():
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            verify_gds(session)
            project_graph(session)


if __name__ == "__main__":
    main()