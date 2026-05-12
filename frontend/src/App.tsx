import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import ContractDetail from './pages/ContractDetail'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/contracts/:id" element={<ContractDetail />} />
    </Routes>
  )
}
