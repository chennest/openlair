import { get, post, put, del } from '../../api/request'

// ---------- 类型（对齐 mock 表结构 / 后端 DTO） ----------
export interface Category {
  id: number
  name: string
  type: '支出' | '收入'
  sortOrder: number
  isDefault: boolean
  /** 归属用户 id（null = 系统预置；非空 = 该用户创建，可改删） */
  userId: number | null
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

/** 编辑流水：可改字段（type/分类/金额/日期/备注） */
export interface UpdateTransactionInput {
  type?: '支出' | '收入'
  categoryId?: number
  amount?: number
  date?: string
  note?: string
}

// ---------- 分类常量（仅前端本地兜底/展示用；数据源以接口为准） ----------
export const EXPENSE_CATEGORIES = [
  '餐饮', '交通', '购物', '居住', '娱乐', '医疗', '学习', '人情', '通讯',
  '数码', '宠物', '运动健身', '美妆', '旅行', '维修', '订阅服务', '汽车', '其他',
]
export const INCOME_CATEGORIES = ['工资', '奖金', '理财', '礼金', '退款', '副业', '报销', '其他']
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
  /**
   * 分类表：系统预置 + 可见自定义
   * @param bookId 传入 = 该账本全部成员的自定义分类也可见（共享账本共用）；缺省 = 仅本人
   */
  categories: (type?: '支出' | '收入', bookId?: number) => {
    const p = new URLSearchParams()
    if (type) p.set('type', type)
    if (bookId) p.set('bookId', String(bookId))
    const s = p.toString()
    return get<Category[]>(`/api/ledger/categories${s ? `?${s}` : ''}`)
  },
  /** 交易列表（按账本隔离 + 筛选 + 分页） */
  list: (query: LedgerQuery = {}) => get<LedgerData>(`/api/ledger${qs(query)}`),
  /** 近 6 月收支趋势（按账本） */
  trend: (bookId?: number) => get<TrendPoint[]>(`/api/ledger/trend${bookId ? `?bookId=${bookId}` : ''}`),
  /** 当前月预算（按账本） */
  getBudget: (bookId?: number) => get<{ budget: number }>(`/api/ledger/budget${bookId ? `?bookId=${bookId}` : ''}`),
  updateBudget: (bookId: number, amount: number) =>
    put<{ budget: number }>('/api/ledger/budget', { bookId, amount }),
  create: (input: CreateTransactionInput) => post<{ id: number; item: Transaction }>('/api/ledger', input),
  /** 编辑单条流水（PUT /api/ledger/{id}） */
  update: (id: number, patch: UpdateTransactionInput) =>
    put<{ item: Transaction }>(`/api/ledger/${id}`, patch),
  remove: (id: number) => del<{ ok: boolean }>(`/api/ledger/${id}`),
}

/** 分类管理 API：仅系统预置不可改删；删除时若挂有流水后端返回 409 */
export const categoryApi = {
  create: (input: { name: string; type: '支出' | '收入' }) => post<Category>('/api/ledger/categories', input),
  rename: (id: number, name: string) => put<Category>(`/api/ledger/categories/${id}`, { name }),
  remove: (id: number) => del<{ ok: boolean }>(`/api/ledger/categories/${id}`),
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
  /** 查看邀请码（仅 owner；null = 未生成） */
  getInvite: (bookId: number) => get<{ code: string | null }>(`/api/books/${bookId}/invite`),
  /** 生成/重置邀请码（旧码立即失效） */
  resetInvite: (bookId: number) => post<{ code: string }>(`/api/books/${bookId}/invite`, {}),
  /** 关闭邀请（彻底停止新成员加入） */
  disableInvite: (bookId: number) => del<{ ok: boolean }>(`/api/books/${bookId}/invite`),
  /** 输入邀请码加入共享账本 */
  joinByCode: (code: string) => post<{ book: Book }>('/api/books/join', { code }),
  /** 成员自助退出账本（owner 不可） */
  leave: (bookId: number) => post<{ ok: boolean }>(`/api/books/${bookId}/leave`, {}),
  /** 回收站列表（软删除的账本） */
  trash: () => get<Book[]>('/api/books/trash'),
  /** 删除账本 → 移入回收站（软删除） */
  softDelete: (bookId: number) => del<{ ok: boolean }>(`/api/books/${bookId}`),
  /** 从回收站恢复 */
  restore: (bookId: number) => post<{ ok: boolean }>(`/api/books/${bookId}/restore`, {}),
  /** 个人账本 → 共享账本（单向，不可倒转） */
  convertToShared: (bookId: number) => post<{ ok: boolean; book: Book }>(`/api/books/${bookId}/convert`, {}),
  /** 彻底删除（级联清流水/预算/成员） */
  purge: (bookId: number) => del<{ ok: boolean }>(`/api/books/${bookId}/purge`),
}
