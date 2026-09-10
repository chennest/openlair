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
  visibleCategories,
  categoryExists,
  createCategory,
  renameCategory,
  categoryUsageCount,
  removeCategory,
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
  // 分类表：系统预置 + 可见自定义。?type= 过滤；?bookId= 共享账本成员共用
  categories: defineMock({
    url: '/api/ledger/categories',
    method: 'GET',
    response: respond(
      guard((req, auth) => {
        const type = String(req.query?.type ?? '') as '支出' | '收入' | ''
        const bookId = Number(req.query?.bookId) || undefined
        let userIds: number[] | undefined
        if (bookId) {
          const memberIds = store.bookMembers.filter((m) => m.bookId === bookId).map((m) => Number(m.userId))
          userIds = memberIds.length ? memberIds : [Number(auth.userId)]
        } else {
          userIds = [Number(auth.userId)]
        }
        const rows = type ? visibleCategories(userIds, type) : visibleCategories(userIds)
        return ok(rows.map((c) => ({ ...c })))
      }),
    ),
  }),

  // 新增自定义分类（仅本人；与系统预置/本人已有重名 → 409）
  createCategory: defineMock({
    url: '/api/ledger/categories',
    method: 'POST',
    response: respond(
      guard((req, auth) => {
        const { name, type } = req.body ?? {}
        const n = String(name ?? '').trim()
        const t = type === '收入' ? '收入' : '支出'
        if (!n) return err(400, '分类名不能为空')
        if (n.length > 20) return err(400, '分类名最长 20 字')
        if (categoryExists(n, t, Number(auth.userId))) return err(409, `「${n}」已存在（系统预置或你已创建）`)
        return ok(createCategory(n, t, Number(auth.userId)))
      }),
    ),
  }),

  // 改名（仅本人创建的分类可改）
  renameCategory: defineMock({
    url: '/api/ledger/categories/:id',
    method: 'PUT',
    response: respond(
      guard((req, auth) => {
        const id = Number(req.params?.id)
        const c = getCategory(id)
        if (!c) return err(404, '分类不存在')
        if (c.userId === null) return err(403, '系统预置分类不可修改')
        if (Number(c.userId) !== Number(auth.userId)) return err(403, '只能修改自己创建的分类')
        const n = String(req.body?.name ?? '').trim()
        if (!n) return err(400, '分类名不能为空')
        if (n.length > 20) return err(400, '分类名最长 20 字')
        if (n !== c.name && categoryExists(n, c.type, Number(auth.userId), id)) {
          return err(409, `「${n}」已存在（系统预置或你已创建）`)
        }
        return ok(renameCategory(id, n))
      }),
    ),
  }),

  // 删除（仅本人创建；挂有流水 → 409 拒绝）
  removeCategory: defineMock({
    url: '/api/ledger/categories/:id',
    method: 'DELETE',
    response: respond(
      guard((req, auth) => {
        const id = Number(req.params?.id)
        const c = getCategory(id)
        if (!c) return err(404, '分类不存在')
        if (c.userId === null) return err(403, '系统预置分类不可删除')
        if (Number(c.userId) !== Number(auth.userId)) return err(403, '只能删除自己创建的分类')
        const usage = categoryUsageCount(id)
        if (usage > 0) return err(409, `「${c.name}」下有 ${usage} 条流水，请先迁移流水后再删除`)
        removeCategory(id)
        return ok({ ok: true })
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
        const pageSize = Number(req.query?.pageSize) || 10
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

  // 更新（注意：Transaction.id 是 number，路径参数必须转 number 再比较——
  // 旧实现 String() 后严格比较恒 false，导致 mock 下编辑静默失效）
  update: defineMock({
    url: '/api/ledger/:id',
    method: 'PUT',
    response: respond(
      guard((req) => {
        const id = Number(req.params?.id)
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

  // 删除（同上：number 比较修复）
  remove: defineMock({
    url: '/api/ledger/:id',
    method: 'DELETE',
    response: respond(
      guard((req) => {
        const id = Number(req.params?.id)
        const before = store.transactions.length
        store.transactions = store.transactions.filter((t) => t.id !== id)
        if (store.transactions.length === before) return err(404, '流水不存在')
        return ok({ ok: true })
      }),
    ),
  }),
}

export { getCategory }
