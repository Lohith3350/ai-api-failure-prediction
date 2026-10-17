import React, { useState, useEffect, useRef, useMemo } from 'react'
import { createRoot } from 'react-dom/client'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from 'recharts'
import './style.css'

// API Base URL - using Vite proxy /api or direct localhost:8000
const API_BASE = '/api'

// Helper icons
function ActivityIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
    </svg>
  )
}

function ShieldAlertIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
      <line x1="12" y1="8" x2="12" y2="12"></line>
      <line x1="12" y1="16" x2="12.01" y2="16"></line>
    </svg>
  )
}

function ServerIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
      <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
      <line x1="6" y1="6" x2="6.01" y2="6"></line>
      <line x1="6" y1="18" x2="6.01" y2="18"></line>
    </svg>
  )
}

function RefreshIcon({ spinning }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ animation: spinning ? 'spin 1s linear infinite' : 'none' }}
    >
      <polyline points="23 4 23 10 17 10"></polyline>
      <polyline points="1 20 1 14 7 14"></polyline>
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
      <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
    </svg>
  )
}

function PlayIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <polygon points="5 3 19 12 5 21 5 3"></polygon>
    </svg>
  )
}

function PauseIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="4" width="4" height="16"></rect>
      <rect x="14" y="4" width="4" height="16"></rect>
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"></polyline>
    </svg>
  )
}

export default function App() {
  // State variables
  const [overview, setOverview] = useState(null)
  const [topology, setTopology] = useState(null)
  const [predictions, setPredictions] = useState([])
  const [telemetry, setTelemetry] = useState([])
  const [incidents, setIncidents] = useState([])
  const [selectedService, setSelectedService] = useState('all')
  const [chartMetric, setChartMetric] = useState('latency') // 'latency' | 'risk' | 'errors' | 'resources'
  const [isStreaming, setIsStreaming] = useState(true)
  const [activeScenario, setActiveScenario] = useState('normal')
  const [isInjecting, setIsInjecting] = useState(false)
  const [connected, setConnected] = useState(true)
  const [lastRefreshed, setLastRefreshed] = useState(new Date())
  const [remediationMsg, setRemediationMsg] = useState(null)

  // Fetch all state from FastAPI backend
  const fetchData = async () => {
    try {
      const [ovRes, topRes, predRes, telemRes, incRes] = await Promise.all([
        fetch(`${API_BASE}/system/overview`),
        fetch(`${API_BASE}/system/topology`),
        fetch(`${API_BASE}/predictions`),
        fetch(`${API_BASE}/telemetry/recent?limit=45`),
        fetch(`${API_BASE}/incidents`),
      ])

      if (ovRes.ok && topRes.ok && predRes.ok) {
        const [ovData, topData, predData, telemData, incData] = await Promise.all([
          ovRes.json(),
          topRes.json(),
          predRes.json(),
          telemRes.json(),
          incRes.json(),
        ])

        setOverview(ovData)
        setTopology(topData)
        setPredictions(predData.predictions || [])
        setTelemetry(telemData.records || [])
        setIncidents(incData.incidents || [])
        setConnected(true)
        setLastRefreshed(new Date())
      } else {
        setConnected(false)
      }
    } catch (err) {
      console.warn('Backend polling error:', err)
      setConnected(false)
    }
  }

  // Initial and recurring poll
  useEffect(() => {
    fetchData()
    if (!isStreaming) return
    const interval = setInterval(fetchData, 2500)
    return () => clearInterval(interval)
  }, [isStreaming])

  // Step simulation scenario
  const handleStepSimulation = async (scenario = activeScenario) => {
    setIsInjecting(true)
    try {
      const res = await fetch(`${API_BASE}/simulation/step`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario }),
      })
      if (res.ok) {
        await fetchData()
      }
    } catch (err) {
      console.error('Simulation step error:', err)
    } finally {
      setIsInjecting(false)
    }
  }

  // Reset simulation
  const handleResetSimulation = async () => {
    try {
      const res = await fetch(`${API_BASE}/simulation/reset`, { method: 'POST' })
      if (res.ok) {
        setActiveScenario('normal')
        setRemediationMsg('Simulation reset to baseline normal traffic.')
        setTimeout(() => setRemediationMsg(null), 4000)
        await fetchData()
      }
    } catch (err) {
      console.error('Reset error:', err)
    }
  }

  // Apply simulated remediation action
  const handleApplyRemediation = async (actionText) => {
    setRemediationMsg(`Applying automated mitigation: "${actionText}"...`)
    // Step simulation back to normal to demonstrate resolution
    await handleStepSimulation('normal')
    setActiveScenario('normal')
    setTimeout(() => {
      setRemediationMsg(`Mitigation applied successfully. Circuit breaker triggered and traffic normalized.`)
      setTimeout(() => setRemediationMsg(null), 5000)
    }, 1200)
  }

  // Process telemetry data for charting
  const formattedChartData = useMemo(() => {
    if (!telemetry || telemetry.length === 0) return []

    // Filter by selected service if not 'all'
    const filtered = selectedService === 'all'
      ? telemetry
      : telemetry.filter(r => r.service_name === selectedService)

    // Group by timestamp or step sequence for multi-service display
    // If 'all', compute average or show individual service points
    const pointsMap = new Map()

    filtered.forEach(r => {
      const timeStr = r.timestamp ? r.timestamp.slice(11, 19) : ''
      const key = `${timeStr}-${r.service_name}`
      
      if (!pointsMap.has(timeStr)) {
        pointsMap.set(timeStr, {
          time: timeStr,
          timestamp: r.timestamp,
        })
      }
      const entry = pointsMap.get(timeStr)
      const prefix = selectedService === 'all' ? r.service_name.replace('-', '_') : 'val'

      entry[`${prefix}_latency`] = r.response_time_ms
      entry[`${prefix}_error_rate`] = (r.error_rate * 100).toFixed(1)
      entry[`${prefix}_timeouts`] = r.timeout_count
      entry[`${prefix}_cpu`] = r.cpu_usage_pct
      entry[`${prefix}_memory`] = r.memory_usage_pct
      entry[`${prefix}_dep_latency`] = r.dependency_latency_ms || 0
      entry.service_name = r.service_name
    })

    return Array.from(pointsMap.values()).slice(-25)
  }, [telemetry, selectedService])

  // Get primary root cause from overview or prediction
  const primaryRootCause = overview?.primary_root_cause

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo">
            <ActivityIcon />
          </div>
          <div className="brand-title">
            <h1>
              SPECTRA <span className="brand-tag">ML Failure Predictor</span>
            </h1>
            <p className="brand-subtitle">
              Real-time microservice degradation forecasting, dependency cascade analysis & decision engine
            </p>
          </div>
        </div>

        <div className="header-controls">
          <div className="connection-pill">
            <span className={`pulse-dot ${connected ? '' : 'error'}`}></span>
            {connected ? 'FastAPI Backend Online (:8000)' : 'Backend Disconnected'}
            <span className="mono" style={{ fontSize: '0.68rem', color: '#64748b' }}>
              {lastRefreshed.toLocaleTimeString()}
            </span>
          </div>

          <button
            className={`btn ${isStreaming ? 'btn-active' : ''}`}
            onClick={() => setIsStreaming(!isStreaming)}
            title={isStreaming ? 'Pause live stream' : 'Resume live stream'}
          >
            {isStreaming ? <PauseIcon /> : <PlayIcon />}
            {isStreaming ? 'Live Polling (2.5s)' : 'Polling Paused'}
          </button>

          <button
            className="btn"
            onClick={() => fetchData()}
            title="Refresh now"
          >
            <RefreshIcon spinning={false} />
            Refresh
          </button>
        </div>
      </header>

      {/* Scenario Control Bar */}
      <section className="scenario-bar">
        <div className="scenario-title">
          <ShieldAlertIcon />
          <span>Interactive Chaos & Traffic Simulation:</span>
        </div>

        <div className="scenario-buttons">
          <button
            className={`btn ${activeScenario === 'normal' ? 'btn-active' : ''}`}
            onClick={() => {
              setActiveScenario('normal')
              handleStepSimulation('normal')
            }}
          >
            Nominal Traffic
          </button>

          <button
            className={`btn ${activeScenario === 'degraded' ? 'btn-active' : ''}`}
            onClick={() => {
              setActiveScenario('degraded')
              handleStepSimulation('degraded')
            }}
          >
            Payment Latency (Degraded)
          </button>

          <button
            className={`btn btn-danger ${activeScenario === 'critical' ? 'btn-active' : ''}`}
            onClick={() => {
              setActiveScenario('critical')
              handleStepSimulation('critical')
            }}
          >
            Cascade Outage (Critical)
          </button>

          <button
            className={`btn ${activeScenario === 'spike' ? 'btn-active' : ''}`}
            onClick={() => {
              setActiveScenario('spike')
              handleStepSimulation('spike')
            }}
          >
            Traffic Burst
          </button>

          <button
            className="btn btn-primary"
            onClick={() => handleStepSimulation(activeScenario)}
            disabled={isInjecting}
          >
            <RefreshIcon spinning={isInjecting} />
            Step Window (+10s)
          </button>

          <button
            className="btn"
            onClick={handleResetSimulation}
            title="Reset telemetry and ML buffer to clean baseline"
          >
            Reset
          </button>
        </div>
      </section>

      {/* Notification Banner */}
      {remediationMsg && (
        <div style={{
          background: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid #10b981',
          color: '#34d399',
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '20px',
          fontSize: '0.85rem',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <CheckIcon />
          <span>{remediationMsg}</span>
        </div>
      )}

      {/* KPI Stat Cards Row */}
      <section className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">
            <span>System Status</span>
            <span className={`badge badge-${(overview?.status || 'HEALTHY').toLowerCase()}`}>
              {overview?.status || 'HEALTHY'}
            </span>
          </div>
          <div className="kpi-value mono">
            {overview?.healthy_count || 3}/{overview?.total_services || 3}
          </div>
          <div className="kpi-subtext">Services operating within nominal thresholds</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>Mean Cluster Latency</span>
            <ActivityIcon />
          </div>
          <div className="kpi-value mono">
            {overview?.average_cluster_latency_ms || 0} <span style={{ fontSize: '1rem', color: '#64748b' }}>ms</span>
          </div>
          <div className="kpi-subtext">Rolling mean across edge and internal APIs</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>Peak Failure Risk</span>
            <span className="brand-tag">XGBoost H=3</span>
          </div>
          <div className="kpi-value mono" style={{
            color: (overview?.peak_failure_probability || 0) >= 0.85 ? '#fb7185' : ((overview?.peak_failure_probability || 0) >= 0.3 ? '#fbbf24' : '#34d399')
          }}>
            {((overview?.peak_failure_probability || 0) * 100).toFixed(1)}%
          </div>
          <div className="kpi-subtext">Calibrated probability within next 30s horizon</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>Primary Root Cause</span>
            <ServerIcon />
          </div>
          <div className="kpi-value mono" style={{ fontSize: '1.25rem' }}>
            {primaryRootCause ? primaryRootCause : 'None (Nominal)'}
          </div>
          <div className="kpi-subtext">
            {primaryRootCause ? 'Identified by telemetry & dependency traversal' : 'No upstream or downstream anomalies'}
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>Active Incidents</span>
            <ShieldAlertIcon />
          </div>
          <div className="kpi-value mono" style={{ color: (incidents.length > 0 ? '#fb7185' : '#94a3b8') }}>
            {incidents.length}
          </div>
          <div className="kpi-subtext">
            {incidents.length > 0 ? 'Requires operator mitigation' : 'No active alerts pending'}
          </div>
        </div>
      </section>

      {/* Microservice Dependency Topology */}
      <section className="panel" style={{ marginBottom: '24px' }}>
        <div className="panel-header">
          <div className="panel-title">
            <ServerIcon />
            <span>Service Architecture & Live Dependency Graph</span>
          </div>
          <div className="panel-actions">
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
              Click any node to focus charts on that service
            </span>
          </div>
        </div>

        <div className="topology-container">
          {topology?.nodes?.map((node, idx) => {
            const pred = node.prediction || {}
            const metrics = node.metrics || {}
            const isSelected = selectedService === node.id
            const risk = pred.risk_level || 'LOW'
            const isCritical = risk === 'CRITICAL'
            const isDegraded = risk === 'MEDIUM' || risk === 'HIGH'

            return (
              <React.Fragment key={node.id}>
                <div
                  className={`topology-node ${isSelected ? 'selected' : ''} ${isCritical ? 'critical' : (isDegraded ? 'degraded' : '')}`}
                  onClick={() => setSelectedService(selectedService === node.id ? 'all' : node.id)}
                >
                  <div className="node-header">
                    <div>
                      <div className="node-title">{node.name}</div>
                      <div className="node-port mono">:{node.port} • {node.role}</div>
                    </div>
                    <span className={`badge badge-${risk.toLowerCase()}`}>{risk}</span>
                  </div>

                  <div className="node-metrics">
                    <div className="metric-pill">
                      <span>Latency</span>
                      <strong className="mono">{metrics.response_time_ms ? `${metrics.response_time_ms.toFixed(1)} ms` : '—'}</strong>
                    </div>
                    <div className="metric-pill">
                      <span>Error Rate</span>
                      <strong className="mono" style={{ color: (metrics.error_rate > 0.05 ? '#fb7185' : '#e2e8f0') }}>
                        {metrics.error_rate !== undefined ? `${(metrics.error_rate * 100).toFixed(1)}%` : '0.0%'}
                      </strong>
                    </div>
                    <div className="metric-pill">
                      <span>CPU Saturation</span>
                      <strong className="mono">{metrics.cpu_usage_pct ? `${metrics.cpu_usage_pct.toFixed(1)}%` : '—'}</strong>
                    </div>
                    <div className="metric-pill">
                      <span>Failure Risk</span>
                      <strong className="mono" style={{ color: isCritical ? '#fb7185' : (isDegraded ? '#fbbf24' : '#34d399') }}>
                        {pred.failure_probability !== undefined ? `${(pred.failure_probability * 100).toFixed(1)}%` : '0.0%'}
                      </strong>
                    </div>
                  </div>

                  {pred.failure_probability >= 0.3 && (
                    <div style={{ marginTop: '10px', fontSize: '0.7rem', color: '#fb7185', fontWeight: 600 }}>
                      ⚠️ High Failure Probability Predicted
                    </div>
                  )}
                </div>

                {idx < (topology.nodes.length - 1) && (
                  <div className="topology-edge">
                    <span className="edge-label">{topology.edges[idx]?.label}</span>
                    <div className="edge-arrow">
                      <div className={`edge-line ${isDegraded || isCritical ? 'degraded' : 'active'}`}></div>
                      <span style={{ fontSize: '0.9rem', color: isCritical ? '#f43f5e' : '#38bdf8' }}>▶</span>
                    </div>
                    <span className="mono" style={{ fontSize: '0.65rem' }}>
                      {topology.edges[idx]?.latency_ms ? `${topology.edges[idx].latency_ms.toFixed(0)}ms dep` : ''}
                    </span>
                  </div>
                )}
              </React.Fragment>
            )
          })}
        </div>
      </section>

      {/* Main Two-Column Layout: Charts & Predictions */}
      <div className="two-col-grid">
        {/* Left Column: Live Telemetry Charts */}
        <section className="panel">
          <div className="panel-header">
            <div className="panel-title">
              <ActivityIcon />
              <span>Real-Time Telemetry & Predictive Horizon</span>
            </div>

            <div className="panel-actions">
              {/* Service filter */}
              <div className="tab-group">
                <button
                  className={`tab-btn ${selectedService === 'all' ? 'active' : ''}`}
                  onClick={() => setSelectedService('all')}
                >
                  All Services
                </button>
                <button
                  className={`tab-btn ${selectedService === 'user-service' ? 'active' : ''}`}
                  onClick={() => setSelectedService('user-service')}
                >
                  user-service
                </button>
                <button
                  className={`tab-btn ${selectedService === 'order-service' ? 'active' : ''}`}
                  onClick={() => setSelectedService('order-service')}
                >
                  order-service
                </button>
                <button
                  className={`tab-btn ${selectedService === 'payment-service' ? 'active' : ''}`}
                  onClick={() => setSelectedService('payment-service')}
                >
                  payment-service
                </button>
              </div>

              {/* Metric filter */}
              <div className="tab-group">
                <button
                  className={`tab-btn ${chartMetric === 'latency' ? 'active' : ''}`}
                  onClick={() => setChartMetric('latency')}
                >
                  Latency
                </button>
                <button
                  className={`tab-btn ${chartMetric === 'errors' ? 'active' : ''}`}
                  onClick={() => setChartMetric('errors')}
                >
                  Errors
                </button>
                <button
                  className={`tab-btn ${chartMetric === 'resources' ? 'active' : ''}`}
                  onClick={() => setChartMetric('resources')}
                >
                  CPU / Memory
                </button>
              </div>
            </div>
          </div>

          {/* Chart Rendering */}
          <div style={{ height: 320, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              {chartMetric === 'latency' ? (
                <AreaChart data={formattedChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorUser" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#38bdf8" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorOrder" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#818cf8" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#818cf8" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorPayment" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.45}/>
                      <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 11 }} unit="ms" />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (!active || !payload) return null
                      return (
                        <div className="recharts-custom-tooltip">
                          <div className="tooltip-time mono">{label}</div>
                          {payload.map((p, i) => (
                            <div key={i} className="tooltip-metric" style={{ color: p.color }}>
                              <span>{p.name}:</span>
                              <strong className="mono">{p.value} ms</strong>
                            </div>
                          ))}
                        </div>
                      )
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '0.75rem', paddingTop: '10px' }} />
                  <ReferenceLine y={160} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: 'Degraded Thr (160ms)', fill: '#f59e0b', fontSize: 10 }} />
                  <ReferenceLine y={400} stroke="#f43f5e" strokeDasharray="4 4" label={{ value: 'Critical Outage Thr (400ms)', fill: '#f43f5e', fontSize: 10 }} />
                  
                  {selectedService === 'all' ? (
                    <>
                      <Area type="monotone" dataKey="user_service_latency" name="user-service" stroke="#38bdf8" fill="url(#colorUser)" strokeWidth={2} />
                      <Area type="monotone" dataKey="order_service_latency" name="order-service" stroke="#818cf8" fill="url(#colorOrder)" strokeWidth={2} />
                      <Area type="monotone" dataKey="payment_service_latency" name="payment-service" stroke="#f43f5e" fill="url(#colorPayment)" strokeWidth={2.5} />
                    </>
                  ) : (
                    <>
                      <Area type="monotone" dataKey="val_latency" name={`${selectedService} Latency`} stroke="#38bdf8" fill="url(#colorUser)" strokeWidth={2.5} />
                      <Line type="monotone" dataKey="val_dep_latency" name="Dependency Latency" stroke="#f43f5e" strokeWidth={1.8} strokeDasharray="5 5" />
                    </>
                  )}
                </AreaChart>
              ) : chartMetric === 'errors' ? (
                <AreaChart data={formattedChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 11 }} unit="%" />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (!active || !payload) return null
                      return (
                        <div className="recharts-custom-tooltip">
                          <div className="tooltip-time mono">{label}</div>
                          {payload.map((p, i) => (
                            <div key={i} className="tooltip-metric" style={{ color: p.color }}>
                              <span>{p.name}:</span>
                              <strong className="mono">{p.value}%</strong>
                            </div>
                          ))}
                        </div>
                      )
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '0.75rem', paddingTop: '10px' }} />
                  <ReferenceLine y={20} stroke="#f43f5e" strokeDasharray="3 3" label={{ value: 'Error SLA (20%)', fill: '#f43f5e', fontSize: 10 }} />
                  {selectedService === 'all' ? (
                    <>
                      <Area type="monotone" dataKey="order_service_error_rate" name="order-service Error %" stroke="#f43f5e" fill="rgba(244,63,94,0.3)" strokeWidth={2} />
                      <Area type="monotone" dataKey="payment_service_error_rate" name="payment-service Error %" stroke="#f59e0b" fill="rgba(245,158,11,0.2)" strokeWidth={2} />
                      <Area type="monotone" dataKey="user_service_error_rate" name="user-service Error %" stroke="#38bdf8" fill="rgba(56,189,248,0.1)" strokeWidth={2} />
                    </>
                  ) : (
                    <>
                      <Area type="monotone" dataKey="val_error_rate" name="Error Rate %" stroke="#f43f5e" fill="rgba(244,63,94,0.3)" strokeWidth={2.5} />
                      <Line type="monotone" dataKey="val_timeouts" name="Timeouts Count" stroke="#fbbf24" strokeWidth={2} />
                    </>
                  )}
                </AreaChart>
              ) : (
                <LineChart data={formattedChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 11 }} unit="%" domain={[0, 100]} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: '0.75rem', paddingTop: '10px' }} />
                  <ReferenceLine y={90} stroke="#f43f5e" strokeDasharray="4 4" label={{ value: 'CPU Saturation (90%)', fill: '#f43f5e', fontSize: 10 }} />
                  {selectedService === 'all' ? (
                    <>
                      <Line type="monotone" dataKey="payment_service_cpu" name="payment-service CPU %" stroke="#f43f5e" strokeWidth={2.5} dot={false} />
                      <Line type="monotone" dataKey="order_service_cpu" name="order-service CPU %" stroke="#818cf8" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="user_service_cpu" name="user-service CPU %" stroke="#38bdf8" strokeWidth={2} dot={false} />
                    </>
                  ) : (
                    <>
                      <Line type="monotone" dataKey="val_cpu" name="CPU Usage %" stroke="#f43f5e" strokeWidth={2.5} />
                      <Line type="monotone" dataKey="val_memory" name="Memory Usage %" stroke="#38bdf8" strokeWidth={2} />
                    </>
                  )}
                </LineChart>
              )}
            </ResponsiveContainer>
          </div>
        </section>

        {/* Right Column: Predictive Models & Feature Attribution */}
        <section className="panel">
          <div className="panel-header">
            <div className="panel-title">
              <ShieldAlertIcon />
              <span>Predictive Intelligence & Feature Attributions</span>
            </div>
            <span className="brand-tag">SHAP / Tree Weights</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {predictions.map(pred => {
              const prob = pred.failure_probability || 0
              const risk = pred.risk_level || 'LOW'
              const anom = pred.anomaly_score || 0
              const topExplanation = pred.explanation || []

              return (
                <div key={pred.service_name} className="pred-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>{pred.service_name}</span>
                    <span className={`badge badge-${risk.toLowerCase()}`}>{risk}</span>
                  </div>

                  <div className="prob-meter">
                    <div className="prob-header">
                      <span>Failure Probability (Horizon = 30s)</span>
                      <span className="mono">{(prob * 100).toFixed(1)}%</span>
                    </div>
                    <div className="prob-track">
                      <div
                        className={`prob-fill ${risk.toLowerCase()}`}
                        style={{ width: `${Math.min(100, Math.max(2, prob * 100))}%` }}
                      ></div>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: '#64748b', marginTop: '2px' }}>
                      <span>Nominal (0%)</span>
                      <span className="mono">Anomaly Score: {anom.toFixed(3)}</span>
                      <span>Critical (100%)</span>
                    </div>
                  </div>

                  {/* Feature attributions bar */}
                  {topExplanation.length > 0 && (
                    <div className="attribution-list">
                      <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase' }}>
                        Top Contributing Factors
                      </span>
                      {topExplanation.map((attr, i) => {
                        const impPct = Math.min(100, (attr.model_importance || 0.1) * 100)
                        return (
                          <div key={i} className="attribution-item">
                            <div className="attr-label">
                              <span className="mono" style={{ fontSize: '0.7rem' }}>{attr.feature}</span>
                              <span className="mono" style={{ fontSize: '0.7rem' }}>
                                val: {typeof attr.value === 'number' ? attr.value.toFixed(1) : attr.value}
                              </span>
                            </div>
                            <div className="attr-bar-bg">
                              <div
                                className={`attr-bar-fill ${risk === 'CRITICAL' ? 'critical' : ''}`}
                                style={{ width: `${impPct}%` }}
                              ></div>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      </div>

      {/* Incidents & Decision Engine Recommendations Section */}
      <section className="panel" style={{ marginTop: '24px' }}>
        <div className="panel-header">
          <div className="panel-title">
            <ShieldAlertIcon />
            <span>Active Incidents & Automated Decision Engine Runbooks</span>
          </div>
          <span className="mono" style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
            Decision Engine: Risk Matrix & Circuit Breaker Policy
          </span>
        </div>

        {incidents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '36px 0', color: '#64748b' }}>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '10px' }}>
              <span className="badge badge-low" style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
                <CheckIcon /> All Microservices Operating Nominally
              </span>
            </div>
            <p style={{ fontSize: '0.85rem' }}>
              Zero SLA violations detected. Ingesting telemetry at 10-second intervals.
            </p>
          </div>
        ) : (
          <div className="incident-list">
            {incidents.map(inc => (
              <div key={inc.id} className={`incident-card ${inc.severity.toLowerCase()}`}>
                <div className="incident-header">
                  <div className="incident-title">
                    <span className={`badge badge-${inc.severity.toLowerCase()}`}>{inc.severity}</span>
                    <span>{inc.title}</span>
                  </div>
                  <span className="mono" style={{ fontSize: '0.72rem', color: '#64748b' }}>
                    {inc.timestamp?.slice(11, 19)}
                  </span>
                </div>

                <div className="incident-desc">
                  {inc.description}
                  {inc.root_cause_service && (
                    <strong style={{ color: '#fbbf24', marginLeft: '6px' }}>
                      Probable Root Cause: {inc.root_cause_service} ({(inc.confidence * 100).toFixed(0)}% confidence)
                    </strong>
                  )}
                </div>

                {inc.affected_downstream && inc.affected_downstream.length > 0 && (
                  <div style={{ fontSize: '0.75rem', color: '#fb923c' }}>
                    <strong>Cascade Ripple Impact:</strong> Degrading downstream callers: {inc.affected_downstream.join(', ')}
                  </div>
                )}

                {inc.recommended_actions && inc.recommended_actions.length > 0 && (
                  <div className="incident-actions-box">
                    <h4>Automated Runbook Recommendations</h4>
                    {inc.recommended_actions.map((action, idx) => (
                      <div key={idx} className="action-item" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                        <span>• {action}</span>
                        <button
                          className="btn btn-primary"
                          style={{ padding: '3px 9px', fontSize: '0.72rem' }}
                          onClick={() => handleApplyRemediation(action)}
                        >
                          Execute Runbook
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

createRoot(document.getElementById('root')).render(<App />)
