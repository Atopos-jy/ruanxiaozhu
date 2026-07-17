import type { TokenResponse, User } from '../types/auth'

const API_BASE = 'http://127.0.0.1:8000'
const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const CURRENT_USER_KEY = 'current_user'

export function getApiError(data: unknown, fallback: string) {
  if (typeof data === 'object' && data !== null && 'detail' in data && typeof data.detail === 'string') return data.detail
  return fallback
}

export function getTokenExpiresAt(token: string) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return typeof payload.exp === 'number' ? payload.exp * 1000 : 0
  } catch {
    return 0
  }
}

export function getStoredAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function saveTokens(data: TokenResponse) {
  localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token)
  localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token)
  localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(data.user))
}

export function clearStoredSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(CURRENT_USER_KEY)
}

export async function refreshSession(): Promise<User> {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
  if (!refreshToken) throw new Error('登录已过期')
  const response = await fetch(`${API_BASE}/api/auth/refresh`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: refreshToken }),
  })
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(getApiError(data, '登录已过期'))
  saveTokens(data as TokenResponse)
  return (data as TokenResponse).user
}

export async function logout() {
  const accessToken = getStoredAccessToken()
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
  await fetch(`${API_BASE}/api/auth/logout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}) },
    body: JSON.stringify({ refresh_token: refreshToken }),
  }).catch(() => undefined)
  clearStoredSession()
}
