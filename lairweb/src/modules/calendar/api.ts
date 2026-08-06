import { get, post, put, del } from '../../api/request'

export interface CalendarEvent {
  id: string
  title: string
  date: string
  time: string
  location: string
  done: boolean
}

export interface CreateEventInput {
  title: string
  date: string
  time: string
  location?: string
}

export const calendarApi = {
  list: () => get<{ events: CalendarEvent[] }>('/api/calendar'),
  create: (input: CreateEventInput) => post<{ ok: boolean; id: string }>('/api/calendar', input),
  update: (id: string, patch: Partial<CalendarEvent>) => put<{ ok: boolean }>(`/api/calendar/${id}`, patch),
  remove: (id: string) => del<{ ok: boolean }>(`/api/calendar/${id}`),
}
