import { defineMock } from 'vite-plugin-mock-dev-server'
import { store, CATEGORIES, type Transaction, guid, date } from './store'


function summary() {
  const income = store.transactions.filter((t) => t.type === '收入').reduce((s, t) => s + t.amount, 0)
  const expense = store.transactions.filter((t) => t.type === '支出').reduce((s, t) => s + t.amount, 0)
  return {
    income: Number(income.toFixed(2)),
    expense: Number(expense.toFixed(2)),
    balance: Number((income - expense).toFixed(2)),
  }
}

function categoryStats() {
  return CATEGORIES.map((name) => {
    const amount = store.transactions.filter((t) => t.type === '支出' && t.category === name).reduce((s, t) => s + t.amount, 0)
    return { name, amount: Number(amount.toFixed(2)), percent: 0 }
  })
    .filter((c) => c.amount > 0)
    .sort((a, b) => b.amount - a.amount)
}

export default {
  // 列表
  list: defineMock({
    url: '/api/ledger',
    method: 'GET',
    body: () => ({
      summary: summary(),
      categoryStats: categoryStats(),
      transactions: [...store.transactions].sort((a, b) => b.date.localeCompare(a.date)),
    }),
  }),

  // 新增
  create: defineMock({
    url: '/api/ledger',
    method: 'POST',
    body: (req) => {
      const { type, category, amount, date: reqDate, note } = req.body ?? {}
      const item: Transaction = {
        id: guid(),
        type: type === '收入' ? '收入' : '支出',
        category: String(category || '其他'),
        amount: Number(amount) || 0,
        date: String(reqDate || date()),
        note: String(note || ''),
      }
      store.transactions.push(item)
      return { ok: true, id: item.id, item }
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
      store.transactions[index] = { ...store.transactions[index], ...patch, id }
      return { ok: true, item: store.transactions[index] }
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
