import { useState, useRef } from 'react'
import { Upload, CheckCircle, AlertCircle, X } from 'lucide-react'
import { uploadCSV } from '../api/client'
import toast from 'react-hot-toast'

export default function CSVUpload({ businessId, onDone }) {
  const [dragging, setDragging]   = useState(false)
  const [file, setFile]           = useState(null)
  const [result, setResult]       = useState(null)
  const [loading, setLoading]     = useState(false)
  const inputRef                  = useRef()

  const handleFile = (f) => {
    if (!f || !f.name.endsWith('.csv')) {
      toast.error('Please upload a .csv file')
      return
    }
    setFile(f)
    setResult(null)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    try {
      const res = await uploadCSV(businessId, file)
      setResult(res)
      toast.success(`Imported ${res.imported} transactions!`)
      onDone?.()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current.click()}
        style={{
          border: `2px dashed ${dragging ? '#2563eb' : '#cbd5e1'}`,
          borderRadius: 8,
          padding: '32px 24px',
          textAlign: 'center',
          cursor: 'pointer',
          background: dragging ? '#eff6ff' : '#f8fafc',
          transition: 'all .15s',
        }}
      >
        <Upload size={28} color={dragging ? '#2563eb' : '#94a3b8'} style={{ margin: '0 auto 8px' }} />
        {file ? (
          <div>
            <div style={{ fontWeight: 500, color: '#1e293b' }}>{file.name}</div>
            <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
              {(file.size / 1024).toFixed(1)} KB — click to change
            </div>
          </div>
        ) : (
          <div>
            <div style={{ fontWeight: 500, color: '#334155' }}>Drop your CSV here or click to browse</div>
            <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
              Columns auto-detected: Date, Amount, Type, Description
            </div>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          style={{ display: 'none' }}
          onChange={e => handleFile(e.target.files[0])}
        />
      </div>

      {/* CSV format hint */}
      <div style={{ marginTop: 12, padding: 10, background: '#f1f5f9', borderRadius: 6, fontSize: 12 }}>
        <strong>Supported column names:</strong><br />
        Date/date/timestamp · Amount/amount/value · Type/flow_type/direction · Description/note
        <br /><br />
        <strong>Example row:</strong> <code>2024-03-15, 1200, OUTFLOW, Vegetable purchase</code>
      </div>

      {file && !result && (
        <button
          className="btn btn-primary"
          style={{ marginTop: 14, width: '100%', justifyContent: 'center' }}
          onClick={handleUpload}
          disabled={loading}
        >
          {loading ? <><span className="spinner" style={{width:14,height:14}} /> Uploading...</> : <>
            <Upload size={14} /> Upload & Import
          </>}
        </button>
      )}

      {/* Result summary */}
      {result && (
        <div style={{ marginTop: 14 }}>
          <div className={`alert ${result.failed === 0 ? 'alert-success' : 'alert-warning'}`}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {result.failed === 0
                ? <CheckCircle size={16} />
                : <AlertCircle size={16} />}
              <strong>
                {result.imported} imported · {result.failed} failed · {result.total_rows} total rows
              </strong>
            </div>
            {result.errors.length > 0 && (
              <ul style={{ marginTop: 8, paddingLeft: 20, fontSize: 12 }}>
                {result.errors.slice(0, 5).map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            )}
          </div>
          <button
            className="btn btn-outline btn-sm"
            style={{ marginTop: 8 }}
            onClick={() => { setFile(null); setResult(null) }}
          >
            <X size={12} /> Clear
          </button>
        </div>
      )}
    </div>
  )
}