import { useState, useEffect } from 'react'
import { Plus, Trash2, RefreshCw } from 'lucide-react'
import { getTransactions, addTransaction, deleteTransaction } from '../api/client'
import toast from 'react-hot-toast'

const CATEGORIES = [
  'Revenue','Inventory','Utility','Rent','Staff_Wages',
  'Transport','Marketing','Food','Uncategorized',
]

export default function TransactionsPage({ activeBiz }) {
  const [txs, setTxs]       = useState([])
  const [total, setTotal]   = useState(0)
  const [loading, setLoading] = useState(true)
  const [days, setDays]     = useState(30)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm]     = useState({
    timestamp: new Date().toISOString().slice(0, 16),
    amount: '',
    flow_type: 'INFLOW',
    category: 'Revenue',
    description: '',
  })

  const load = async () => {
    if (!activeBiz) return
    setLoading(true)
    try {
      const d = await getTransactions(activeBiz.id, { days, limit: 200 })
      setTxs(d.transactions)
      setTotal(d.total)
    } catch {
      toast.error('Failed to load transactions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [activeBiz?.id, days])

  const handleAdd = async (e) => {
    e.preventDefault()
    if (!form.amount || isNaN(Number(form.amount))) return toast.error('Enter a valid amount')
    try {
      await addTransaction(activeBiz.id, { ...form, amount: Number(form.amount) })
      toast.success('Transaction added!')
      setShowForm(false)
      setForm({ timestamp: new Date().toISOString().slice(0,16), amount: '', flow_type: 'INFLOW', category: 'Revenue', description: '' })
      load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add')
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this transaction?')) return
    try {
      await deleteTransaction(activeBiz.id, id)
      toast.success('Deleted')
      load()
    } catch {
      toast.error('Delete failed')
    }
  }

  if (!activeBiz) return (
    <div className="empty" style={{ padding: 80 }}>
      <div className="empty-icon">↔️</div>
      <div>Select a business first</div>
    </div>
  )

  return (
    <div style={{ padding: 28 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <div className="page-title">Transactions</div>
          <div className="page-sub">{total} total · showing last {days} days</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <select value={days} onChange={e => setDays(Number(e.target.value))} style={{ width: 'auto' }}>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>All time</option>
          </select>
          <button className="btn btn-outline" onClick={load}>
            <RefreshCw size={13} />
          </button>
          <button className="btn btn-primary" onClick={() => setShowForm(v => !v)}>
            <Plus size={14} /> Add
          </button>
        </div>
      </div>

      {/* Add form */}
      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ fontWeight: 600, marginBottom: 14 }}>New Transaction</div>
          <form onSubmit={handleAdd}>
            <div className="grid-3" style={{ marginBottom: 12 }}>
              <div>
                <label>Date & Time</label>
                <input type="datetime-local" value={form.timestamp}
                  onChange={e => setForm(f => ({ ...f, timestamp: e.target.value }))} />
              </div>
              <div>
                <label>Amount (₹)</label>
                <input type="number" value={form.amount} min="0.01" step="0.01"
                  onChange={e => setForm(f => ({ ...f, amount: e.target.value }))}
                  placeholder="0.00" />
              </div>
              <div>
                <label>Type</label>
                <select value={form.flow_type} onChange={e => setForm(f => ({ ...f, flow_type: e.target.value }))}>
                  <option value="INFLOW">INFLOW (Revenue)</option>
                  <option value="OUTFLOW">OUTFLOW (Expense)</option>
                </select>
              </div>
              <div>
                <label>Category</label>
                <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}>
                  {CATEGORIES.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div style={{ gridColumn: 'span 2' }}>
                <label>Description</label>
                <input value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="Optional note" />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit" className="btn btn-primary btn-sm">Save</button>
              <button type="button" className="btn btn-outline btn-sm" onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      {/* Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div className="loading"><div className="spinner" /> Loading…</div>
        ) : txs.length === 0 ? (
          <div className="empty">
            <div className="empty-icon">📋</div>
            <div>No transactions found. Add one above or use the "Add Data" page to import.</div>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Amount</th>
                <th>Category</th>
                <th>Description</th>
                <th>Source</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {txs.map(tx => (
                <tr key={tx.id}>
                  <td style={{ color: '#64748b', fontSize: 12 }}>{tx.timestamp.slice(0, 16).replace('T', ' ')}</td>
                  <td>
                    <span className={`badge ${tx.flow_type === 'INFLOW' ? 'badge-green' : 'badge-red'}`}>
                      {tx.flow_type === 'INFLOW' ? '↑' : '↓'} {tx.flow_type}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600, color: tx.flow_type === 'INFLOW' ? '#16a34a' : '#dc2626' }}>
                    {tx.flow_type === 'INFLOW' ? '+' : '-'}₹{Number(tx.amount).toLocaleString('en-IN')}
                  </td>
                  <td><span className="badge badge-blue">{tx.category}</span></td>
                  <td style={{ color: '#64748b', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {tx.description || '—'}
                  </td>
                  <td style={{ fontSize: 11, color: '#94a3b8' }}>{tx.source}</td>
                  <td>
                    <button className="btn btn-outline btn-sm" onClick={() => handleDelete(tx.id)}>
                      <Trash2 size={12} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
