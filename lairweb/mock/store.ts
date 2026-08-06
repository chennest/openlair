// 内存态 mock 数据 store
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

// ---------- 类型 ----------
export interface Transaction {
  id: string
  type: '支出' | '收入'
  category: string
  amount: number
  date: string
  note: string
}

export interface TodoItem {
  id: string
  text: string
  quadrant: string
  done: boolean
  due: string
}

export interface CalendarEvent {
  id: string
  title: string
  date: string
  time: string
  location: string
  done: boolean
}

export interface Note {
  id: string
  title: string
  summary: string
  tags: string[]
  updatedAt: string
}

export interface Habit {
  id: string
  name: string
  streak: number
  done: boolean
  week: boolean[]
}

// ---------- 分类常量 ----------
export const CATEGORIES = ['餐饮', '交通', '购物', '居住', '娱乐', '医疗', '学习', '其他']
export const QUADRANTS = ['重要紧急', '重要不紧急', '紧急不重要', '不重要不紧急']

// ---------- 共享运行时（globalThis） ----------
interface SharedRuntime {
  rand: () => number
  store: StoreShape | null
}

export interface StoreShape {
  transactions: Transaction[]
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

function seed(): StoreShape {
  return {
    transactions: Array.from({ length: 10 }, () => ({
      id: guid(),
      type: rand() < 0.25 ? ('收入' as const) : ('支出' as const),
      category: pick(CATEGORIES),
      amount: float(5, 800),
      date: date(-integer(0, 6)),
      note: pick(NOTES),
    })),
    todos: Array.from({ length: 8 }, () => ({
      id: guid(),
      text: csentence(),
      quadrant: pick(QUADRANTS),
      done: bool(),
      due: pick(DUES),
    })),
    events: Array.from({ length: 6 }, () => ({
      id: guid(),
      title: csentence(),
      date: date(integer(0, 6)),
      time: `${pad(integer(8, 20))}:00`,
      location: pick(LOCATIONS),
      done: bool(),
    })),
    notes: ['本周复盘', '阅读摘录', '会议纪要', '灵感速记', '部署备忘'].map((title) => ({
      id: guid(),
      title,
      summary: csentence() + '，' + csentence() + '。',
      tags: Array.from({ length: integer(1, 3) }, () => pick(TAGS)),
      updatedAt: date(-integer(0, 5)),
    })),
    habits: HABIT_NAMES.map((name) => ({
      id: guid(),
      name,
      streak: integer(0, 15),
      done: bool(),
      week: Array.from({ length: 7 }, () => bool()),
    })),
  }
}

if (!rt.store) {
  rt.store = seed()
}

// ---------- 内存态 store（全局唯一，重启即重置） ----------
export const store: StoreShape = rt.store as StoreShape
export { guid, date }
