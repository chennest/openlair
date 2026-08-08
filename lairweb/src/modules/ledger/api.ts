import { get, post, put, del } from '../../api/request'

// ---------- 类型（对齐 mock 表结构 / 后端 DTO） ----------
export interface Category {
  id: number
  name: string
  type: '支出' | '收入'
  sortOrder: number
  isDefault: boolean
}

export interface Transaction {
  id: number
  type: '支出' | '收入'
  categoryId: number
  /** join 分类名（后端 DTO 返回） */
  category: string
  bookId: number
  /** 记账人 id */
  userId: number
  /** join 记账人名字 */
  userName: string
  amount: number
  date: string
  note: string
}

// ---------- 账本 / 成员 ----------
export interface User {
  id: number
  name: string
  avatarColor: string
}

export interface BookMember {
  bookId: number
  userId: number
  role: 'owner' | 'editor'
  user?: User
}

export interface Book {
  id: number
  name: string
  type: 'personal' | 'shared'
  members: BookMember[]
  /** 软删除标记（非空 = 在回收站） */
  deletedAt?: string
}

export interface CategoryStat {
  categoryId: number
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
  /** 账本 id */
  bookId?: number
  /** 支出 / 收入 / 空 = 全部 */
  type?: '支出' | '收入' | ''
  /** 分类 id */
  categoryId?: number
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
  categoryId: number
  bookId?: number
  userId?: number
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
  if (query.bookId) params.set('bookId', String(query.bookId))
  if (query.type) params.set('type', query.type)
  if (query.categoryId) params.set('categoryId', String(query.categoryId))
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
  /** 交易列表（按账本隔离 + 筛选 + 分页） */
  list: (query: LedgerQuery = {}) => get<LedgerData>(`/api/ledger${qs(query)}`),
  /** 近 6 月收支趋势（按账本） */
  trend: (bookId?: number) => get<TrendPoint[]>(`/api/ledger/trend${bookId ? `?bookId=${bookId}` : ''}`),
  /** 当前月预算（按账本） */
  getBudget: (bookId?: number) => get<{ budget: number }>(`/api/ledger/budget${bookId ? `?bookId=${bookId}` : ''}`),
  updateBudget: (bookId: number, amount: number) =>
    put<{ budget: number }>('/api/ledger/budget', { bookId, amount }),
  create: (input: CreateTransactionInput) => post<{ id: number; item: Transaction }>('/api/ledger', input),
  remove: (id: number) => del<{ ok: boolean }>(`/api/ledger/${id}`),
}

/** 账本 API（共享账单核心） */
export const bookApi = {
  list: () => get<Book[]>('/api/books'),
  create: (input: { name: string; type: 'personal' | 'shared' }) =>
    post<{ ok: boolean; book: Book }>('/api/books', input),
  addMember: (bookId: number, input: { userId?: number; name?: string }) =>
    post<{ ok: boolean; book?: Book }>(`/api/books/${bookId}/members`, input),
  removeMember: (bookId: number, userId: number) =>
    del<{ ok: boolean; book?: Book }>(`/api/books/${bookId}/members/${userId}`),
  /** 回收站列表（软删除的账本） */
  trash: () => get<Book[]>('/api/books/trash'),
  /** 删除账本 → 移入回收站（软删除） */
  softDelete: (bookId: number) => del<{ ok: boolean }>(`/api/books/${bookId}`),
  /** 从回收站恢复 */
  restore: (bookId: number) => post<{ ok: boolean }>(`/api/books/${bookId}/restore`, {}),
  /** 彻底删除（级联清流水/预算/成员） */
  purge: (bookId: number) => del<{ ok: boolean }>(`/api/books/${bookId}/purge`),
}
