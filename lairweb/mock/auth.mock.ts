import { defineMock } from 'vite-plugin-mock-dev-server'
import {
  store,
  type User,
  nextId,
  respond,
  ok,
  err,
  guard,
  signToken,
  revokeToken,
  hashPassword,
  verifyPassword,
} from './store'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const AVATAR_COLORS = ['#0071e3', '#30d158', '#ff6b00', '#5e5ce6', '#ff375f', '#1d9bf0', '#ff9f0a']

/** 用户 DTO：绝不返回 passwordHash（与真实后端一致） */
interface AuthUserDTO {
  id: string
  name: string
  email: string
  avatarColor: string
  createdAt: string
}

function toDTO(u: User): AuthUserDTO {
  return { id: u.id, name: u.name, email: u.email ?? '', avatarColor: u.avatarColor, createdAt: u.createdAt }
}

export default {
  // 注册：{ name, email, password } → 成功自动登录（返回 token）
  register: defineMock({
    url: '/api/auth/register',
    method: 'POST',
    response: respond((req) => {
      const { name, email, password } = req.body ?? {}
      if (typeof name !== 'string' || !name.trim() || name.trim().length > 20) return err(400, '昵称需为 1-20 个字符')
      if (typeof email !== 'string' || !EMAIL_RE.test(email.trim())) return err(400, '邮箱格式不正确')
      if (typeof password !== 'string' || password.length < 6 || password.length > 64) return err(400, '密码需为 6-64 位')
      const mail = email.trim().toLowerCase()
      if (store.users.some((u) => u.email === mail)) return err(409, '该邮箱已被注册')
      const u: User = {
        id: nextId(store.users),
        name: name.trim(),
        email: mail,
        passwordHash: hashPassword(password),
        avatarColor: AVATAR_COLORS[Math.floor(Math.random() * AVATAR_COLORS.length)],
        createdAt: new Date().toISOString(),
      }
      store.users.push(u)
      return ok({ token: signToken(u.id), user: toDTO(u) }, '注册成功')
    }),
  }),

  // 登录：{ email, password } → 校验通过发 token
  login: defineMock({
    url: '/api/auth/login',
    method: 'POST',
    response: respond((req) => {
      const { email, password } = req.body ?? {}
      if (typeof email !== 'string' || !email.trim()) return err(400, '请输入邮箱')
      if (typeof password !== 'string' || !password) return err(400, '请输入密码')
      const mail = email.trim().toLowerCase()
      const u = store.users.find((x) => x.email === mail)
      // 不区分「用户不存在」与「密码错误」，避免账号探测（与后端一致）
      if (!u?.passwordHash || !verifyPassword(password, u.passwordHash)) return err(401, '邮箱或密码错误')
      return ok({ token: signToken(u.id), user: toDTO(u) }, '登录成功')
    }),
  }),

  // 登出：当前 token 的 jti 进黑名单，立即失效
  logout: defineMock({
    url: '/api/auth/logout',
    method: 'POST',
    response: respond(
      guard((_req, auth) => {
        revokeToken(auth.jti)
        return ok({ ok: true }, '已退出登录')
      }),
    ),
  }),

  // 当前登录用户（刷新页面后用 token 恢复登录态）
  me: defineMock({
    url: '/api/auth/me',
    method: 'GET',
    response: respond(
      guard((_req, auth) => {
        const u = store.users.find((x) => x.id === auth.userId)
        if (!u) return err(401, '用户不存在')
        return ok(toDTO(u))
      }),
    ),
  }),
}
