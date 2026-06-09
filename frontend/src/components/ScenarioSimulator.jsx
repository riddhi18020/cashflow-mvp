import { useState, useEffect } from 'react'
import { SlidersHorizontal } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts'

function fmt(v) {
  if (Math.abs(v) >= 100000) return `₹${(v/100000).toFixed(1)}L`
  if (Math.abs(v) >= 1000)   return `₹${(v/1000).toFixed(1)}K`
  return `₹${v.toFixed(0)}`
}

export default function ScenarioSimulator({ predictions = [], currentBalance = 0 }) {
  const [rentDelta,      setRentDelta]      = useState(0)
  const [staffDelta,     setStaffDelta]     = useState(0)
  const [inventoryPct,   setInventoryPct]   = useState(0)
  const [revenuePct,     setRevenuePct]     = useState(0)

  const simulatedPredictions = predictions.map(p => {
    const adjustedNet =
      p.predicted_net
      - rentDelta / 30
      - staffDelta / 30
      + p.predicted_net * (revenuePct / 100)
      - (p.predicted_net > 0 ? 0 : Math.abs(p.predicted_net) * (inventoryPct / 100))
    return { ...p, simulated_net: adjustedNet }
  })

  // Compute simulated cumulative
  let runBal = currentBalance
  const chartData = simulatedPredictions.map((p, i) => {
    const origCum  = p.cumulative_balance
    runBal += p.simulated_net
    return {
      date: p.date.slice(5),
      original: origCum,
      simulated: Math.round(runBal),
    }
  })

  const hasChange = rentDelta || staffDelta || inventoryPct || revenuePct

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <SlidersHorizontal size={16} color="#2563eb" />
        <span style={{ fontWeight: 600, fontSize: 13 }}>Scenario Simulator</span>
        {hasChange && (
          <button
            className="btn btn-outline btn-sm"
            onClick={() => { setRentDelta(0); setStaffDelta(0); setInventoryPct(0); setRevenuePct(0) }}
          >
            Reset
          </button>
        )}
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <SliderInput
          label="Extra monthly rent (₹)"
          value={rentDelta}
          onChange={setRentDelta}
          min={-50000} max={100000} step={1000}
          format={v => v >= 0 ? `+₹${v.toLocaleString()}` : `-₹${Math.abs(v).toLocaleString()}`}
          color={rentDelta > 0 ? '#dc2626' : '#16a34a'}
        />
        <SliderInput
          label="Extra monthly staff wages (₹)"
          value={staffDelta}
          onChange={setStaffDelta}
          min={-100000} max={200000} step={5000}
          format={v => v >= 0 ? `+₹${v.toLocaleString()}` : `-₹${Math.abs(v).toLocaleString()}`}
          color={staffDelta > 0 ? '#dc2626' : '#16a34a'}
        />
        <SliderInput
          label="Revenue change (%)"
          value={revenuePct}
          onChange={setRevenuePct}
          min={-50} max={100} step={5}
          format={v => `${v >= 0 ? '+' : ''}${v}%`}
          color={revenuePct >= 0 ? '#16a34a' : '#dc2626'}
        />
        <SliderInput
          label="Inventory cost change (%)"
          value={inventoryPct}
          onChange={setInventoryPct}
          min={-50} max={100} step={5}
          format={v => `${v >= 0 ? '+' : ''}${v}%`}
          color={inventoryPct <= 0 ? '#16a34a' : '#dc2626'}
        />
      </div>

      {predictions.length > 0 && (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData.filter((_, i) => i % 2 === 0)}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
            <YAxis tickFormatter={fmt} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={60} />
            <Tooltip formatter={(v) => fmt(v)} />
            <Legend iconType="line" wrapperStyle={{ fontSize: 12 }} />
            <Line type="monotone" dataKey="original"  stroke="#94a3b8" strokeDasharray="4 2" dot={false} name="Original" />
            <Line type="monotone" dataKey="simulated" stroke="#2563eb" strokeWidth={2} dot={false} name="Simulated" />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

function SliderInput({ label, value, onChange, min, max, step, format, color }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <label style={{ margin: 0 }}>{label}</label>
        <span style={{ fontSize: 12, fontWeight: 600, color }}>{format(value)}</span>
      </div>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        style={{
          appearance: 'none', width: '100%', height: 4,
          background: `linear-gradient(to right, ${color} ${((value-min)/(max-min))*100}%, #e2e8f0 0)`,
          borderRadius: 2, border: 'none', outline: 'none', padding: 0, cursor: 'pointer',
        }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#94a3b8', marginTop: 3 }}>
        <span>{format(min)}</span><span>{format(max)}</span>
      </div>
    </div>
  )
}
