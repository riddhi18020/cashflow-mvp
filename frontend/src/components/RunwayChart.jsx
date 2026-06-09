import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Legend
} from 'recharts'

function fmt(v) {
  if (Math.abs(v) >= 100000) return `₹${(v/100000).toFixed(1)}L`
  if (Math.abs(v) >= 1000)   return `₹${(v/1000).toFixed(1)}K`
  return `₹${v.toFixed(0)}`
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div style={{
      background: 'white', border: '1px solid #e2e8f0',
      borderRadius: 8, padding: '10px 14px', fontSize: 12,
      boxShadow: '0 4px 6px rgba(0,0,0,.07)',
    }}>
      <div style={{ fontWeight: 600, marginBottom: 6, color: '#1e293b' }}>{label}</div>
      <div style={{ color: '#2563eb' }}>Balance: {fmt(d?.cumulative_balance ?? 0)}</div>
      <div style={{ color: d?.predicted_net >= 0 ? '#16a34a' : '#dc2626', marginTop: 2 }}>
        Daily: {d?.predicted_net >= 0 ? '+' : ''}{fmt(d?.predicted_net ?? 0)}
      </div>
    </div>
  )
}

export default function RunwayChart({ predictions = [], firstRiskDate, currentBalance }) {
  if (!predictions.length) {
    return (
      <div className="empty">
        <div className="empty-icon">📈</div>
        <div>No forecast data — click "Run Forecast" to generate predictions</div>
      </div>
    )
  }

  // Show every 7th label to avoid clutter
  const data = predictions.map((p, i) => ({
    ...p,
    label: i % 7 === 0 ? p.date.slice(5) : '',  // MM-DD only
  }))

  const minBalance = Math.min(...predictions.map(p => p.cumulative_balance))
  const yMin = Math.min(minBalance * 1.1, -1000)

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
        <defs>
          <linearGradient id="balanceGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#2563eb" stopOpacity={0.15}/>
            <stop offset="95%" stopColor="#2563eb" stopOpacity={0.01}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: '#94a3b8' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={fmt}
          tick={{ fontSize: 11, fill: '#94a3b8' }}
          axisLine={false}
          tickLine={false}
          width={60}
        />
        <Tooltip content={<CustomTooltip />} />

        {/* Zero line */}
        <ReferenceLine y={0} stroke="#dc2626" strokeDasharray="4 2" strokeWidth={1.5}
          label={{ value: '₹0', position: 'right', fontSize: 10, fill: '#dc2626' }} />

        {/* Risk date */}
        {firstRiskDate && (
          <ReferenceLine
            x={firstRiskDate.slice(5)}
            stroke="#d97706"
            strokeDasharray="4 2"
            label={{ value: '⚠ Risk', position: 'top', fontSize: 10, fill: '#d97706' }}
          />
        )}

        <Area
          type="monotone"
          dataKey="cumulative_balance"
          stroke="#2563eb"
          strokeWidth={2}
          fill="url(#balanceGrad)"
          name="Balance"
          dot={false}
          activeDot={{ r: 4, fill: '#2563eb' }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
