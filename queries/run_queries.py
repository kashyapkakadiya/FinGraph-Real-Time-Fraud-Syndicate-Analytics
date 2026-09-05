import time

from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "fingraph123")


def canonicalize_cycle(chain):
    core = chain[:-1]
    min_idx = core.index(min(core))
    rotated = core[min_idx:] + core[:min_idx]
    return tuple(rotated)


def timed_run(session, cypher, params=None, warm_runs=1):
    records, summary, client_ms = None, None, None
    for _ in range(warm_runs + 1):
        start = time.perf_counter()
        result = session.run(cypher, params or {})
        records = [dict(r) for r in result]
        summary = result.consume()
        client_ms = (time.perf_counter() - start) * 1000

    server_ms = summary.result_available_after + summary.result_consumed_after
    return records, client_ms, server_ms


def report(label, records, client_ms, server_ms):
    print(f"\n{'=' * 60}\n{label}\n{'=' * 60}")
    for r in records:
        print(r)
    verdict = "PASS" if server_ms < 100 else "OVER 100ms TARGET"
    print(f"\n-- Client wall-clock: {client_ms:.2f} ms "
          f"(includes network + Python overhead)")
    print(f"-- Server-reported time: {server_ms:.2f} ms ({verdict} vs. doc's <100ms target)")


def main():
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()

        with driver.session() as session:
            with open("risk_scoring_optimized.cypher") as f:
                risk_records, risk_client_ms, risk_server_ms = timed_run(session, f.read())
            report("Risk Scoring (optimized, warm cache)", risk_records, risk_client_ms, risk_server_ms)

            candidate_ids = [r["account_id"] for r in risk_records]

            with open("circular_flow_detection_optimized.cypher") as f:
                cycle_records, cycle_client_ms, cycle_server_ms = timed_run(
                    session, f.read(), {"candidate_ids": candidate_ids})

            seen, deduped = set(), []
            for r in cycle_records:
                key = canonicalize_cycle(r["account_chain"])
                if key not in seen:
                    seen.add(key)
                    deduped.append(r)

            report(f"Circular Flow Detection (optimized, {len(candidate_ids)} candidates, warm cache)",
                   deduped, cycle_client_ms, cycle_server_ms)


if __name__ == "__main__":
    main()