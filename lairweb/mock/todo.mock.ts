import { defineMock } from 'vite-plugin-mock-dev-server'
import { store, QUADRANTS, type TodoItem, nextId, respond, ok, err, guard } from './store'


export default {
  // 列表
  list: defineMock({
    url: '/api/todo',
    method: 'GET',
    response: respond(
      guard(() => ok({ todos: store.todos })),
    ),
  }),

  // 新增
  create: defineMock({
    url: '/api/todo',
    method: 'POST',
    response: respond(
      guard((req) => {
        const { text, quadrant, due } = req.body ?? {}
        const item: TodoItem = {
          id: nextId(store.todos),
          text: String(text || ''),
          quadrant: QUADRANTS.includes(String(quadrant)) ? String(quadrant) : QUADRANTS[1],
          done: false,
          due: String(due || '今天'),
        }
        store.todos.push(item)
        return ok({ id: item.id, item })
      }),
    ),
  }),

  // 更新（勾选完成 / 改象限 / 改截止）
  update: defineMock({
    url: '/api/todo/:id',
    method: 'PUT',
    response: respond(
      guard((req) => {
        const id = String(req.params?.id)
        const index = store.todos.findIndex((t) => t.id === id)
        if (index < 0) return err(404, '待办不存在')
        const patch = (req.body ?? {}) as Partial<TodoItem>
        store.todos[index] = { ...store.todos[index], ...patch, id }
        return ok({ item: store.todos[index] })
      }),
    ),
  }),

  // 删除
  remove: defineMock({
    url: '/api/todo/:id',
    method: 'DELETE',
    response: respond(
      guard((req) => {
        const id = String(req.params?.id)
        const before = store.todos.length
        store.todos = store.todos.filter((t) => t.id !== id)
        if (store.todos.length === before) return err(404, '待办不存在')
        return ok({ ok: true })
      }),
    ),
  }),
}
