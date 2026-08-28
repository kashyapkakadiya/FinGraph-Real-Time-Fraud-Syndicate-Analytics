from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "fingraph123")

GRAPH_NAME = "fingraph-accounts"


def verify_gds(session):
    result = session.run("RETURN gds.version() AS version")
    version = result.single()["version"]
    print(f"GDS plugin active: version {version}")


def project_graph(session):
    session.run(f"""
        CALL gds.graph.exists('{GRAPH_NAME}') YIELD exists
        WITH exists WHERE exists
        CALL gds.graph.drop('{GRAPH_NAME}') YIELD graphName
        RETURN graphName
    """)

    # Day 14 update: now also projects 'amount' as a relationship property,
    # so PageRank (and any future algorithm) can optionally weight by
    # transaction size instead of treating every edge equally.
    result = session.run(f"""
        CALL gds.graph.project(
            '{GRAPH_NAME}',
            'Account',
            {{
                TRANSFERRED_TO: {{
                    properties: 'amount'
                }}
            }}
        )
        YIELD graphName, nodeCount, relationshipCount
        RETURN graphName, nodeCount, relationshipCount
    """)
    record = result.single()
    print(f"Projected graph '{record['graphName']}': "
          f"{record['nodeCount']} nodes, {record['relationshipCount']} relationships "
          f"(with 'amount' property for weighted algorithms)")


def main():
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            verify_gds(session)
            project_graph(session)


if __name__ == "__main__":
    main()