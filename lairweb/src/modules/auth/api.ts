import { get, post } from '../../api/request'

export interface AuthUser {
  id: number
  name: string
  email: string
  avatarColor: string
  createdAt: string
}

export interface LoginInput {
  email: string
  password: string
}

export interface RegisterInput {
  name: string
  email: string
  password: string
}

export interface AuthResult {
  token: string
  user: AuthUser
}

export const authApi = {
  register: (input: RegisterInput) => post<AuthResult>('/api/auth/register', input),
  login: (input: LoginInput) => post<AuthResult>('/api/auth/login', input),
  logout: () => post<{ ok: boolean }>('/api/auth/logout', {}),
  me: () => get<AuthUser>('/api/auth/me'),
}
