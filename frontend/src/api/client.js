import axios from 'axios'

// Same-origin API calls use Vite's /api proxy in development and can be served
// behind a single-origin reverse proxy in production. Set VITE_API_BASE_URL only
// when the API is intentionally hosted on a separate origin.
const baseURL = import.meta.env.VITE_API_BASE_URL ?? ''
const TOKEN_KEY = 'quantumhire.token'

/** Read the stored JWT (set by AuthContext after a successful login). */
export const getToken = () => {
  try {
    return window.localStorage.getItem(TOKEN_KEY) ?? null
  } catch {
    return null
  }
}

/** Shared axios instance - all API calls go through this. */
export const apiClient = axios.create({
  baseURL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// Attach the bearer token to every request (mutation endpoints require it).
apiClient.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Normalise API errors into a plain Error with a readable message.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error?.response?.data?.detail
    const message =
      (typeof detail === 'string' && detail) ||
      error?.message ||
      'Unexpected API error'
    return Promise.reject(new Error(message))
  },
)

export const endpoints = {
  health: '/api/health',
  databaseHealth: '/api/health/db',
  roles: '/api/roles',
  candidates: '/api/candidates',
  resumeUpload: '/api/candidates/upload',
  dashboardSummary: '/api/dashboard/summary',
  login: '/api/auth/login',
  me: '/api/auth/me',
  knowledge: '/api/knowledge/search',
  agentTools: '/api/agents/tools',
}

export default apiClient
