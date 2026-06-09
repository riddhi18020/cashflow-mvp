import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Wallet, Hash } from 'lucide-react'
import StatCard from '../components/StatCard'
import RunwayChart from '../components/RunwayChart'
import ScenarioSimulator from '../components/ScenarioSimulator'
import { getDashboard, runForecast } from '../api/client'
import toast from 'react-hot-toast'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts'

function fmt(v) {
  if (Math.abs(v) >= 100000) return `₹${(v/100000).toFixed(1)}L`
  if (Math.abs(v) >= 1000)   return `₹${(v/1000).toFixed(1)}K`
  return `₹${Math.round(v)}`
}

export default function DashboardPage({ activeBiz }) {
  const [data, setData]         = useState(null)
  const [loading, setLoading]   = useState(true)
  const [forecasting, setForecasting] = useState(false)

  const load = async () => {
    if (!activeBiz) return
    setLoading(true)
    try {
      const d = await getDashboard(activeBiz.id)
      setData(d)
    } catch (err) {
      toast.error('Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [activeBiz?.id])

  const handleForecast = async () => {
    setForecasting(true)
    try {
      await runForecast(activeBiz.id, { horizon_days: 90 })
      toast.success('Forecast generated!')
      load()
    } catch (err) {
      const msg = err.response?.data?.detail || 'Forecast failed'
      toast.error(msg)
    } finally {
      setForecasting(false)
    }
  }

  if (!activeBiz) return (
    <div className="empty" style={{ padding: 80 }}>
      <div className="empty-icon">🏪</div>
      <div>Select a business from the <a href="/" style={{ color: '#2563eb' }}>Businesses page</a> to view its dashboard.</div>
    </div>
  )

  if (loading) return <div className="loading"><div className="spinner" /> Loading dashboard…</div>
  if (!data)   return <div className="empty">No data available</div>

  const fc = data.latest_forecast

  // Determine alert class
  const alertClass = !fc ? 'alert-info'
    : fc.alert_message.includes('CRITICAL') ? 'alert-danger'
    : fc.alert_message.includes('WARNING')  ? 'alert-warning'
    : fc.alert_message.includes('HEALTHY')  ? 'alert-success'
    : 'alert-info'

  // Daily bar chart data (last 30 days)
  const barData = data.daily_history.slice(-30).map(d => ({
    date: d.date.slice(5),
    net: d.daily_net,
  }))

  return (
    <div style={{ padding: 28 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <div className="page-title">{activeBiz.name}</div>
          <div className="page-sub">{activeBiz.city} · {activeBiz.business_type}</div>
        </div>
        <button className="btn btn-primary" onClick={handleForecast} disabled={forecasting}>
          <TrendingUp size={14} />
          {forecasting ? 'Generating…' : fc ? 'Refresh Forecast' : 'Run Forecast'}
        </button>
      </div>

      {/* Alert banner */}
      {fc && (
        <div className={`alert ${alertClass}`} style={{ marginBottom: 20 }}>
          {fc.alert_message}
        </div>
      )}

      {/* Stat cards */}
      <div className="grid-4" style={{ marginBottom: 20 }}>
        <StatCard
          label="Current Balance"
          value={fmt(data.total_balance)}
          icon={<Wallet size={18} />}
          color={data.total_balance >= 0 ? 'green' : 'red'}
        />
        <StatCard
          label="30-Day Inflow"
          value={fmt(data.last_30_days_inflow)}
          sub="Last 30 days"
          icon={<TrendingUp size={18} />}
          color="green"
        />
        <StatCard
          label="30-Day Outflow"
          value={fmt(data.last_30_days_outflow)}
          sub="Last 30 days"
          icon={<TrendingDown size={18} />}
          color="red"
        />
        <StatCard
          label="Cash Runway"
          value={fc?.runway_days ? `${fc.runway_days} days` : '—'}
          sub={fc?.first_risk_date ? `Risk on ${fc.first_risk_date}` : 'Run forecast to calculate'}
          icon={<Hash size={18} />}
          color={!fc?.runway_days ? 'gray' : fc.runway_days < 14 ? 'red' : fc.runway_days < 30 ? 'yellow' : 'green'}
        />
      </div>

      {/* Forecast chart */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ fontWeight: 600 }}>90-Day Cash Runway</div>
          {fc && <span style={{ fontSize: 12, color: '#64748b' }}>Generated {fc.generated_at.slice(0,10)}</span>}
        </div>
        <RunwayChart
          predictions={fc?.predictions || []}
          firstRiskDate={fc?.first_risk_date}
          currentBalance={data.total_balance}
        />
      </div>

      {/* Daily cashflow bar chart */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ fontWeight: 600, marginBottom: 16 }}>Daily Net Cashflow (Last 30 Days)</div>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={barData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
            <YAxis tickFormatter={v => fmt(v)} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={55} />
            <Tooltip formatter={v => [fmt(v), 'Net']} />
            <Bar dataKey="net" radius={[3, 3, 0, 0]}>
              {barData.map((entry, i) => (
                <Cell key={i} fill={entry.net >= 0 ? '#86efac' : '#fca5a5'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Scenario simulator */}
      {fc && (
        <div className="card">
          <ScenarioSimulator
            predictions={fc.predictions}
            currentBalance={data.total_balance}
          />
        </div>
      )}
    </div>
  )
}