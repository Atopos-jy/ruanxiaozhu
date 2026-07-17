import { useEffect, useState } from 'react'
import { ConfigProvider } from 'antd'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './layouts/AppLayout'
import { clearStoredSession, getTokenExpiresAt, getStoredAccessToken, refreshSession } from './lib/auth'
import { AuthPage } from './pages/AuthPage'
import { AiManagerPage } from './pages/AiManagerPage'
import { EmptyPage } from './pages/EmptyPage'
import type { User } from './types/auth'

const REFRESH_BEFORE_EXPIRY_MS = 3 * 60 * 1000

function App() {
  const [user, setUser] = useState<User | null>(null)
  const [checkingSession, setCheckingSession] = useState(true)

  useEffect(() => {
    void (async () => {
      const accessToken = getStoredAccessToken()
      if (!accessToken) {
        setCheckingSession(false)
        return
      }
      try {
        const response = await fetch('http://127.0.0.1:8000/api/auth/me', { headers: { Authorization: `Bearer ${accessToken}` } })
        if (!response.ok) throw new Error('access token expired')
        setUser(await response.json() as User)
      } catch {
        try {
          setUser(await refreshSession())
        } catch {
          clearStoredSession()
        }
      } finally {
        setCheckingSession(false)
      }
    })()
  }, [])

  useEffect(() => {
    if (!user) return
    const accessToken = getStoredAccessToken()
    if (!accessToken) return
    const delay = Math.max(0, getTokenExpiresAt(accessToken) - Date.now() - REFRESH_BEFORE_EXPIRY_MS)
    const timer = window.setTimeout(() => {
      void refreshSession().then(setUser).catch(() => {
        clearStoredSession()
        setUser(null)
      })
    }, delay)
    return () => window.clearTimeout(timer)
  }, [user])

  if (checkingSession) return <div className="grid h-screen place-items-center bg-slate-50 text-sm text-slate-500">正在检查登录状态…</div>

  return <ConfigProvider theme={{ token: { colorPrimary: '#4f6cff', borderRadius: 10, fontFamily: 'Microsoft YaHei, PingFang SC, Arial, sans-serif' } }}>
    <BrowserRouter>
      {user ? <Routes>
        <Route element={<AppLayout user={user} onLogout={() => setUser(null)} />}>
          <Route path="/robot/chat" element={<AiManagerPage />} />
          <Route path="/app" element={<EmptyPage />} />
          <Route path="/document" element={<EmptyPage />} />
          <Route path="/robot/knowledge-diagnosis" element={<EmptyPage />} />
          <Route path="/robot/sales-expert" element={<EmptyPage />} />
          <Route path="*" element={<Navigate to="/app" replace />} />
        </Route>
      </Routes> : <Routes>
        <Route path="*" element={<AuthPage onAuthenticated={setUser} />} />
      </Routes>}
    </BrowserRouter>
  </ConfigProvider>
}

export default App
