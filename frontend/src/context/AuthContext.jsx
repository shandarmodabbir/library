import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api, getToken, setToken } from '../api/client.js'

const AuthContext = createContext(null)

function decodeUserId(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return payload.user_id ?? null
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadUser = useCallback(async (token) => {
    const userId = decodeUserId(token)
    if (!userId) {
      setUser(null)
      return
    }
    try {
      const u = await api.getUser(userId)
      setUser(u)
    } catch {
      setToken(null)
      setUser(null)
    }
  }, [])

  useEffect(() => {
    const token = getToken()
    if (token) {
      loadUser(token).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [loadUser])

  const login = async (email, password) => {
    const { access_token } = await api.login(email, password)
    setToken(access_token)
    await loadUser(access_token)
  }

  const register = async (email, password) => {
    await api.register(email, password)
    await login(email, password)
  }

  const logout = () => {
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
