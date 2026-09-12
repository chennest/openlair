// 内存态 mock 数据层 —— 模拟真实数据库（表 + 查询）
// - 表结构与后续 FastAPI + SQLAlchemy 后端对齐：id / 外键 / 时间戳
// - 使用固定 seed 的伪随机，初始数据每次启动一致
// - 运行中增删改查直接改内存，重启即恢复初始数据
// - 通过 globalThis 共享：vite-plugin-mock-dev-server 对每个 mock 文件单独 esbuild
//   bundle，若用模块级变量，每个文件会得到独立实例（id 冲突 + 数据不互通）
import { createHash, createHmac, randomBytes, scryptSync, timingSafeEqual } from 'node:crypto'

// ---------- seedable 伪随机 (mulberry32) ----------
function mulberry32(seed: number) {
  let a = seed
  return function () {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// ══════════════════════════════════════════════════════════════
// 表结构（与后端 schema 对齐）
// ══════════════════════════════════════════════════════════════

/** categories 表：分类（id = 自增 int 主键，与 SQLAlchemy INTEGER PRIMARY KEY 对齐） */
export interface Category {
  id: number
  name: string
  type: '支出' | '收入'
  /** 排序权重（小在前） */
  sortOrder: number
  /** 系统默认分类（如「其他」），不可删除 */
  isDefault: boolean
  /** 归属用户（null = 系统预置；非空 = 该用户创建，可改删） */
  userId: number | null
  createdAt: string
}

/** users 表：用户（id = 自增 int；被邀请成员可以没有登录账号） */
export interface User {
  id: number
  name: string
  /** 登录邮箱（仅已注册账号有；被邀请的成员无账号时为空） */
  email?: string
  /** 密码哈希（模拟后端 passlib bcrypt，格式 scrypt$salt$hash；绝不返回给前端） */
  passwordHash?: string
  /** 头像底色（无图片，用色块 + 首字） */
  avatarColor: string
  createdAt: string
}

/** books 表：账本（个人 / 共享；「家庭」只是共享账本的一种场景） */
export interface Book {
  id: number
  name: string
  type: 'personal' | 'shared'
  createdAt: string
  /** 软删除：非空 = 在回收站（删除时间） */
  deletedAt?: string
}

/** book_members 表：账本成员关系 */
export interface BookMember {
  bookId: number
  userId: number
  role: 'owner' | 'editor'
  joinedAt: string
}

/** book 邀请码（独立于 book DTO，避免下发到账本列表泄漏给成员） */
export interface BookInvite {
  bookId: number
  /** 8 位大写字母数字（剔除 0/O/1/I/L） */
  code: string
}

/** transactions 表：交易流水（categoryId → categories.id，bookId → books.id，userId → users.id） */
export interface Transaction {
  id: number
  type: '支出' | '收入'
  categoryId: number
  bookId: number
  /** 记账人 */
  userId: number
  amount: number
  /** YYYY-MM-DD */
  date: string
  note: string
  createdAt: string
  updatedAt: string
}

/** budgets 表：月度预算（按账本隔离，month = 'YYYY-MM'） */
export interface Budget {
  id: number
  bookId: number
  month: string
  expenseLimit: number
  createdAt: string
  updatedAt: string
}

export interface TodoItem {
  id: number
  text: string
  quadrant: string
  done: boolean
  due: string
  createdAt: string
  updatedAt: string
}

export interface CalendarEvent {
  id: number
  title: string
  date: string
  time: string
  location: string
  done: boolean
  createdAt: string
  updatedAt: string
}

export interface Note {
  id: number
  title: string
  summary: string
  tags: string[]
  updatedAt: string
  createdAt: string
}

export interface Habit {
  id: number
  name: string
  streak: number
  done: boolean
  week: boolean[]
  createdAt: string
  updatedAt: string
}

/** days 表：倒数日 / 纪念日（repeat 决定后端如何展开下一次日期） */
export interface DayItem {
  id: number
  title: string
  emoji: string
  /** YYYY-MM-DD（重复时只取月/日展开） */
  date: string
  /** once 一次性 / yearly 每年 / monthly 每月 */
  repeat: 'once' | 'yearly' | 'monthly'
  pinned: boolean
  createdAt: string
  updatedAt: string
}

/** AI 助手会话 */
export interface AssistantSession {
  id: number
  title: string
  createdAt: string
  updatedAt: string
}

/** AI 助手消息 */
export interface AssistantMessage {
  id: number
  sessionId: number
  role: 'user' | 'assistant'
  type?: 'text' | 'confirm_request' | 'tool_result'
  content: string
  meta?: Record<string, unknown>
  createdAt: string
}

/** api_keys 表：用户 API Key（只存哈希，明文仅创建时返回一次；撤销即置 revokedAt） */
export interface ApiKey {
  id: number
  userId: number
  name: string
  keyHash: string
  prefix: string
  createdAt: string
  lastUsedAt?: string
  revokedAt?: string
}

// ---------- 常量 ----------
export const QUADRANTS = ['重要紧急', '重要不紧急', '紧急不重要', '不重要不紧急']
export const MONTH = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

// ---------- 共享运行时（globalThis） ----------
interface SharedRuntime {
  rand: () => number
  store: StoreShape | null
  /** 已注销的 JWT jti 黑名单（模拟后端 Redis 黑名单；重启即清空） */
  revokedJtis: Set<string>
}

export interface StoreShape {
  categories: Category[]
  transactions: Transaction[]
  budgets: Budget[]
  users: User[]
  books: Book[]
  bookMembers: BookMember[]
  bookInvites: BookInvite[]
  todos: TodoItem[]
  events: CalendarEvent[]
  notes: Note[]
  habits: Habit[]
  days: DayItem[]
  assistantSessions: AssistantSession[]
  assistantMessages: AssistantMessage[]
  apiKeys: ApiKey[]
}

const g = globalThis as unknown as { __openlair_mock__?: SharedRuntime }
if (!g.__openlair_mock__) {
  g.__openlair_mock__ = { rand: mulberry32(20260806), store: null, revokedJtis: new Set() }
}
const rt = g.__openlair_mock__
const rand = rt.rand

// ---------- 随机辅助 ----------
const pick = <T,>(arr: T[]): T => arr[Math.floor(rand() * arr.length)]
const integer = (min: number, max: number) => Math.floor(rand() * (max - min + 1)) + min
const float = (min: number, max: number, digits = 2) => Number((rand() * (max - min) + min).toFixed(digits))
const bool = () => rand() > 0.5
const pad = (n: number) => String(n).padStart(2, '0')
const date = (offsetDays = 0) => {
  const d = new Date(Date.now() + offsetDays * 86400000)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
/** YYYY-MM-DD 年份平移（生日/周年演示数据用） */
const shiftYear = (raw: string, dy: number) => `${Number(raw.slice(0, 4)) + dy}${raw.slice(4)}`
const nowISO = () => new Date().toISOString()

/** 自增主键：模拟 SQLAlchemy 自增 INTEGER PRIMARY KEY（新行 id = 当前最大 id + 1） */
export function nextId(rows: { id: number }[]): number {
  return rows.reduce((m, r) => Math.max(m, r.id), 0) + 1
}
const csentence = () => {
  const pool = ['推进周报整理', '预约下周会议', '整理报销发票', '完成季度复盘', '更新学习计划', '排查线上告警', '审阅合同条款', '参加技术分享', '优化部署脚本', '补充接口文档']
  return pick(pool)
}

// ---------- 初始数据 ----------
const NOTES = ['午饭', '地铁', '买书', '房租', '工资', '聚餐', '打车', '日用品', '电影票', '水电费']
const LOCATIONS = ['公司', '家', '健身房', '咖啡厅', '线上']
const DUES = ['今天', '明天', '本周', '下月', '无期限']
const TAGS = ['工作', '学习', '生活', '灵感', '会议', '备忘']
const HABIT_NAMES = ['早起打卡', '背单词', '跑步 3km', '阅读 30 分钟', '冥想', '记账']

// ══════════════════════════════════════════════════════════════
// 安全层（模拟真实后端 FastAPI security）
// - JWT：HS256 真实签名（HMAC-SHA256），claims 含 sub/iat/exp/jti，与 python-jose 产出格式一致
// - 密码：scrypt 加盐哈希（模拟 passlib bcrypt；格式 scrypt$salt$hash）
// - 登出：jti 进黑名单（模拟 Redis 黑名单；重启即清空）
// ══════════════════════════════════════════════════════════════

/** 模拟后端 SECRET_KEY（真实后端从环境变量读取） */
const JWT_SECRET = 'openlair-mock-secret-2026'
/** 访问令牌有效期：7 天（秒，模拟后端 ACCESS_TOKEN_EXPIRE_SECONDS） */
const JWT_TTL = 7 * 24 * 3600

const b64url = (input: Buffer | string) => Buffer.from(input).toString('base64url')

/** 生成 JWT（HS256） */
export function signToken(userId: string): string {
  const header = b64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const now = Math.floor(Date.now() / 1000)
  const payload = b64url(JSON.stringify({ sub: userId, iat: now, exp: now + JWT_TTL, jti: randomBytes(8).toString('hex') }))
  const sig = b64url(createHmac('sha256', JWT_SECRET).update(`${header}.${payload}`).digest())
  return `${header}.${payload}.${sig}`
}

type TokenStatus =
  | { status: 'ok'; userId: string; jti: string }
  | { status: 'expired' }
  | { status: 'invalid' }

/** 验签 + 过期检查 + 黑名单检查（模拟后端 jwt.decode + 黑名单查询） */
function verifyToken(token: string): TokenStatus {
  const parts = token.split('.')
  if (parts.length !== 3) return { status: 'invalid' }
  const [header, payload, sig] = parts
  const expect = Buffer.from(createHmac('sha256', JWT_SECRET).update(`${header}.${payload}`).digest())
  let got: Buffer
  try {
    got = Buffer.from(sig, 'base64url')
  } catch {
    return { status: 'invalid' }
  }
  if (got.length !== expect.length || !timingSafeEqual(got, expect)) return { status: 'invalid' }
  let claims: Record<string, unknown>
  try {
    claims = JSON.parse(Buffer.from(payload, 'base64url').toString('utf-8'))
  } catch {
    return { status: 'invalid' }
  }
  const now = Math.floor(Date.now() / 1000)
  if (typeof claims.exp !== 'number' || now >= claims.exp) return { status: 'expired' }
  const jti = typeof claims.jti === 'string' ? claims.jti : ''
  if (!jti || rt.revokedJtis.has(jti)) return { status: 'invalid' }
  return { status: 'ok', userId: String(claims.sub), jti }
}

/** 登出：jti 进黑名单 */
export function revokeToken(jti: string) {
  rt.revokedJtis.add(jti)
}

/** API Key：生成明文（ol_ + 32 字节随机串），哈希用 SHA-256（与后端一致：只存哈希） */
export function generateMockApiKey(): string {
  return `ol_${randomBytes(32).toString('base64url')}`
}

export function hashApiKey(apiKey: string): string {
  return createHash('sha256').update(apiKey).digest('hex')
}

/** 密码哈希（模拟 bcrypt）：scrypt$salt$hash */
export function hashPassword(password: string): string {
  const salt = randomBytes(16).toString('hex')
  return `scrypt$${salt}$${scryptSync(password, salt, 64).toString('hex')}`
}

/** 密码校验（恒定时间比较） */
export function verifyPassword(password: string, stored: string): boolean {
  const [scheme, salt, hash] = stored.split('$')
  if (scheme !== 'scrypt' || !salt || !hash) return false
  const expect = Buffer.from(hash, 'hex')
  const got = scryptSync(password, salt, 64)
  return got.length === expect.length && timingSafeEqual(got, expect)
}

/** 分类表种子：固定 id（跨重启稳定，供外键引用），系统预置 26 个（支出 18 + 收入 8）
 *  sortOrder 与后端 seed 一致：支出块 0-17 / 收入块 18-25，「其他」各组兜底位 */
function seedCategories(): Category[] {
  const exp: [string, number][] = [
    ['餐饮', 1], ['交通', 2], ['购物', 3],
    ['居住', 4], ['娱乐', 5], ['医疗', 6],
    ['学习', 7], ['人情', 8], ['通讯', 9],
    ['数码', 17], ['宠物', 18], ['运动健身', 19], ['美妆', 20],
    ['旅行', 21], ['维修', 22], ['订阅服务', 23], ['汽车', 24],
    ['其他', 10],
  ]
  const inc: [string, number][] = [
    ['工资', 11], ['奖金', 12], ['理财', 13],
    ['礼金', 14], ['退款', 15], ['副业', 25], ['报销', 26],
    ['其他', 16],
  ]
  const t = nowISO()
  return [
    ...exp.map(([name, id], i) => ({ id, name, type: '支出' as const, sortOrder: i, isDefault: name === '其他', userId: null, createdAt: t })),
    ...inc.map(([name, id], i) => ({ id, name, type: '收入' as const, sortOrder: 18 + i, isDefault: name === '其他', userId: null, createdAt: t })),
  ]
}

function seed(): StoreShape {
  const categories = seedCategories()
  const expIds = categories.filter((c) => c.type === '支出').map((c) => c.id)
  const incIds = categories.filter((c) => c.type === '收入').map((c) => c.id)
  const t = nowISO()

  // 用户（当前登录用户 + 共享账本成员；id = 1/2/3，注册用户从 4 自增）
  // 测试账号（密码统一 test123456）：
  //   test1@openlair.dev → 我(1)；test2@openlair.dev → 小明(2)；test3@openlair.dev → 小美(3)
  const users: User[] = [
    { id: 1, name: '我', email: 'test1@openlair.dev', passwordHash: hashPassword('test123456'), avatarColor: '#0071e3', createdAt: t },
    { id: 2, name: '小明', email: 'test2@openlair.dev', passwordHash: hashPassword('test123456'), avatarColor: '#30d158', createdAt: t },
    { id: 3, name: '小美', email: 'test3@openlair.dev', passwordHash: hashPassword('test123456'), avatarColor: '#ff6b00', createdAt: t },
  ]

  // 账本：个人账本（默认）+ 共享账本（家庭只是场景之一）
  const books: Book[] = [
    { id: 1, name: '我的账本', type: 'personal', createdAt: t },
    { id: 2, name: '家庭共享账本', type: 'shared', createdAt: t },
  ]

  const bookMembers: BookMember[] = [
    { bookId: 1, userId: 1, role: 'owner', joinedAt: t },
    { bookId: 2, userId: 1, role: 'owner', joinedAt: t },
    { bookId: 2, userId: 2, role: 'editor', joinedAt: t },
    { bookId: 2, userId: 3, role: 'editor', joinedAt: t },
  ]

  // 共享账本 2 预置邀请码（演示 owner 分享界面）
  const bookInvites: BookInvite[] = [{ bookId: 2, code: 'KD7F2GQW' }]

  // 近 90 天交易：个人账本 85 + 共享账本 15（收入 ~25%）
  let txId = 0
  const makeTx = (bookId: number, userId: number): Transaction => {
    const isIncome = rand() < 0.25
    const createdAt = new Date(Date.now() - integer(0, 89) * 86400000 - integer(0, 23) * 3600000).toISOString()
    return {
      id: ++txId,
      type: isIncome ? ('收入' as const) : ('支出' as const),
      categoryId: isIncome ? pick(incIds) : pick(expIds),
      bookId,
      userId,
      amount: isIncome ? float(200, 15000) : float(5, 800),
      date: date(-integer(0, 89)),
      note: isIncome ? pick(['工资', '季度奖金', '理财收益', '红包']) : pick(NOTES),
      createdAt,
      updatedAt: createdAt,
    }
  }
  const familyUsers = [1, 2, 3]
  const transactions: Transaction[] = [
    ...Array.from({ length: 85 }, () => makeTx(1, 1)),
    ...Array.from({ length: 15 }, () => makeTx(2, pick(familyUsers))),
  ]

  return {
    categories,
    transactions,
    budgets: [{ id: 1, bookId: 1, month: MONTH(), expenseLimit: 5000, createdAt: t, updatedAt: t }],
    users,
    books,
    bookMembers,
    bookInvites,
    todos: Array.from({ length: 8 }, (_, i) => {
      const c = nowISO()
      return {
        id: i + 1,
        text: csentence(),
        quadrant: pick(QUADRANTS),
        done: bool(),
        due: pick(DUES),
        createdAt: c,
        updatedAt: c,
      }
    }),
    events: Array.from({ length: 6 }, (_, i) => {
      const c = nowISO()
      return {
        id: i + 1,
        title: csentence(),
        date: date(integer(0, 6)),
        time: `${pad(integer(8, 20))}:00`,
        location: pick(LOCATIONS),
        done: bool(),
        createdAt: c,
        updatedAt: c,
      }
    }),
    notes: ['本周复盘', '阅读摘录', '会议纪要', '灵感速记', '部署备忘'].map((title, i) => {
      const c = nowISO()
      return {
        id: i + 1,
        title,
        summary: csentence() + '，' + csentence() + '。',
        tags: Array.from({ length: integer(1, 3) }, () => pick(TAGS)),
        updatedAt: c,
        createdAt: c,
      }
    }),
    habits: HABIT_NAMES.map((name, i) => {
      const c = nowISO()
      return {
        id: i + 1,
        name,
        streak: integer(0, 15),
        done: bool(),
        week: Array.from({ length: 7 }, () => bool()),
        createdAt: c,
        updatedAt: c,
      }
    }),
    // 倒数日 / 纪念日：覆盖一次性未来/今天/过去、每年、每月（与后端 seed 演示数据同款）
    days: [
      { emoji: '📚', title: '考研初试', date: date(3), repeat: 'once', pinned: false },
      { emoji: '🚀', title: '项目上线', date: date(0), repeat: 'once', pinned: false },
      { emoji: '🎂', title: '宝宝生日', date: shiftYear(date(12), -2), repeat: 'yearly', pinned: true },
      { emoji: '💰', title: '发工资', date: `${new Date().getFullYear()}-${pad(new Date().getMonth() + 1)}-01`, repeat: 'monthly', pinned: false },
      { emoji: '💍', title: '结婚纪念日', date: shiftYear(date(45), -5), repeat: 'yearly', pinned: false },
      { emoji: '💕', title: '在一起', date: date(-1023), repeat: 'once', pinned: false },
    ].map((row, i) => {
      const c = nowISO()
      return { id: i + 1, ...row, createdAt: c, updatedAt: c }
    }),
    assistantSessions: [],
    assistantMessages: [],
    apiKeys: [],
  }
}

if (!rt.store) {
  rt.store = seed()
}

// ---------- 内存态 store（全局唯一，重启即重置） ----------
export const store: StoreShape = rt.store as StoreShape
export { date }

// ══════════════════════════════════════════════════════════════
// Repository 查询层（模拟后端 Service/Repository；各 mock 接口复用）
// ══════════════════════════════════════════════════════════════

// ---------- 分类 ----------
export function getCategory(id: number): Category | undefined {
  return store.categories.find((c) => c.id === id)
}

export function categoryName(id: number): string {
  return getCategory(id)?.name ?? '其他'
}

export function categoriesOf(type: '支出' | '收入'): Category[] {
  return store.categories.filter((c) => c.type === type).sort((a, b) => a.sortOrder - b.sortOrder)
}

/** 分类可见范围：系统预置 + 指定用户集合的自定义（不传 = 全量） */
export function visibleCategories(userIds?: number[], type?: '支出' | '收入'): Category[] {
  let rows = store.categories
  if (userIds) rows = rows.filter((c) => c.userId === null || userIds.includes(c.userId))
  if (type) rows = rows.filter((c) => c.type === type)
  return rows.sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id)
}

/** 同名同类型防重（系统预置或本人已占用即重复） */
export function categoryExists(name: string, type: string, userId: number, excludeId?: number): boolean {
  return store.categories.some(
    (c) => c.name === name && c.type === type && (c.userId === null || c.userId === userId) && c.id !== excludeId,
  )
}

export function createCategory(name: string, type: '支出' | '收入', userId: number): Category {
  const maxSort = Math.max(...store.categories.filter((c) => c.type === type).map((c) => c.sortOrder), 0)
  const c: Category = { id: nextId(store.categories), name, type, sortOrder: maxSort + 1, isDefault: false, userId, createdAt: nowISO() }
  store.categories.push(c)
  return c
}

export function renameCategory(id: number, name: string): Category | undefined {
  const c = getCategory(id)
  if (c) c.name = name
  return c
}

/** 该分类被流水引用条数（删除保护依据） */
export function categoryUsageCount(id: number): number {
  return store.transactions.filter((t) => t.categoryId === id).length
}

export function removeCategory(id: number): boolean {
  const i = store.categories.findIndex((c) => c.id === id)
  if (i === -1) return false
  store.categories.splice(i, 1)
  return true
}

// ---------- 交易筛选条件 ----------
export interface TransactionQuery {
  /** 账本 id（必传，按账本隔离） */
  bookId?: number
  /** 类型：支出 / 收入 / 空（全部） */
  type?: string
  /** 分类 id：空 = 全部 */
  categoryId?: number
  /** 备注/分类名关键字模糊匹配 */
  keyword?: string
  /** 日期范围（含，YYYY-MM-DD） */
  startDate?: string
  endDate?: string
}

// 字符串日期比较（YYYY-MM-DD 可直接 lexicographic）
const cmpDate = (a: string, b: string) => a.localeCompare(b)

/** 按条件筛选（分类名 join） + 日期倒序排序 */
export function queryTransactions(q: TransactionQuery = {}): Transaction[] {
  const kw = (q.keyword ?? '').trim().toLowerCase()
  return store.transactions
    .filter((t) => {
      if (q.bookId && t.bookId !== q.bookId) return false
      if (q.type && t.type !== q.type) return false
      if (q.categoryId && t.categoryId !== q.categoryId) return false
      if (q.startDate && cmpDate(t.date, q.startDate) < 0) return false
      if (q.endDate && cmpDate(t.date, q.endDate) > 0) return false
      if (kw) {
        const name = categoryName(t.categoryId).toLowerCase()
        if (!(t.note.toLowerCase().includes(kw) || name.includes(kw))) return false
      }
      return true
    })
    .sort((a, b) => cmpDate(b.date, a.date))
}

/** 分页（page 从 1 开始），返回切片 */
export function paginate<T>(rows: T[], page = 1, pageSize = 20): T[] {
  const p = Math.max(1, Math.floor(page) || 1)
  const size = Math.max(1, Math.floor(pageSize) || 20)
  return rows.slice((p - 1) * size, p * size)
}

/** 收支汇总 */
export function summarize(rows: Transaction[]) {
  const income = rows.filter((t) => t.type === '收入').reduce((s, t) => s + t.amount, 0)
  const expense = rows.filter((t) => t.type === '支出').reduce((s, t) => s + t.amount, 0)
  return {
    income: Number(income.toFixed(2)),
    expense: Number(expense.toFixed(2)),
    balance: Number((income - expense).toFixed(2)),
  }
}

/** 支出分类统计（join 分类名 + 百分比，按金额倒序） */
export function categoryStats(rows: Transaction[]) {
  const expenses = rows.filter((t) => t.type === '支出')
  const total = expenses.reduce((s, t) => s + t.amount, 0) || 1
  const map = new Map<string, number>()
  for (const t of expenses) map.set(t.categoryId, (map.get(t.categoryId) ?? 0) + t.amount)
  return [...map.entries()]
    .map(([categoryId, amount]) => ({
      categoryId,
      name: categoryName(categoryId),
      amount: Number(amount.toFixed(2)),
      percent: Number(((amount / total) * 100).toFixed(1)),
    }))
    .sort((a, b) => b.amount - a.amount)
}

/** 近 N 个月收支趋势（按月聚合，倒序） */
export function monthlyTrend(rows: Transaction[], months = 6) {
  const points: { month: string; income: number; expense: number }[] = []
  const now = new Date()
  for (let i = months - 1; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const key = `${d.getFullYear()}-${pad(d.getMonth() + 1)}`
    let income = 0
    let expense = 0
    for (const t of rows) {
      if (!t.date.startsWith(key)) continue
      if (t.type === '收入') income += t.amount
      else expense += t.amount
    }
    points.push({
      month: key,
      income: Number(income.toFixed(2)),
      expense: Number(expense.toFixed(2)),
    })
  }
  return points
}

/** 当前月预算（按账本） */
export function currentBudget(bookId: number): Budget {
  const month = MONTH()
  const found = store.budgets.find((b) => b.bookId === bookId && b.month === month)
  if (found) return found
  const t = nowISO()
  const b: Budget = { id: nextId(store.budgets), bookId, month, expenseLimit: 5000, createdAt: t, updatedAt: t }
  store.budgets.push(b)
  return b
}

// ---------- 账本 / 成员 ----------
export function bookOf(id: number): Book | undefined {
  return store.books.find((b) => b.id === id)
}

export function membersOf(bookId: number): BookMember[] {
  return store.bookMembers.filter((m) => m.bookId === bookId)
}

/** 邀请码字母表（与后端一致：剔除 0/O/1/I/L） */
const INVITE_ALPHABET = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'

/** 生成 8 位随机邀请码 */
export function generateInviteCode(): string {
  let code = ''
  for (let i = 0; i < 8; i++) code += INVITE_ALPHABET[Math.floor(Math.random() * INVITE_ALPHABET.length)]
  return code
}

/** 查账本的邀请码（未生成 = undefined） */
export function inviteOf(bookId: number): string | undefined {
  return store.bookInvites.find((i) => i.bookId === bookId)?.code
}

/** 设置/清除邀请码（code = null 时关闭邀请） */
export function setInvite(bookId: number, code: string | null): void {
  store.bookInvites = store.bookInvites.filter((i) => i.bookId !== bookId)
  if (code) store.bookInvites.push({ bookId, code })
}

/** 按邀请码查账本（仅未删除） */
export function bookByInvite(code: string): Book | undefined {
  const normalized = code.toUpperCase().replace(/[^0-9A-Z]/g, '')
  const invite = store.bookInvites.find((i) => i.code === normalized)
  if (!invite) return undefined
  const book = bookOf(invite.bookId)
  return book && !book.deletedAt ? book : undefined
}

export function userOf(id: number): User | undefined {
  return store.users.find((u) => u.id === id)
}

export function userName(id: number): string {
  return userOf(id)?.name ?? '未知'
}

// ══════════════════════════════════════════════════════════════
// 统一响应信封（与真实后端完全一致）：{ code, message, data }
// - 成功：code=200，data 为业务数据
// - 失败：code=HTTP 状态码，message 为人类可读错误，data=null
// - HTTP 状态码与 code 一致（respond 里写入）
// ══════════════════════════════════════════════════════════════

export interface ApiResult<T = unknown> {
  status: number
  code: number
  message: string
  data: T
}

/** 成功响应 */
export function ok<T>(data: T, message = '成功'): ApiResult<T> {
  return { status: 200, code: 200, message, data }
}

/** 失败响应（code 与 HTTP 状态码一致） */
export function err(status: number, message: string): ApiResult<null> {
  return { status, code: status, message, data: null }
}

/** 请求对象最小类型（对应 vite-plugin-mock-dev-server 的 MockRequest） */
export interface MockReq {
  query: Record<string, unknown>
  params: Record<string, unknown>
  body: Record<string, unknown>
  headers: Record<string, unknown>
  getCookie: (name: string) => string | undefined
}

interface MockRes {
  statusCode: number
  setHeader: (name: string, value: string) => void
  end: (body?: string) => void
}

/** 标准响应处理器：写 HTTP 状态码 + JSON 信封（模拟 FastAPI 响应） */
export function respond(handler: (req: MockReq) => ApiResult) {
  return (req: MockReq, res: MockRes) => {
    try {
      const result = handler(req)
      res.statusCode = result.status
      res.setHeader('Content-Type', 'application/json; charset=utf-8')
      res.end(JSON.stringify({ code: result.code, message: result.message, data: result.data }))
    } catch {
      res.statusCode = 500
      res.setHeader('Content-Type', 'application/json; charset=utf-8')
      res.end(JSON.stringify({ code: 500, message: '服务器内部错误', data: null }))
    }
  }
}

// ---------- 鉴权 ----------

export interface AuthContext {
  userId: string
  jti: string
}

/** 从请求头解析并验签凭证（模拟后端 OAuth2PasswordBearer + API Key 依赖）：
 * - X-API-Key: <ol_xxx>：哈希比对 store.apiKeys，未撤销则以其 userId 通过（jti 为空串）
 * - Authorization: Bearer <jwt>：JWT 验签 */
export function requireAuth(req: MockReq): AuthContext | null {
  const apiKeyHeader = req.headers?.['x-api-key']
  if (typeof apiKeyHeader === 'string' && apiKeyHeader.trim()) {
    const found = store.apiKeys.find(
      (k) => k.keyHash === hashApiKey(apiKeyHeader.trim()) && !k.revokedAt,
    )
    if (!found) return null
    found.lastUsedAt = new Date().toISOString()
    return { userId: String(found.userId), jti: '' }
  }
  const header = req.headers?.authorization
  if (typeof header !== 'string' || !header.startsWith('Bearer ')) return null
  const result = verifyToken(header.slice(7).trim())
  return result.status === 'ok' ? { userId: result.userId, jti: result.jti } : null
}

/** 业务接口鉴权包装：未登录 / token 无效 / 过期 → 统一 401 */
export function guard(handler: (req: MockReq, auth: AuthContext) => ApiResult) {
  return (req: MockReq): ApiResult => {
    const auth = requireAuth(req)
    if (!auth) return err(401, '未登录或登录已过期，请重新登录')
    return handler(req, auth)
  }
}
