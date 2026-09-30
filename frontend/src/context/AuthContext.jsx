import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { getCurrentUser, login as loginRequest } from '../api/quantumhire.js'

const SESSION_KEY = 'quantumhire.session'
const TOKEN_KEY = 'quantumhire.token'

const AuthContext = createContext(null)

const readSession = () => {
  try {
    const raw = window.localStorage.getItem(SESSION_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

/**
 * Real JWT session: `POST /api/auth/login` returns a bearer token which is
 * stored locally and attached to every API call (see `api/client.js`).
 * The token is re-validated against `/api/auth/me` on mount.
 */
export function AuthProvider({ children }) {
  const [session, setSession] = useState(readSession)
  const [checking, setChecking] = useState(Boolean(readSession()))

  useEffect(() => {
    if (!session?.token) {
      setChecking(false)
      return undefined
    }

    let cancelled = false
    getCurrentUser()
      .then((user) => {
        if (cancelled) return
        setSession((current) => ({ ...current, user }))
      })
      .catch(() => {
        // Expired/revoked token: drop the session rather than half-sign-in.
        if (cancelled) return
        window.localStorage.removeItem(SESSION_KEY)
        window.localStorage.removeItem(TOKEN_KEY)
        setSession(null)
      })
      .finally(() => {
        if (!cancelled) setChecking(false)
      })

    return () => {
      cancelled = true
    }
  }, [session?.token])

  const login = useCallback(async ({ email, password }) => {
    const data = await loginRequest({ email: email.trim(), password })
    const next = {
      token: data.access_token,
      user: data.user ?? { email },
      name: data.user?.name ?? email.split('@')[0],
      role: data.user?.role ?? 'recruiter',
      signedInAt: new Date().toISOString(),
    }
    window.localStorage.setItem(TOKEN_KEY, next.token)
    window.localStorage.setItem(SESSION_KEY, JSON.stringify(next))
    setSession(next)
    return next
  }, [])

  const logout = useCallback(() => {
    window.localStorage.removeItem(TOKEN_KEY)
    window.localStorage.removeItem(SESSION_KEY)
    setSession(null)
  }, [])

  const value = useMemo(
    () => ({ session, isAuthenticated: Boolean(session?.token), checking, login, logout }),
    [session, checking, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside an <AuthProvider>')
  }
  return context
}
