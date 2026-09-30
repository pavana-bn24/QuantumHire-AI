import { Navigate, Route, Routes } from 'react-router-dom'

import AppLayout from './components/layout/AppLayout.jsx'
import { useAuth } from './context/AuthContext.jsx'
import CandidateDetail from './pages/CandidateDetail.jsx'
import Candidates from './pages/Candidates.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Login from './pages/Login.jsx'
import NotFound from './pages/NotFound.jsx'
import Roles from './pages/Roles.jsx'

function RequireAuth({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/roles" element={<Roles />} />
        <Route path="/candidates" element={<Candidates />} />
        <Route path="/candidates/:candidateId" element={<CandidateDetail />} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
