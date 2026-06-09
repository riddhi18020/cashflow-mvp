import { NavLink } from 'react-router-dom'
import { LayoutDashboard, ArrowLeftRight, TrendingUp, MessageSquare, Building2 } from 'lucide-react'

const NAV = [
  { to: '/',              icon: Building2,       label: 'Businesses'    },
  { to: '/dashboard',     icon: LayoutDashboard, label: 'Dashboard'     },
  { to: '/transactions',  icon: ArrowLeftRight,  label: 'Transactions'  },
  { to: '/forecast',      icon: TrendingUp,      label: 'Forecast'      },
  { to: '/ingest',        icon: MessageSquare,   label: 'Add Data'      },
]

export default function Sidebar({ activeBiz }) {
  return (
    <aside style={{
      width: 220, minHeight: '100vh', background: 'white',
      borderRight: '1px solid #e2e8f0', padding: '20px 0',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* Logo */}
      <div style={{ padding: '0 20px 24px' }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: '#1e293b' }}>
          💸 CashFlow
        </div>
        <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>Forecasting MVP</div>
      </div>

      {/* Active business */}
      {activeBiz && (
        <div style={{
          margin: '0 12px 16px', padding: '10px 12px',
          background: '#eff6ff', borderRadius: 8,
          fontSize: 12, color: '#1e40af',
        }}>
          <div style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
                        letterSpacing: '.05em', marginBottom: 2 }}>Active business</div>
          <div style={{ fontWeight: 500 }}>{activeBiz.name}</div>
          <div style={{ color: '#3b82f6', marginTop: 1 }}>{activeBiz.city}</div>
        </div>
      )}

      {/* Nav links */}
      <nav style={{ flex: 1 }}>
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '9px 20px', fontSize: 13, fontWeight: 500,
              textDecoration: 'none',
              color: isActive ? '#2563eb' : '#475569',
              background: isActive ? '#eff6ff' : 'transparent',
              borderRight: isActive ? '2px solid #2563eb' : '2px solid transparent',
              transition: 'all .12s',
            })}
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: '16px 20px', fontSize: 11, color: '#94a3b8' }}>
        API docs: <a href="http://localhost:8000/docs" target="_blank"
          style={{ color: '#2563eb' }}>localhost:8000/docs</a>
      </div>
    </aside>
  )
}