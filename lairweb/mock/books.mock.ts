import { defineMock } from 'vite-plugin-mock-dev-server'
import {
  store,
  type Book,
  type BookMember,
  type User,
  nextId,
  membersOf,
  userOf,
  respond,
  ok,
  err,
  guard,
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
    response: respond(
      guard(() => ok(store.books.map(toDTO))),
    ),
  }),

  // 建账本：{ name, type }，当前登录用户为 owner
  create: defineMock({
    url: '/api/books',
    method: 'POST',
    response: respond(
      guard((req, auth) => {
        const { name, type } = req.body ?? {}
        const b: Book = {
          id: nextId(store.books),
          name: String(name || '共享账本'),
          type: type === 'shared' ? 'shared' : 'personal',
          createdAt: new Date().toISOString(),
        }
        store.books.push(b)
        store.bookMembers.push({
          bookId: b.id,
          userId: auth.userId,
          role: 'owner',
          joinedAt: new Date().toISOString(),
        })
        return ok({ book: toDTO(b) })
      }),
    ),
  }),

  // 添加成员：{ userId }（或 { name } 新建用户）
  addMember: defineMock({
    url: '/api/books/:id/members',
    method: 'POST',
    response: respond(
      guard((req) => {
        const bookId = Number(req.params?.id)
        const { userId, name } = req.body ?? {}
        let uid = Number(userId)
        if (!uid && name) {
          const u: User = {
            id: nextId(store.users),
            name: String(name).slice(0, 12),
            avatarColor: ['#30d158', '#ff6b00', '#5e5ce6', '#ff375f', '#1d9bf0', '#ff9f0a'][Math.floor(Math.random() * 6)],
            createdAt: new Date().toISOString(),
          }
          store.users.push(u)
          uid = u.id
        }
        if (!uid) return err(400, '缺少成员信息')
        if (store.bookMembers.some((m) => m.bookId === bookId && m.userId === uid)) {
          return err(409, '该成员已在账本中')
        }
        store.bookMembers.push({ bookId, userId: uid, role: 'editor', joinedAt: new Date().toISOString() })
        const book = store.books.find((b) => b.id === bookId)
        if (!book) return err(404, '账本不存在')
        return ok({ book: toDTO(book) })
      }),
    ),
  }),

  // 移除成员（owner 不可移除）
  removeMember: defineMock({
    url: '/api/books/:id/members/:userId',
    method: 'DELETE',
    response: respond(
      guard((req) => {
        const bookId = Number(req.params?.id)
        const userId = Number(req.params?.userId)
        const m = store.bookMembers.find((x) => x.bookId === bookId && x.userId === userId)
        if (!m) return err(404, '该成员不在账本中')
        if (m.role === 'owner') return err(400, '不能移除账本创建者')
        store.bookMembers = store.bookMembers.filter((x) => !(x.bookId === bookId && x.userId === userId))
        const book = store.books.find((b) => b.id === bookId)
        return ok({ book: book ? toDTO(book) : undefined })
      }),
    ),
  }),
}
