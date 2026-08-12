import { defineMock } from 'vite-plugin-mock-dev-server'
import { store, respond, ok, guard, MONTH, currentBudget } from './store'

// 总览页：从内存态聚合各模块真实数据（语义与后端 OverviewService 对齐）
export default defineMock({
  url: '/api/overview',
  method: 'GET',
  response: respond(
    guard(() => {
      const month = MONTH()
      const prevDate = new Date()
      prevDate.setDate(0) // 上月最后一天
      const prevMonth = `${prevDate.getFullYear()}-${String(prevDate.getMonth() + 1).padStart(2, '0')}`

      const monthExpense = store.transactions
        .filter((t) => t.type === '支出' && t.date.startsWith(month))
        .reduce((s, t) => s + t.amount, 0)
      const prevExpense = store.transactions
        .filter((t) => t.type === '支出' && t.date.startsWith(prevMonth))
        .reduce((s, t) => s + t.amount, 0)
      const trend = prevExpense ? Number((((monthExpense - prevExpense) / prevExpense) * 100).toFixed(1)) : 0

      return ok({
        monthExpense: {
          amount: Number(monthExpense.toFixed(2)),
          budget: currentBudget(1).expenseLimit,
          trend,
        },
        todos: store.todos.filter((t) => !t.done).slice(0, 4).map((t) => ({
          text: t.text,
          time: t.due,
          tag: t.quadrant,
          tagClass: t.quadrant === '重要紧急' ? 'red' : 'gray',
        })),
        upcoming: store.events.slice(0, 3).map((e) => ({
          text: e.title,
          date: `${e.date} ${e.time}`,
          tag: '日程',
          tagClass: 'green',
        })),
        habits: store.habits.slice(0, 4).map((h) => ({ name: h.name, done: h.done })),
      })
    }),
  ),
})
