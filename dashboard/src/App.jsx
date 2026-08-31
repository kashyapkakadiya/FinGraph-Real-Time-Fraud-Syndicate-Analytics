import { useEffect, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'

const API_BASE = 'http://localhost:8000'

export default function App() {
  const [stats, setStats] = useState(null)
  const [riskScores, setRiskScores] = useState([])
  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function loadAll() {
      try {
        const [statsRes, riskRes, graphRes] = await Promise.all([
          fetch(`${API_BASE}/api/stats`),
          fetch(`${API_BASE}/api/risk-scores?limit=15`),
          fetch(`${API_BASE}/api/graph?limit=150`),
        ])
        if (!statsRes.ok || !riskRes.ok || !graphRes.ok) {
          throw new Error('One or more API calls failed')
        }
        setStats(await statsRes.json())
        setRiskScores(await riskRes.json())

        const raw = await graphRes.json()
        // react-force-graph wants "links" with source/target, which matches
        // the API's edge shape directly -- just rename edges -> links.
        setGraphData({
          nodes: raw.nodes,
          links: raw.edges.map((e) => ({
            source: e.source,
            target: e.target,
            amount: e.amount,
            is_fraud: e.is_fraud,
          })),
        })
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    loadAll()
  }, [])

  if (loading) return <div style={styles.centered}>Loading FinGraph...</div>
  if (error) {
    return (
      <div style={styles.centered}>
        Failed to load: {error}. Is the backend running on port 8000?
      </div>
    )
  }

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <h1 style={{ margin: 0 }}>FinGraph — Fraud Syndicate Dashboard</h1>
        <div style={styles.statsRow}>
          <StatCard label="Accounts" value={stats.account_count} />
          <StatCard label="Transactions" value={stats.transaction_count} />
          <StatCard label="Flagged Fraud" value={stats.fraud_count} highlight />
        </div>
      </header>

      <main style={styles.main}>
        <section style={styles.graphPanel}>
          <h2 style={styles.sectionTitle}>Live Transaction Graph (latest 150)</h2>
          <ForceGraph2D
            graphData={graphData}
            width={800}
            height={600}
            nodeLabel="id"
            nodeColor={() => '#c084c4'}
            linkColor={(link) => (link.is_fraud ? '#e63946' : '#cccccc')}
            linkWidth={(link) => (link.is_fraud ? 2 : 0.5)}
            linkDirectionalArrowLength={4}
          />
        </section>

        <section style={styles.riskPanel}>
          <h2 style={styles.sectionTitle}>Top Risk Accounts</h2>
          <table style={styles.table}>
            <thead>
              <tr>
                <th>Account</th>
                <th>Fan-in</th>
                <th>PageRank</th>
              </tr>
            </thead>
            <tbody>
              {riskScores.map((r) => (
                <tr key={r.account_id}>
                  <td>{r.account_id}</td>
                  <td>{r.fan_in}</td>
                  <td>{r.pagerank_weighted}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  )
}

function StatCard({ label, value, highlight }) {
  return (
    <div style={{ ...styles.statCard, ...(highlight ? styles.statCardHighlight : {}) }}>
      <div style={styles.statValue}>{value.toLocaleString()}</div>
      <div style={styles.statLabel}>{label}</div>
    </div>
  )
}

const styles = {
  page: { fontFamily: 'system-ui, sans-serif', background: '#0f0f14', color: '#eee', minHeight: '100vh' },
  centered: { display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', fontFamily: 'system-ui, sans-serif' },
  header: { padding: '1.5rem 2rem', borderBottom: '1px solid #333' },
  statsRow: { display: 'flex', gap: '1rem', marginTop: '1rem' },
  statCard: { background: '#1a1a22', padding: '1rem 1.5rem', borderRadius: 8, minWidth: 120 },
  statCardHighlight: { background: '#3a1a1f', border: '1px solid #e63946' },
  statValue: { fontSize: '1.8rem', fontWeight: 700 },
  statLabel: { fontSize: '0.85rem', color: '#999' },
  main: { display: 'flex', gap: '1.5rem', padding: '1.5rem 2rem' },
  graphPanel: { flex: 2 },
  riskPanel: { flex: 1 },
  sectionTitle: { fontSize: '1.1rem', marginBottom: '0.75rem' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' },
}