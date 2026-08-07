import { get, post, put, del } from '../../api/request'

export interface Habit {
  id: number
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
  create: (name: string) => post<{ ok: boolean; id: number }>('/api/habits', { name }),
  update: (id: number, patch: UpdateHabitInput) => put<{ ok: boolean }>(`/api/habits/${id}`, patch),
  remove: (id: number) => del<{ ok: boolean }>(`/api/habits/${id}`),
}
