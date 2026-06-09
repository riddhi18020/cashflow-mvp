export default function StatCard({ label, value, sub, color = 'blue', icon }) {
  const colors = {
    blue:   { bg: '#eff6ff', text: '#2563eb' },
    green:  { bg: '#f0fdf4', text: '#16a34a' },
    red:    { bg: '#fef2f2', text: '#dc2626' },
    yellow: { bg: '#fffbeb', text: '#d97706' },
    gray:   { bg: '#f1f5f9', text: '#475569' },
  }
  const c = colors[color] || colors.blue

  return (
    <div className="card" style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
      {icon && (
        <div style={{
          width: 40, height: 40, borderRadius: 8,
          background: c.bg, color: c.text,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0, fontSize: 18,
        }}>
          {icon}
        </div>
      )}
      <div>
        <div style={{ fontSize: 12, color: 'var(--gray-500)', fontWeight: 500 }}>{label}</div>
        <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--gray-900)', marginTop: 2 }}>{value}</div>
        {sub && <div style={{ fontSize: 11, color: 'var(--gray-500)', marginTop: 2 }}>{sub}</div>}
      </div>
    </div>
  )
}