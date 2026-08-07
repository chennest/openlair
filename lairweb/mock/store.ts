// 内存态 mock 数据层 —— 模拟真实数据库（表 + 查询）
// - 表结构与后续 FastAPI + SQLAlchemy 后端对齐：id / 外键 / 时间戳
// - 使用固定 seed 的伪随机，初始数据每次启动一致
// - 运行中增删改查直接改内存，重启即恢复初始数据
// - 通过 globalThis 共享：vite-plugin-mock-dev-server 对每个 mock 文件单独 esbuild
//   bundle，若用模块级变量，每个文件会得到独立实例（id 冲突 + 数据不互通）

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

/** categories 表：分类 */
export interface Category {
  id: string
  name: string
  type: '支出' | '收入'
  /** 排序权重（小在前） */
  sortOrder: number
  /** 系统默认分类（如「其他」），不可删除 */
  isDefault: boolean
  createdAt: string
}

/** transactions 表：交易流水（categoryId 外键 → categories.id） */
export interface Transaction {
  id: string
  type: '支出' | '收入'
  categoryId: string
  amount: number
  /** YYYY-MM-DD */
  date: string
  note: string
  createdAt: string
  updatedAt: string
}

/** budgets 表：月度预算（month = 'YYYY-MM'） */
export interface Budget {
  id: string
  month: string
  expenseLimit: number
  createdAt: string
  updatedAt: string
}

export interface TodoItem {
  id: string
  text: string
  quadrant: string
  done: boolean
  due: string
  createdAt: string
  updatedAt: string
}

export interface CalendarEvent {
  id: string
  title: string
  date: string
  time: string
  location: string
  done: boolean
  createdAt: string
  updatedAt: string
}

export interface Note {
  id: string
  title: string
  summary: string
  tags: string[]
  updatedAt: string
  createdAt: string
}

export interface Habit {
  id: string
  name: string
  streak: number
  done: boolean
  week: boolean[]
  createdAt: string
  updatedAt: string
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
}

export interface StoreShape {
  categories: Category[]
  transactions: Transaction[]
  budgets: Budget[]
  todos: TodoItem[]
  events: CalendarEvent[]
  notes: Note[]
  habits: Habit[]
}

const g = globalThis as unknown as { __openlair_mock__?: SharedRuntime }
if (!g.__openlair_mock__) {
  g.__openlair_mock__ = { rand: mulberry32(20260806), store: null }
}
const rt = g.__openlair_mock__
const rand = rt.rand

// ---------- 随机辅助 ----------
const pick = <T,>(arr: T[]): T => arr[Math.floor(rand() * arr.length)]
const integer = (min: number, max: number) => Math.floor(rand() * (max - min + 1)) + min
const float = (min: number, max: number, digits = 2) => Number((rand() * (max - min) + min).toFixed(digits))
const bool = () => rand() > 0.5
const guid = () =>
  'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (rand() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
const pad = (n: number) => String(n).padStart(2, '0')
const date = (offsetDays = 0) => {
  const d = new Date(Date.now() + offsetDays * 86400000)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
const nowISO = () => new Date().toISOString()
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

/** 分类表种子：固定 id（跨重启稳定，供外键引用），支出 10 + 收入 6 */
function seedCategories(): Category[] {
  const exp: [string, string][] = [
    ['cat-exp-food', '餐饮'], ['cat-exp-trans', '交通'], ['cat-exp-shop', '购物'],
    ['cat-exp-home', '居住'], ['cat-exp-fun', '娱乐'], ['cat-exp-med', '医疗'],
    ['cat-exp-study', '学习'], ['cat-exp-social', '人情'], ['cat-exp-com', '通讯'],
    ['cat-exp-other', '其他'],
  ]
  const inc: [string, string][] = [
    ['cat-inc-salary', '工资'], ['cat-inc-bonus', '奖金'], ['cat-inc-inv', '理财'],
    ['cat-inc-gift', '礼金'], ['cat-inc-refund', '退款'], ['cat-inc-other', '其他'],
  ]
  const t = nowISO()
  return [
    ...exp.map(([id, name], i) => ({ id, name, type: '支出' as const, sortOrder: i, isDefault: name === '其他', createdAt: t })),
    ...inc.map(([id, name], i) => ({ id, name, type: '收入' as const, sortOrder: i, isDefault: name === '其他', createdAt: t })),
  ]
}

function seed(): StoreShape {
  const categories = seedCategories()
  const expIds = categories.filter((c) => c.type === '支出').map((c) => c.id)
  const incIds = categories.filter((c) => c.type === '收入').map((c) => c.id)
  const t = nowISO()

  // 近 90 天交易：约 85 笔（收入 ~25%），历史查询有数据可筛
  const transactions: Transaction[] = Array.from({ length: 85 }, () => {
    const isIncome = rand() < 0.25
    const createdAt = new Date(Date.now() - integer(0, 89) * 86400000 - integer(0, 23) * 3600000).toISOString()
    return {
      id: guid(),
      type: isIncome ? ('收入' as const) : ('支出' as const),
      categoryId: isIncome ? pick(incIds) : pick(expIds),
      amount: isIncome ? float(200, 15000) : float(5, 800),
      date: date(-integer(0, 89)),
      note: isIncome ? pick(['工资', '季度奖金', '理财收益', '红包']) : pick(NOTES),
      createdAt,
      updatedAt: createdAt,
    }
  })

  return {
    categories,
    transactions,
    budgets: [{ id: 'bud-1', month: MONTH(), expenseLimit: 5000, createdAt: t, updatedAt: t }],
    todos: Array.from({ length: 8 }, () => {
      const c = nowISO()
      return {
        id: guid(),
        text: csentence(),
        quadrant: pick(QUADRANTS),
        done: bool(),
        due: pick(DUES),
        createdAt: c,
        updatedAt: c,
      }
    }),
    events: Array.from({ length: 6 }, () => {
      const c = nowISO()
      return {
        id: guid(),
        title: csentence(),
        date: date(integer(0, 6)),
        time: `${pad(integer(8, 20))}:00`,
        location: pick(LOCATIONS),
        done: bool(),
        createdAt: c,
        updatedAt: c,
      }
    }),
    notes: ['本周复盘', '阅读摘录', '会议纪要', '灵感速记', '部署备忘'].map((title) => {
      const c = nowISO()
      return {
        id: guid(),
        title,
        summary: csentence() + '，' + csentence() + '。',
        tags: Array.from({ length: integer(1, 3) }, () => pick(TAGS)),
        updatedAt: c,
        createdAt: c,
      }
    }),
    habits: HABIT_NAMES.map((name) => {
      const c = nowISO()
      return {
        id: guid(),
        name,
        streak: integer(0, 15),
        done: bool(),
        week: Array.from({ length: 7 }, () => bool()),
        createdAt: c,
        updatedAt: c,
      }
    }),
  }
}

if (!rt.store) {
  rt.store = seed()
}

// ---------- 内存态 store（全局唯一，重启即重置） ----------
export const store: StoreShape = rt.store as StoreShape
export { guid, date }

// ══════════════════════════════════════════════════════════════
// Repository 查询层（模拟后端 Service/Repository；各 mock 接口复用）
// ══════════════════════════════════════════════════════════════

// ---------- 分类 ----------
export function getCategory(id: string): Category | undefined {
  return store.categories.find((c) => c.id === id)
}

export function categoryName(id: string): string {
  return getCategory(id)?.name ?? '其他'
}

export function categoriesOf(type: '支出' | '收入'): Category[] {
  return store.categories.filter((c) => c.type === type).sort((a, b) => a.sortOrder - b.sortOrder)
}

// ---------- 交易筛选条件 ----------
export interface TransactionQuery {
  /** 类型：支出 / 收入 / 空（全部） */
  type?: string
  /** 分类 id：空 = 全部 */
  categoryId?: string
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

/** 当前月预算 */
export function currentBudget(): Budget {
  const month = MONTH()
  const found = store.budgets.find((b) => b.month === month)
  if (found) return found
  const t = nowISO()
  const b: Budget = { id: guid(), month, expenseLimit: 5000, createdAt: t, updatedAt: t }
  store.budgets.push(b)
  return b
}
