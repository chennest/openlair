import { get, post, put, del } from '../../api/request'

export interface Habit {
  id: string
  name: string
  streak: number
  done: boolean
  week: boolean[]
}

export interface UpdateHabitInput {
  done?: boolean
  streak?: number
  week?: boolean[]
}

export const habitApi = {
  list: () => get<{ habits: Habit[] }>('/api/habits'),
  create: (name: string) => post<{ ok: boolean; id: string }>('/api/habits', { name }),
  update: (id: string, patch: UpdateHabitInput) => put<{ ok: boolean }>(`/api/habits/${id}`, patch),
  remove: (id: string) => del<{ ok: boolean }>(`/api/habits/${id}`),
}
