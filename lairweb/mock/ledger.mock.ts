import { defineMock } from 'vite-plugin-mock-dev-server'
import {
  store,
  type Transaction,
  nextId,
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
  userName,
  respond,
  ok,
  err,
  guard,
  type TransactionQuery,
} from './store'

/** DTO：交易 + join 分类名 + 记账人（真实后端同样返回扁平 DTO） */
type TransactionDTO = Transaction & { category: string; userName: string }

function toDTO(t: Transaction): TransactionDTO {
  return { ...t, category: categoryName(t.categoryId), userName: userName(t.userId) }
}

function queryFrom(req: { query?: Record<string, unknown> }): TransactionQuery {
  const q = req.query ?? {}
  const str = (v: unknown) => (v == null ? '' : String(v))
  const num = (v: unknown) => {
    const n = Number(v)
    return Number.isFinite(n) && n > 0 ? n : undefined
  }
  return {
    bookId: num(q.bookId),
    type: str(q.type) || undefined,
    categoryId: num(q.categoryId),
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
    response: respond(
      guard((req) => {
        const type = String(req.query?.type ?? '')
        const rows = type ? categoriesOf(type as '支出' | '收入') : store.categories
        return ok(rows.map((c) => ({ ...c })))
      }),
    ),
  }),

  // 列表：按账本隔离 + 筛选 + 分页；摘要/分类统计跟随筛选结果
  list: defineMock({
    url: '/api/ledger',
    method: 'GET',
    response: respond(
      guard((req) => {
        const q = queryFrom(req)
        const rows = queryTransactions(q)
        const page = Number(req.query?.page) || 1
        const pageSize = Number(req.query?.pageSize) || 20
        const budget = currentBudget(q.bookId ?? 1)
        return ok({
          summary: summarize(rows),
          categoryStats: categoryStats(rows),
          transactions: paginate(rows, page, pageSize).map(toDTO),
          total: rows.length,
          page,
          pageSize,
          budget: budget.expenseLimit,
        })
      }),
    ),
  }),

  // 近 6 个月收支趋势（按账本）
  trend: defineMock({
    url: '/api/ledger/trend',
    method: 'GET',
    response: respond(
      guard((req) => {
        const bookId = Number(req.query?.bookId) || 1
        return ok(monthlyTrend(store.transactions.filter((t) => t.bookId === bookId), 6))
      }),
    ),
  }),

  // 读取/更新当前月预算（按账本）
  budget: defineMock({
    url: '/api/ledger/budget',
    method: 'GET',
    response: respond(
      guard((req) => {
        const bookId = Number(req.query?.bookId) || 1
        return ok({ budget: currentBudget(bookId).expenseLimit })
      }),
    ),
  }),
  updateBudget: defineMock({
    url: '/api/ledger/budget',
    method: 'PUT',
    response: respond(
      guard((req) => {
        const bookId = Number(req.body?.bookId) || 1
        const amount = Number(req.body?.amount)
        if (!Number.isFinite(amount) || amount < 0) return err(400, '预算金额不合法')
        const b = currentBudget(bookId)
        b.expenseLimit = Number(amount.toFixed(2))
        b.updatedAt = new Date().toISOString()
        return ok({ budget: b.expenseLimit })
      }),
    ),
  }),

  // 新增（记账人 = 当前登录用户）
  create: defineMock({
    url: '/api/ledger',
    method: 'POST',
    response: respond(
      guard((req, auth) => {
        const { type, categoryId, category, amount, date: reqDate, note, bookId } = req.body ?? {}
        // 兼容：传 categoryId 直接使用；传 category 名字则查表（或兜底「其他」）
        let cid = Number(categoryId)
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
          id: nextId(store.transactions),
          type: type === '收入' ? '收入' : '支出',
          categoryId: cid,
          bookId: Number(bookId) || 1,
          userId: auth.userId,
          amount: Number(amount) || 0,
          date: String(reqDate || date()),
          note: String(note || ''),
          createdAt: t,
          updatedAt: t,
        }
        store.transactions.push(item)
        return ok({ id: item.id, item: toDTO(item) })
      }),
    ),
  }),

  // 更新
  update: defineMock({
    url: '/api/ledger/:id',
    method: 'PUT',
    response: respond(
      guard((req) => {
        const id = String(req.params?.id)
        const index = store.transactions.findIndex((t) => t.id === id)
        if (index < 0) return err(404, '流水不存在')
        const patch = (req.body ?? {}) as Partial<Transaction>
        store.transactions[index] = {
          ...store.transactions[index],
          ...patch,
          id,
          updatedAt: new Date().toISOString(),
        }
        return ok({ item: toDTO(store.transactions[index]) })
      }),
    ),
  }),

  // 删除
  remove: defineMock({
    url: '/api/ledger/:id',
    method: 'DELETE',
    response: respond(
      guard((req) => {
        const id = String(req.params?.id)
        const before = store.transactions.length
        store.transactions = store.transactions.filter((t) => t.id !== id)
        if (store.transactions.length === before) return err(404, '流水不存在')
        return ok({ ok: true })
      }),
    ),
  }),
}

export { getCategory }
