import { get, post, put, del } from '../../api/request'

export interface Note {
  id: string
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
  create: (input: CreateNoteInput) => post<{ ok: boolean; id: string }>('/api/notes', input),
  update: (id: string, patch: Partial<Note>) => put<{ ok: boolean }>(`/api/notes/${id}`, patch),
  remove: (id: string) => del<{ ok: boolean }>(`/api/notes/${id}`),
}
