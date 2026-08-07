import { defineMock } from 'vite-plugin-mock-dev-server'
import {
  store,
  type Book,
  type BookMember,
  type User,
  guid,
  membersOf,
  userOf,
} from './store'

/** 账本 DTO：带成员（含用户信息） */
interface BookDTO extends Book {
  members: (BookMember & { user: User | undefined })[]
}

function toDTO(b: Book): BookDTO {
  return {
    ...b,
    members: membersOf(b.id).map((m) => ({ ...m, user: userOf(m.userId) })),
  }
}

export default {
  // 账本列表（全部账本；单用户场景不分权限）
  list: defineMock({
    url: '/api/books',
    method: 'GET',
    body: () => store.books.map(toDTO),
  }),

  // 建账本：{ name, type }，当前用户为 owner
  create: defineMock({
    url: '/api/books',
    method: 'POST',
    body: (req) => {
      const { name, type } = req.body ?? {}
      const b: Book = {
        id: guid(),
        name: String(name || '共享账本'),
        type: type === 'shared' ? 'shared' : 'personal',
        createdAt: new Date().toISOString(),
      }
      store.books.push(b)
      store.bookMembers.push({
        bookId: b.id,
        userId: 'u-me',
        role: 'owner',
        joinedAt: new Date().toISOString(),
      })
      return { ok: true, book: toDTO(b) }
    },
  }),

  // 添加成员：{ userId }（或 { name } 新建用户）
  addMember: defineMock({
    url: '/api/books/:id/members',
    method: 'POST',
    body: (req) => {
      const bookId = String(req.params?.id)
      const { userId, name } = req.body ?? {}
      let uid = String(userId || '')
      if (!uid && name) {
        const u: User = {
          id: guid(),
          name: String(name).slice(0, 12),
          avatarColor: ['#30d158', '#ff6b00', '#5e5ce6', '#ff375f', '#1d9bf0', '#ff9f0a'][Math.floor(Math.random() * 6)],
          createdAt: new Date().toISOString(),
        }
        store.users.push(u)
        uid = u.id
      }
      if (!uid) return { ok: false, error: 'missing user' }
      if (store.bookMembers.some((m) => m.bookId === bookId && m.userId === uid)) {
        return { ok: false, error: 'already a member' }
      }
      store.bookMembers.push({ bookId, userId: uid, role: 'editor', joinedAt: new Date().toISOString() })
      const book = store.books.find((b) => b.id === bookId)
      return { ok: true, book: book ? toDTO(book) : undefined }
    },
  }),

  // 移除成员（owner 不可移除）
  removeMember: defineMock({
    url: '/api/books/:id/members/:userId',
    method: 'DELETE',
    body: (req) => {
      const bookId = String(req.params?.id)
      const userId = String(req.params?.userId)
      const m = store.bookMembers.find((x) => x.bookId === bookId && x.userId === userId)
      if (!m) return { ok: false, error: 'not a member' }
      if (m.role === 'owner') return { ok: false, error: 'cannot remove owner' }
      store.bookMembers = store.bookMembers.filter((x) => !(x.bookId === bookId && x.userId === userId))
      const book = store.books.find((b) => b.id === bookId)
      return { ok: true, book: book ? toDTO(book) : undefined }
    },
  }),
}
