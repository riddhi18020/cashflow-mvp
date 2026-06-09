import { useState } from 'react'
import { MessageSquare, Smartphone, Upload } from 'lucide-react'
import { ingestSMS, ingestWhatsApp } from '../api/client'
import CSVUpload from '../components/CSVUpload'
import toast from 'react-hot-toast'

const TABS = [
  { id: 'whatsapp', label: 'WhatsApp',  icon: MessageSquare },
  { id: 'sms',      label: 'SMS / UPI', icon: Smartphone },
  { id: 'csv',      label: 'CSV Upload', icon: Upload },
]

export default function IngestPage({ activeBiz }) {
  const [tab, setTab]         = useState('whatsapp')
  const [wa, setWa]           = useState('')
  const [sms, setSms]         = useState('')
  const [loading, setLoading] = useState(false)
  const [lastResult, setLastResult] = useState(null)

  if (!activeBiz) return (
    <div className="empty" style={{ padding: 80 }}>
      <div className="empty-icon">📨</div>
      <div>Select a business first</div>
    </div>
  )

  const handleWA = async () => {
    if (!wa.trim()) return
    setLoading(true)
    try {
      const r = await ingestWhatsApp(activeBiz.id, wa.trim())
      if (r.success) {
        toast.success(`Logged: ₹${r.transaction.amount} ${r.transaction.flow_type}`)
        setLastResult(r.transaction)
        setWa('')
      } else {
        toast.error(r.error)
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSMS = async () => {
    if (!sms.trim()) return
    setLoading(true)
    try {
      const r = await ingestSMS(activeBiz.id, sms.trim())
      if (r.success) {
        toast.success(`Parsed: ₹${r.transaction.amount} ${r.transaction.flow_type}`)
        setLastResult(r.transaction)
        setSms('')
      } else {
        toast.error(r.error)
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: 28, maxWidth: 700 }}>
      <div className="page-header">
        <div className="page-title">Add Transaction Data</div>
        <div className="page-sub">{activeBiz.name} · {activeBiz.city}</div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, background: '#f1f5f9', padding: 4, borderRadius: 8, width: 'fit-content' }}>
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => { setTab(id); setLastResult(null) }}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 14px', borderRadius: 6, border: 'none',
              fontSize: 13, fontWeight: 500, cursor: 'pointer',
              background: tab === id ? 'white' : 'transparent',
              color: tab === id ? '#1e293b' : '#64748b',
              boxShadow: tab === id ? '0 1px 3px rgba(0,0,0,.08)' : 'none',
              transition: 'all .12s',
            }}
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      <div className="card">
        {/* WhatsApp tab */}
        {tab === 'whatsapp' && (
          <div>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Log via WhatsApp-style message</div>
            <p style={{ fontSize: 13, color: '#64748b', marginBottom: 16 }}>
              Type a natural language message the way you'd send it on WhatsApp. Hindi supported.
            </p>
            <div style={{ marginBottom: 16, padding: 12, background: '#f8fafc', borderRadius: 8, fontSize: 12 }}>
              <strong>Examples:</strong><br />
              • <code>spent 1200 on vegetables</code><br />
              • <code>received 5000 from customer</code><br />
              • <code>paid 800 rent</code><br />
              • <code>mila 2000 aaj</code> (Hindi)<br />
              • <code>sale 3500 today</code>
            </div>
            <label>Your message</label>
            <textarea
              rows={3}
              value={wa}
              onChange={e => setWa(e.target.value)}
              placeholder="spent 800 on vegetable stock today"
              style={{ marginBottom: 12, resize: 'vertical' }}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleWA())}
            />
            <button className="btn btn-primary" onClick={handleWA} disabled={loading || !wa.trim()}>
              <MessageSquare size={14} />
              {loading ? 'Parsing…' : 'Log Transaction'}
            </button>
          </div>
        )}

        {/* SMS tab */}
        {tab === 'sms' && (
          <div>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Paste Banking SMS / UPI Alert</div>
            <p style={{ fontSize: 13, color: '#64748b', marginBottom: 16 }}>
              Copy-paste a transaction notification from your bank (HDFC, SBI, ICICI, Paytm, PhonePe, etc.)
            </p>
            <div style={{ marginBottom: 16, padding: 12, background: '#f8fafc', borderRadius: 8, fontSize: 12 }}>
              <strong>Examples:</strong><br />
              • <code>Rs.1200.00 debited from A/c XX1234 on 15-Mar-24</code><br />
              • <code>INR 5000 credited to your SBI account</code><br />
              • <code>UPI/CR/123456789/2500.00 PaymentFrom:Ramesh</code>
            </div>
            <label>SMS text</label>
            <textarea
              rows={4}
              value={sms}
              onChange={e => setSms(e.target.value)}
              placeholder="Paste your banking SMS here..."
              style={{ marginBottom: 12, resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }}
            />
            <button className="btn btn-primary" onClick={handleSMS} disabled={loading || !sms.trim()}>
              <Smartphone size={14} />
              {loading ? 'Parsing…' : 'Parse & Log'}
            </button>
          </div>
        )}

        {/* CSV tab */}
        {tab === 'csv' && (
          <div>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>Upload CSV File</div>
            <p style={{ fontSize: 13, color: '#64748b', marginBottom: 16 }}>
              Upload a spreadsheet of historical transactions. Column names are detected automatically.
            </p>
            <CSVUpload businessId={activeBiz.id} onDone={() => setLastResult({ csv: true })} />
          </div>
        )}

        {/* Success result */}
        {lastResult && !lastResult.csv && (
          <div className="alert alert-success" style={{ marginTop: 16 }}>
            ✅ Logged: <strong>₹{Number(lastResult.amount).toLocaleString('en-IN')}</strong>
            {' · '}{lastResult.flow_type}
            {' · '}{lastResult.category}
          </div>
        )}
      </div>
    </div>
  )
}
