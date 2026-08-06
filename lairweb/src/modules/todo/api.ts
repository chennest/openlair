import { get, post, put, del } from '../../api/request'

export interface TodoItem {
  id: string
  text: string
  quadrant: string
  done: boolean
  due: string
}

export interface CreateTodoInput {
  text: string
  quadrant: string
  due: string
}

export const QUADRANTS = ['重要紧急', '重要不紧急', '紧急不重要', '不重要不紧急']
export const DUES = ['今天', '明天', '本周', '下月', '无期限']

export const todoApi = {
  list: () => get<{ todos: TodoItem[] }>('/api/todo'),
  create: (input: CreateTodoInput) => post<{ ok: boolean; id: string }>('/api/todo', input),
  update: (id: string, patch: Partial<TodoItem>) => put<{ ok: boolean }>(`/api/todo/${id}`, patch),
  remove: (id: string) => del<{ ok: boolean }>(`/api/todo/${id}`),
}
