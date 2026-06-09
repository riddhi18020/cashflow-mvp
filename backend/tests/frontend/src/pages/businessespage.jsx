import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Trash2, ArrowRight } from 'lucide-react'
import { getBusinesses, createBusiness, deleteBusiness } from '../api/client'
import toast from 'react-hot-toast'

const TYPE_COLORS = {
  micro_vendor: 'badge-yellow',
  boutique:     'badge-blue',
  superstore:   'badge-green',
}

export default function BusinessesPage({ onSelect }) {
  const [businesses, setBusinesses] = useState([])
  const [loading, setLoading]       = useState(true)
  const [creating, setCreating]     = useState(false)
  const [form, setForm]             = useState({
    name: '', owner_phone: '', business_type: 'micro_vendor', city: 'Surat',
  })
  const nav = useNavigate()

  const load = async () => {
    try {
      const data = await getBusinesses()
      setBusinesses(data)
    } catch {
      toast.error('Could not load businesses')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) return toast.error('Name is required')
    setCreating(true)
    try {
      await createBusiness(form)
      toast.success('Business created!')
      setForm({ name: '', owner_phone: '', business_type: 'micro_vendor', city: 'Surat' })
      load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (id, name) => {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return
    try {
      await deleteBusiness(id)
      toast.success('Deleted')
      load()
    } catch {
      toast.error('Delete failed')
    }
  }

  const handleSelect = (biz) => {
    onSelect(biz)
    nav('/dashboard')
  }

  return (
    <div style={{ padding: 28, maxWidth: 900 }}>
      <div className="page-header">
        <div className="page-title">Businesses</div>
        <div className="page-sub">Select a business to view its dashboard and forecast</div>
      </div>

      {/* Create form */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ fontWeight: 600, marginBottom: 16, fontSize: 14 }}>Register New Business</div>
        <form onSubmit={handleCreate}>
          <div className="grid-2" style={{ marginBottom: 12 }}>
            <div>
              <label>Business Name *</label>
              <input
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Ramesh Golgappa Stall"
              />
            </div>
            <div>
              <label>Owner Phone (for WhatsApp)</label>
              <input
                value={form.owner_phone}
                onChange={e => setForm(f => ({ ...f, owner_phone: e.target.value }))}
                placeholder="+919876543210"
              />
            </div>
            <div>
              <label>Business Type</label>
              <select value={form.business_type} onChange={e => setForm(f => ({ ...f, business_type: e.target.value }))}>
                <option value="micro_vendor">Micro Vendor (street stall)</option>
                <option value="boutique">Boutique / Small Shop</option>
                <option value="superstore">Superstore / ERP-integrated</option>
              </select>
            </div>
            <div>
              <label>City</label>
              <input
                value={form.city}
                onChange={e => setForm(f => ({ ...f, city: e.target.value }))}
                placeholder="e.g. Surat"
              />
            </div>
          </div>
          <button type="submit" className="btn btn-primary" disabled={creating}>
            <Plus size={14} /> {creating ? 'Creating…' : 'Create Business'}
          </button>
        </form>
      </div>

      {/* Business list */}
      {loading ? (
        <div className="loading"><div className="spinner" /> Loading…</div>
      ) : businesses.length === 0 ? (
        <div className="empty">
          <div className="empty-icon">🏪</div>
          <div>No businesses yet. Create one above or run <code>python scripts/seed_data.py</code> to load sample data.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {businesses.map(biz => (
            <div key={biz.id} className="card" style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 8,
                  background: '#f1f5f9', display: 'flex', alignItems: 'center',
                  justifyContent: 'center', fontSize: 20,
                }}>
                  {biz.business_type === 'micro_vendor' ? '🛒'
                    : biz.business_type === 'boutique' ? '🏪' : '🏬'}
                </div>
                <div>
                  <div style={{ fontWeight: 600, color: '#1e293b' }}>{biz.name}</div>
                  <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
                    {biz.city} · {biz.owner_phone || 'No phone'}
                  </div>
                </div>
                <span className={`badge ${TYPE_COLORS[biz.business_type] || 'badge-blue'}`}>
                  {biz.business_type}
                </span>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-primary btn-sm" onClick={() => handleSelect(biz)}>
                  Open <ArrowRight size={13} />
                </button>
                <button className="btn btn-outline btn-sm" onClick={() => handleDelete(biz.id, biz.name)}>
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}