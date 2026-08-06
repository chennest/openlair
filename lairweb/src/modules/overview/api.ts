import { get } from '../../api/request'

export interface OverviewTodo {
  text: string
  time: string
  tag: string
  tagClass: string
}

export interface OverviewEvent {
  text: string
  date: string
  tag: string
  tagClass: string
}

export interface OverviewHabit {
  name: string
  done: boolean
}

export interface OverviewData {
  monthExpense: { amount: number; budget: number; trend: number }
  todos: OverviewTodo[]
  upcoming: OverviewEvent[]
  habits: OverviewHabit[]
}

export const overviewApi = {
  get: () => get<OverviewData>('/api/overview'),
}
