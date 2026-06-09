import { useState, useEffect } from 'react'
import { TrendingUp, RefreshCw, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import { runForecast, getLatestForecast } from '../api/client'
import RunwayChart from '../components/RunwayChart.jsx'
import toast from 'react-hot-toast'

export default function ForecastPage({ activeBiz }) {
  const [forecast, setForecast]   = useState(null)
  const [loading, setLoading]     = useState(false)
  const [fetching, setFetching]   = useState(true)
  const [horizon, setHorizon]     = useState(90)
  const [retrain, setRetrain]     = useState(false)

  const loadExisting = async () => {
    if (!activeBiz) return
    setFetching(true)
    try {
      const fc = await getLatestForecast(activeBiz.id)
      setForecast(fc)
    } catch {
      // No forecast yet — that's fine
    } finally {
      setFetching(false)
    }
  }

  useEffect(() => { loadExisting() }, [activeBiz?.id])

  const handleRun = async () => {
    setLoading(true)
    try {
      const fc = await runForecast(activeBiz.id, { horizon_days: horizon, retrain })
      setForecast(fc)
      toast.success('Forecast generated!')
    } catch (err) {
      const msg = err.response?.data?.detail || 'Forecast failed'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  if (!activeBiz) return (
    <div className="empty" style={{ padding: 80 }}>
      <div className="empty-icon">📈</div>
      <div>Select a business first</div>
    </div>
  )

  const alertClass = !forecast ? ''
    : forecast.alert_message.includes('CRITICAL') ? 'alert-danger'
    : forecast.alert_message.includes('WARNING')  ? 'alert-warning'
    : forecast.alert_message.includes('HEALTHY')  ? 'alert-success'
    : 'alert-info'

  return (
    <div style={{ padding: 28 }}>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div className="page-title">Cash Flow Forecast</div>
          <div className="page-sub">{activeBiz.name}</div>
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <select
            value={horizon}
            onChange={e => setHorizon(Number(e.target.value))}
            style={{ width: 'auto' }}
          >
            <option value={30}>30 days</option>
            <option value={60}>60 days</option>
            <option value={90}>90 days</option>
          </select>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, margin: 0,
                          fontSize: 13, color: 'var(--gray-700)', cursor: 'pointer' }}>
            <input type="checkbox" checked={retrain} onChange={e => setRetrain(e.target.checked)} />
            Force retrain
          </label>
          <button className="btn btn-primary" onClick={handleRun} disabled={loading}>
            <TrendingUp size={14} />
            {loading ? 'Generating…' : 'Run Forecast'}
          </button>
        </div>
      </div>

      {fetching && <div className="loading"><div className="spinner" />Loading forecast…</div>}

      {!fetching && !forecast && (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <TrendingUp size={36} color="#94a3b8" style={{ margin: '0 auto 12px' }} />
          <div style={{ fontWeight: 600, marginBottom: 6 }}>No forecast yet</div>
          <div style={{ color: 'var(--gray-500)', fontSize: 13, marginBottom: 20 }}>
            Click "Run Forecast" to generate a {horizon}-day cash flow prediction using your transaction history.
          </div>
          <button className="btn btn-primary" onClick={handleRun} disabled={loading}>
            <TrendingUp size={14} />
            {loading ? 'Generating…' : `Generate ${horizon}-Day Forecast`}
          </button>
        </div>
      )}

      {forecast && (
        <>
          {/* Alert */}
          <div className={`alert ${alertClass}`} style={{ marginBottom: 20 }}>
            {forecast.alert_message}
          </div>

          {/* Summary cards */}
          <div className="grid-3" style={{ marginBottom: 20 }}>
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 12, color: 'var(--gray-500)', marginBottom: 6 }}>Current Balance</div>
              <div style={{ fontSize: 24, fontWeight: 700,
                            color: forecast.current_balance >= 0 ? '#16a34a' : '#dc2626' }}>
                ₹{forecast.current_balance.toLocaleString('en-IN')}
              </div>
            </div>
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 12, color: 'var(--gray-500)', marginBottom: 6 }}>Cash Runway</div>
              <div style={{ fontSize: 24, fontWeight: 700,
                            color: !forecast.runway_days ? '#16a34a'
                              : forecast.runway_days < 14 ? '#dc2626'
                              : forecast.runway_days < 30 ? '#d97706' : '#16a34a' }}>
                {forecast.runway_days ? `${forecast.runway_days} days` : 'Positive ✓'}
              </div>
            </div>
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 12, color: 'var(--gray-500)', marginBottom: 6 }}>First Risk Date</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: forecast.first_risk_date ? '#d97706' : '#16a34a' }}>
                {forecast.first_risk_date || 'None detected'}
              </div>
            </div>
          </div>

          {/* Chart */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div style={{ fontWeight: 600, marginBottom: 16 }}>
              {horizon}-Day Balance Trajectory
            </div>
            <RunwayChart
              predictions={forecast.predictions}
              firstRiskDate={forecast.first_risk_date}
              currentBalance={forecast.current_balance}
            />
          </div>

          {/* Predictions table — first 14 days */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div style={{ fontWeight: 600, marginBottom: 14 }}>Next 14 Days — Day by Day</div>
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Predicted Daily Net</th>
                  <th>Projected Balance</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {forecast.predictions.slice(0, 14).map((p, i) => (
                  <tr key={i}>
                    <td>{p.date}</td>
                    <td style={{ color: p.predicted_net >= 0 ? '#16a34a' : '#dc2626', fontWeight: 500 }}>
                      {p.predicted_net >= 0 ? '+' : ''}₹{p.predicted_net.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </td>
                    <td style={{ fontWeight: 600 }}>
                      ₹{p.cumulative_balance.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </td>
                    <td>
                      {p.cumulative_balance <= 0
                        ? <span className="badge badge-red">⚠ Deficit</span>
                        : p.cumulative_balance < 5000
                        ? <span className="badge badge-yellow">Low</span>
                        : <span className="badge badge-green">OK</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Model metrics */}
          {forecast.metrics && Object.keys(forecast.metrics).length > 0 && (
            <div className="card">
              <div style={{ fontWeight: 600, marginBottom: 14 }}>Model Info</div>
              <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', fontSize: 13 }}>
                {forecast.metrics.training_days && (
                  <div>
                    <span style={{ color: 'var(--gray-500)' }}>Training days: </span>
                    <strong>{forecast.metrics.training_days}</strong>
                  </div>
                )}
                {forecast.metrics.avg_mae && (
                  <div>
                    <span style={{ color: 'var(--gray-500)' }}>Avg MAE: </span>
                    <strong>₹{forecast.metrics.avg_mae.toFixed(0)}</strong>
                  </div>
                )}
                {forecast.metrics.avg_rmse && (
                  <div>
                    <span style={{ color: 'var(--gray-500)' }}>Avg RMSE: </span>
                    <strong>₹{forecast.metrics.avg_rmse.toFixed(0)}</strong>
                  </div>
                )}
                {forecast.metrics.note && (
                  <div style={{ color: '#d97706' }}>⚠ {forecast.metrics.note}</div>
                )}
              </div>
              <div style={{ marginTop: 10, fontSize: 12, color: 'var(--gray-500)' }}>
                Generated: {forecast.generated_at?.slice(0, 19).replace('T', ' ')} UTC
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
