import { get, post, put, del } from '../../api/request'

// ---------- 类型（对齐 mock 表结构 / 后端 DTO） ----------
export interface Category {
  id: string
  name: string
  type: '支出' | '收入'
  sortOrder: number
  isDefault: boolean
}

export interface Transaction {
  id: string
  type: '支出' | '收入'
  categoryId: string
  /** join 分类名（后端 DTO 返回） */
  category: string
  amount: number
  date: string
  note: string
}

export interface CategoryStat {
  categoryId: string
  name: string
  amount: number
  percent: number
}

export interface LedgerSummary {
  income: number
  expense: number
  balance: number
}

export interface TrendPoint {
  month: string
  income: number
  expense: number
}

/** 历史查询参数（与后端 query 对齐） */
export interface LedgerQuery {
  /** 支出 / 收入 / 空 = 全部 */
  type?: '支出' | '收入' | ''
  /** 分类 id */
  categoryId?: string
  keyword?: string
  /** YYYY-MM-DD，含边界 */
  startDate?: string
  endDate?: string
  page?: number
  pageSize?: number
}

export interface LedgerData {
  summary: LedgerSummary
  categoryStats: CategoryStat[]
  transactions: Transaction[]
  total: number
  page: number
  pageSize: number
  budget: number
}

export interface CreateTransactionInput {
  type: '支出' | '收入'
  categoryId: string
  amount: number
  date?: string
  note?: string
}

// ---------- 分类常量（仅前端本地兜底/展示用；数据源以接口为准） ----------
export const EXPENSE_CATEGORIES = ['餐饮', '交通', '购物', '居住', '娱乐', '医疗', '学习', '人情', '通讯', '其他']
export const INCOME_CATEGORIES = ['工资', '奖金', '理财', '礼金', '退款', '其他']
export const CATEGORIES = [...new Set([...EXPENSE_CATEGORIES, ...INCOME_CATEGORIES])]

// ---------- API ----------
function qs(query: LedgerQuery): string {
  const params = new URLSearchParams()
  if (query.type) params.set('type', query.type)
  if (query.categoryId) params.set('categoryId', query.categoryId)
  if (query.keyword) params.set('keyword', query.keyword)
  if (query.startDate) params.set('startDate', query.startDate)
  if (query.endDate) params.set('endDate', query.endDate)
  if (query.page) params.set('page', String(query.page))
  if (query.pageSize) params.set('pageSize', String(query.pageSize))
  const s = params.toString()
  return s ? `?${s}` : ''
}

export const ledgerApi = {
  /** 分类表 */
  categories: (type?: '支出' | '收入') => get<Category[]>(`/api/ledger/categories${type ? `?type=${type}` : ''}`),
  /** 交易列表（筛选 + 分页） */
  list: (query: LedgerQuery = {}) => get<LedgerData>(`/api/ledger${qs(query)}`),
  /** 近 6 月收支趋势 */
  trend: () => get<TrendPoint[]>('/api/ledger/trend'),
  /** 当前月预算 */
  getBudget: () => get<{ budget: number }>('/api/ledger/budget'),
  updateBudget: (amount: number) => put<{ ok: boolean; budget: number }>('/api/ledger/budget', { amount }),
  create: (input: CreateTransactionInput) => post<{ ok: boolean; id: string }>('/api/ledger', input),
  remove: (id: string) => del<{ ok: boolean }>(`/api/ledger/${id}`),
}
