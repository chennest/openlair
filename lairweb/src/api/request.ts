// 通用请求封装 —— 与真实后端统一信封契约 { code, message, data } 严格对齐
// - 自动附加 Authorization: Bearer <token>（模拟前端 axios 拦截器）
// - code !== 200 抛 ApiError（message 为后端返回的人类可读错误）
// - 401 统一清理登录态并跳转 /login（auth 公开接口除外，避免登录失败死循环）

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const TOKEN_KEY = 'openlair_token'
const USER_KEY = 'openlair_user'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export function getUser(): unknown | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function setUser(user: unknown | null) {
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
  else localStorage.removeItem(USER_KEY)
}

/** 这些接口的 401 属于正常业务错误（如密码错误），不触发跳登录 */
const AUTH_PUBLIC_PATHS = ['/api/auth/login', '/api/auth/register']

interface Envelope<T> {
  code: number
  message: string
  data: T
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(url, { ...options, headers })

  let envelope: Envelope<T> | null = null
  try {
    envelope = (await res.json()) as Envelope<T>
  } catch {
    envelope = null
  }

  const code = envelope && typeof envelope.code === 'number' ? envelope.code : res.status
  if (code !== 200) {
    const message = envelope?.message || `请求失败 HTTP ${res.status}`
    if (code === 401 && !AUTH_PUBLIC_PATHS.some((p) => url.startsWith(p))) {
      setToken(null)
      setUser(null)
      if (!window.location.pathname.startsWith('/login')) window.location.href = '/login'
    }
    throw new ApiError(code, message)
  }
  return envelope!.data as T
}

export const get = <T,>(url: string) => request<T>(url)

export const post = <T,>(url: string, body: unknown) =>
  request<T>(url, { method: 'POST', body: JSON.stringify(body) })

export const put = <T,>(url: string, body: unknown) =>
  request<T>(url, { method: 'PUT', body: JSON.stringify(body) })

export const del = <T,>(url: string) => request<T>(url, { method: 'DELETE' })
