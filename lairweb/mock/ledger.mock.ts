import { defineMock } from 'vite-plugin-mock-dev-server'
import {
  store,
  type Transaction,
  guid,
  date,
  queryTransactions,
  paginate,
  summarize,
  categoryStats,
  monthlyTrend,
  currentBudget,
  categoryName,
  getCategory,
  categoriesOf,
  type TransactionQuery,
} from './store'

/** DTO：交易 + join 分类名（真实后端同样返回扁平 DTO） */
type TransactionDTO = Transaction & { category: string }

function toDTO(t: Transaction): TransactionDTO {
  return { ...t, category: categoryName(t.categoryId) }
}

function queryFrom(req: { query?: Record<string, unknown> }): TransactionQuery {
  const q = req.query ?? {}
  const str = (v: unknown) => (v == null ? '' : String(v))
  return {
    type: str(q.type) || undefined,
    categoryId: str(q.categoryId) || undefined,
    keyword: str(q.keyword) || undefined,
    startDate: str(q.startDate) || undefined,
    endDate: str(q.endDate) || undefined,
  }
}

export default {
  // 分类表：?type=支出|收入 过滤，默认全部
  categories: defineMock({
    url: '/api/ledger/categories',
    method: 'GET',
    body: (req) => {
      const type = String(req.query?.type ?? '')
      const rows = type ? categoriesOf(type as '支出' | '收入') : store.categories
      return rows.map((c) => ({ ...c }))
    },
  }),

  // 列表：筛选 + 分页；摘要/分类统计跟随筛选结果
  list: defineMock({
    url: '/api/ledger',
    method: 'GET',
    body: (req) => {
      const q = queryFrom(req)
      const rows = queryTransactions(q)
      const page = Number(req.query?.page) || 1
      const pageSize = Number(req.query?.pageSize) || 20
      const budget = currentBudget()
      return {
        summary: summarize(rows),
        categoryStats: categoryStats(rows),
        transactions: paginate(rows, page, pageSize).map(toDTO),
        total: rows.length,
        page,
        pageSize,
        budget: budget.expenseLimit,
      }
    },
  }),

  // 近 6 个月收支趋势
  trend: defineMock({
    url: '/api/ledger/trend',
    method: 'GET',
    body: () => monthlyTrend(store.transactions, 6),
  }),

  // 读取/更新当前月预算
  budget: defineMock({
    url: '/api/ledger/budget',
    method: 'GET',
    body: () => ({ budget: currentBudget().expenseLimit }),
  }),
  updateBudget: defineMock({
    url: '/api/ledger/budget',
    method: 'PUT',
    body: (req) => {
      const amount = Number(req.body?.amount)
      if (!Number.isFinite(amount) || amount < 0) return { ok: false, error: 'invalid budget' }
      const b = currentBudget()
      b.expenseLimit = Number(amount.toFixed(2))
      b.updatedAt = new Date().toISOString()
      return { ok: true, budget: b.expenseLimit }
    },
  }),

  // 新增
  create: defineMock({
    url: '/api/ledger',
    method: 'POST',
    body: (req) => {
      const { type, categoryId, category, amount, date: reqDate, note } = req.body ?? {}
      // 兼容：传 categoryId 直接使用；传 category 名字则查表（或兜底「其他」）
      let cid = String(categoryId || '')
      if (!cid && category) {
        const c = store.categories.find((x) => x.name === String(category))
        if (c) cid = c.id
      }
      if (!cid) {
        const fallback = store.categories.find((c) => c.type === (type === '收入' ? '收入' : '支出') && c.isDefault)
        cid = fallback?.id ?? store.categories[0].id
      }
      const t = new Date().toISOString()
      const item: Transaction = {
        id: guid(),
        type: type === '收入' ? '收入' : '支出',
        categoryId: cid,
        amount: Number(amount) || 0,
        date: String(reqDate || date()),
        note: String(note || ''),
        createdAt: t,
        updatedAt: t,
      }
      store.transactions.push(item)
      return { ok: true, id: item.id, item: toDTO(item) }
    },
  }),

  // 更新
  update: defineMock({
    url: '/api/ledger/:id',
    method: 'PUT',
    body: (req) => {
      const id = String(req.params?.id)
      const index = store.transactions.findIndex((t) => t.id === id)
      if (index < 0) return { ok: false, error: 'not found' }
      const patch = (req.body ?? {}) as Partial<Transaction>
      store.transactions[index] = {
        ...store.transactions[index],
        ...patch,
        id,
        updatedAt: new Date().toISOString(),
      }
      return { ok: true, item: toDTO(store.transactions[index]) }
    },
  }),

  // 删除
  remove: defineMock({
    url: '/api/ledger/:id',
    method: 'DELETE',
    body: (req) => {
      const id = String(req.params?.id)
      const before = store.transactions.length
      store.transactions = store.transactions.filter((t) => t.id !== id)
      return { ok: before !== store.transactions.length }
    },
  }),
}

export { getCategory }
