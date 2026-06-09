import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Sidebar from './components/Sidebar.jsx'
import BusinessesPage from './pages/BusinessesPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import TransactionsPage from './pages/TransactionsPage.jsx'
import IngestPage from './pages/IngestPage.jsx'
import ForecastPage from './pages/ForecastPage.jsx'

export default function App() {
  const [activeBiz, setActiveBiz] = useState(null)

  return (
    <BrowserRouter>
      <Toaster position="top-right" toastOptions={{ duration: 3000 }} />
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        <Sidebar activeBiz={activeBiz} />
        <main style={{ flex: 1, overflowY: 'auto' }}>
          <Routes>
            <Route path="/"             element={<BusinessesPage onSelect={setActiveBiz} />} />
            <Route path="/dashboard"    element={<DashboardPage activeBiz={activeBiz} />} />
            <Route path="/transactions" element={<TransactionsPage activeBiz={activeBiz} />} />
            <Route path="/forecast"     element={<ForecastPage activeBiz={activeBiz} />} />
            <Route path="/ingest"       element={<IngestPage activeBiz={activeBiz} />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
