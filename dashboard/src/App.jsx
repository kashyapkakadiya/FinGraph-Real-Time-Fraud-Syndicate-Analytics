import { useEffect, useRef, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'

const API_BASE = 'http://localhost:8000'

export default function App() {
  const [stats, setStats] = useState(null)
  const [riskScores, setRiskScores] = useState([])
  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [selectedAccount, setSelectedAccount] = useState(null)
  const [minFanIn, setMinFanIn] = useState(0)
  const [initialGraphData, setInitialGraphData] = useState({ nodes: [], links: [] })

  const graphContainerRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })

  useEffect(() => {
    async function loadAll() {
      try {
        const [statsRes, riskRes, graphRes] = await Promise.all([
          fetch(`${API_BASE}/api/stats`),
          fetch(`${API_BASE}/api/risk-scores?limit=25`),
          fetch(`${API_BASE}/api/graph?limit=150`),
        ])
        if (!statsRes.ok || !riskRes.ok || !graphRes.ok) {
          throw new Error('One or more API calls failed')
        }
        setStats(await statsRes.json())
        setRiskScores(await riskRes.json())

        const raw = await graphRes.json()
        const shaped = toGraphShape(raw.nodes, raw.edges)
        setGraphData(shaped)
        setInitialGraphData(shaped)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    loadAll()
  }, [])

  useEffect(() => {
    function updateSize() {
      if (graphContainerRef.current) {
        const { width } = graphContainerRef.current.getBoundingClientRect()
        setDimensions({ width, height: 600 })
      }
    }
    updateSize()
    window.addEventListener('resize', updateSize)
    return () => window.removeEventListener('resize', updateSize)
  }, [])

  async function handleNodeClick(node) {
    try {
      const [detailRes, edgesRes] = await Promise.all([
        fetch(`${API_BASE}/api/account/${node.id}`),
        fetch(`${API_BASE}/api/account/${node.id}/edges?limit=50`),
      ])
      if (!detailRes.ok) throw new Error('Account not found')
      const detail = await detailRes.json()
      const edges = await edgesRes.json()

      setSelectedAccount(detail)

      setGraphData((prev) => {
        const existingNodeIds = new Set(prev.nodes.map((n) => n.id))
        const newNodeIds = new Set()
        edges.forEach((e) => {
          newNodeIds.add(e.source)
          newNodeIds.add(e.target)
        })
        const nodesToAdd = [...newNodeIds]
          .filter((id) => !existingNodeIds.has(id))
          .map((id) => ({ id }))

        const existingLinkKeys = new Set(
          prev.links.map((l) => `${l.source.id || l.source}->${l.target.id || l.target}`)
        )
        const linksToAdd = edges
          .filter((e) => !existingLinkKeys.has(`${e.source}->${e.target}`))
          .map((e) => ({ source: e.source, target: e.target, amount: e.amount, is_fraud: e.is_fraud }))

        return {
          nodes: [...prev.nodes, ...nodesToAdd],
          links: [...prev.links, ...linksToAdd],
        }
      })
    } catch (err) {
      setError(`Failed to expand ${node.id}: ${err.message}`)
    }
  }

  if (loading) return <div style={styles.centered}>Loading FinGraph...</div>
  if (error) {
    return (
      <div style={styles.centered}>
        Failed to load: {error}. Is the backend running on port 8000?
      </div>
    )
  }

  const filteredRiskScores = riskScores.filter((r) => r.fan_in >= minFanIn)

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
        <section style={styles.graphPanel} ref={graphContainerRef}>
          <h2 style={styles.sectionTitle}>
            Live Transaction Graph — click a node to trace its connections
          </h2>
          <div style={styles.legendRow}>
            <LegendSwatch color="#e63946" label="Fraud edge" isLine />
            <LegendSwatch color="#cccccc" label="Normal edge" isLine />
            <LegendSwatch color="#ffd166" label="Selected account" />
            <span style={{ color: '#999', fontSize: '0.8rem' }}>Node color = Louvain community</span>
            <button onClick={() => { setGraphData(initialGraphData); setSelectedAccount(null) }} style={styles.resetButton}>
              Reset view
            </button>
          </div>
          <ForceGraph2D
            graphData={graphData}
            width={dimensions.width}
            height={dimensions.height}
            nodeLabel="id"
            nodeColor={(node) =>
              selectedAccount && node.id === selectedAccount.account_id
                ? '#ffd166'
                : colorForCommunity(node.louvain_community)
            }
            nodeRelSize={5}
            nodeVal={(node) => 1 + Math.min(node.pagerank_weighted || 0, 10)}
            linkColor={(link) => (link.is_fraud ? '#e63946' : '#cccccc')}
            linkWidth={(link) => (link.is_fraud ? 2 : 0.5)}
            linkDirectionalArrowLength={4}
            onNodeClick={handleNodeClick}
          />

          {selectedAccount && (
            <div style={styles.detailPanel}>
              <h3 style={{ marginTop: 0 }}>{selectedAccount.account_id}</h3>
              <DetailRow label="Distinct senders" value={selectedAccount.distinct_senders} />
              <DetailRow label="Distinct receivers" value={selectedAccount.distinct_receivers} />
              <DetailRow label="Incoming transactions" value={selectedAccount.incoming_txn_count} />
              <DetailRow label="Outgoing transactions" value={selectedAccount.outgoing_txn_count} />
              <DetailRow label="WCC component" value={selectedAccount.wcc_component} />
              <DetailRow label="Louvain community" value={selectedAccount.louvain_community} />
              <DetailRow
                label="PageRank (weighted)"
                value={selectedAccount.pagerank_weighted?.toFixed(4)}
              />
            </div>
          )}
        </section>

        <section style={styles.riskPanel}>
          <h2 style={styles.sectionTitle}>Top Risk Accounts</h2>
          <label style={styles.filterLabel}>
            Min fan-in: {minFanIn}
            <input
              type="range"
              min="0"
              max="50"
              value={minFanIn}
              onChange={(e) => setMinFanIn(Number(e.target.value))}
              style={{ width: '100%' }}
            />
          </label>
          <table style={styles.table}>
            <thead>
              <tr>
                <th>Account</th>
                <th>Fan-in</th>
                <th>PageRank</th>
              </tr>
            </thead>
            <tbody>
              {filteredRiskScores.map((r) => (
                <tr
                  key={r.account_id}
                  onClick={() => handleNodeClick({ id: r.account_id })}
                  style={styles.clickableRow}
                >
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

function toGraphShape(nodes, edges) {
  return {
    nodes,
    links: edges.map((e) => ({
      source: e.source,
      target: e.target,
      amount: e.amount,
      is_fraud: e.is_fraud,
    })),
  }
}

const COMMUNITY_PALETTE = [
  '#c084c4', '#f4a261', '#2a9d8f', '#e76f51', '#8ecae6',
  '#ffb703', '#fb8500', '#06d6a0', '#ef476f', '#118ab2',
]
function colorForCommunity(communityId) {
  if (communityId === null || communityId === undefined) return '#666'
  return COMMUNITY_PALETTE[communityId % COMMUNITY_PALETTE.length]
}

function StatCard({ label, value, highlight }) {
  return (
    <div style={{ ...styles.statCard, ...(highlight ? styles.statCardHighlight : {}) }}>
      <div style={styles.statValue}>{value.toLocaleString()}</div>
      <div style={styles.statLabel}>{label}</div>
    </div>
  )
}

function DetailRow({ label, value }) {
  return (
    <div style={styles.detailRow}>
      <span style={{ color: '#999' }}>{label}</span>
      <span>{value ?? '—'}</span>
    </div>
  )
}

function LegendSwatch({ color, label, isLine }) {
  return (
    <span style={styles.legendItem}>
      <span
        style={
          isLine
            ? { ...styles.legendLine, background: color }
            : { ...styles.legendDot, background: color }
        }
      />
      {label}
    </span>
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
  graphPanel: { flex: 2, position: 'relative' },
  riskPanel: { flex: 1 },
  sectionTitle: { fontSize: '1.1rem', marginBottom: '0.75rem' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', marginTop: '0.75rem' },
  clickableRow: { cursor: 'pointer' },
  filterLabel: { display: 'block', fontSize: '0.85rem', color: '#999' },
  detailPanel: {
    position: 'absolute', top: 90, right: 10, background: '#1a1a22',
    border: '1px solid #333', borderRadius: 8, padding: '1rem', width: 240, fontSize: '0.85rem',
  },
  detailRow: { display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0' },
  legendRow: { display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem', flexWrap: 'wrap' },
  legendItem: { display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', color: '#ccc' },
  legendDot: { width: 10, height: 10, borderRadius: '50%', display: 'inline-block' },
  legendLine: { width: 16, height: 3, display: 'inline-block' },
  resetButton: {
    marginLeft: 'auto', background: '#2a2a35', color: '#eee', border: '1px solid #444',
    borderRadius: 6, padding: '0.3rem 0.75rem', fontSize: '0.8rem', cursor: 'pointer',
  },
}