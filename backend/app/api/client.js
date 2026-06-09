import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// ── Businesses ─────────────────────────────────────────────────────────────

export const getBusinesses   = ()           => api.get('/businesses/').then(r => r.data)
export const getBusiness     = (id)         => api.get(`/businesses/${id}`).then(r => r.data)
export const createBusiness  = (data)       => api.post('/businesses/', data).then(r => r.data)
export const deleteBusiness  = (id)         => api.delete(`/businesses/${id}`)

// ── Transactions ───────────────────────────────────────────────────────────

export const getTransactions = (bizId, params = {}) =>
  api.get(`/businesses/${bizId}/transactions`, { params }).then(r => r.data)

export const addTransaction  = (bizId, data) =>
  api.post(`/businesses/${bizId}/transactions`, data).then(r => r.data)

export const ingestSMS       = (bizId, raw_sms) =>
  api.post(`/businesses/${bizId}/transactions/sms`, { raw_sms }).then(r => r.data)

export const ingestWhatsApp  = (bizId, message) =>
  api.post(`/businesses/${bizId}/transactions/whatsapp`, { message }).then(r => r.data)

export const uploadCSV       = (bizId, file, columnMap = null) => {
  const form = new FormData()
  form.append('file', file)
  if (columnMap) form.append('column_map_json', JSON.stringify(columnMap))
  return api.post(`/businesses/${bizId}/transactions/csv`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

export const deleteTransaction = (bizId, txId) =>
  api.delete(`/businesses/${bizId}/transactions/${txId}`)

// ── Forecast ───────────────────────────────────────────────────────────────

export const runForecast     = (bizId, params = {}) =>
  api.post(`/businesses/${bizId}/forecast`, params).then(r => r.data)

export const getLatestForecast = (bizId) =>
  api.get(`/businesses/${bizId}/forecast`).then(r => r.data)

export const getDashboard    = (bizId) =>
  api.get(`/businesses/${bizId}/dashboard`).then(r => r.data)