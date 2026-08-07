import { get, post, put, del } from '../../api/request'

export interface Note {
  id: number
  title: string
  summary: string
  tags: string[]
  updatedAt: string
}

export interface CreateNoteInput {
  title: string
  summary: string
  tags: string[]
}

export const noteApi = {
  list: () => get<{ notes: Note[] }>('/api/notes'),
  create: (input: CreateNoteInput) => post<{ ok: boolean; id: number }>('/api/notes', input),
  update: (id: number, patch: Partial<Note>) => put<{ ok: boolean }>(`/api/notes/${id}`, patch),
  remove: (id: number) => del<{ ok: boolean }>(`/api/notes/${id}`),
}
