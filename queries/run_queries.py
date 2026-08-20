from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "fingraph123")


def run_query(driver, name, cypher):
    print(f"\n{'=' * 60}\n{name}\n{'=' * 60}")
    with driver.session() as session:
        result = session.run(cypher)
        records = list(result)
        if not records:
            print("(no results)")
            return
        for record in records:
            print(dict(record))


def main():
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()

        with open("risk_scoring.cypher") as f:
            run_query(driver, "Risk Scoring (top 25 by risk_score)", f.read())

        with open("circular_flow_detection.cypher") as f:
            run_query(driver, "Circular Flow Detection", f.read())


if __name__ == "__main__":
    main()
