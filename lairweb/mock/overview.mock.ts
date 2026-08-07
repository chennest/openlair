import { defineMock } from 'vite-plugin-mock-dev-server'
import { store, respond, ok, guard } from './store'

// 总揽页：从内存态聚合各模块真实数据
export default defineMock({
  url: '/api/overview',
  method: 'GET',
  response: respond(
    guard(() => {
      const expense = store.transactions.filter((t) => t.type === '支出').reduce((s, t) => s + t.amount, 0)
      return ok({
        monthExpense: {
          amount: Number(expense.toFixed(2)),
          budget: 6000,
          trend: -12.4,
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
