from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "fingraph123")
SCHEMA_FILE = "schema.cypher"


def apply_schema():
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        with open(SCHEMA_FILE, "r") as f:
            statements = [s.strip() for s in f.read().split(";") if s.strip() and not s.strip().startswith("//")]

        with driver.session() as session:
            for stmt in statements:
                clean = "\n".join(line for line in stmt.splitlines() if not line.strip().startswith("//"))
                if clean.strip():
                    session.run(clean)
                    print(f"Applied: {clean.splitlines()[0][:60]}...")

    print("Schema applied successfully.")


if __name__ == "__main__":
    apply_schema()