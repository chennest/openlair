import { defineMock } from 'vite-plugin-mock-dev-server'
import {
  store,
  type VocabProgressRow,
  type VocabSessionRow,
  type VocabWordItem,
  nextId,
  respond,
  ok,
  err,
  guard,
  type AuthContext,
} from './store'

// ---------- 契约 DTO（与后端 VocabService._word_dto / _progress_dto 同构） ----------

type WordDto = Omit<VocabWordItem, 'createdAt' | 'updatedAt'>

function wordDto(w: VocabWordItem): WordDto {
  const { createdAt: _c, updatedAt: _u, ...rest } = w
  return rest
}

function progressDto(p: VocabProgressRow | null) {
  if (!p) return null
  return {
    wordId: p.wordId,
    bookId: p.bookId,
    status: p.status,
    collected: p.collected,
    wrongCount: p.wrongCount,
    rightCount: p.rightCount,
    wrongActive: p.wrongActive,
    due: p.due ?? null,
    lastReview: p.lastReview ?? null,
    lastWrongAt: p.lastWrongAt ?? null,
    state: p.state,
    stability: p.stability ?? null,
    difficulty: p.difficulty ?? null,
    updatedAt: p.updatedAt,
  }
}

function queueItem(w: VocabWordItem, p: VocabProgressRow | null) {
  return { ...wordDto(w), progress: progressDto(p) }
}

// ---------- mock 简化调度（契约字段与 py-fsrs v6 对齐；间隔为近似值，真实调度以后端为准） ----------

const DAY_MS = 86400000
const nowISO = () => new Date().toISOString()

/** 答错=间隔 1 天记忆收缩；答对有错次=间隔 1 天；全对=间隔按稳定度增长 */
function schedule(p: VocabProgressRow | null, correct: boolean, wrongTimes: number) {
  const s0 = p?.stability ?? 0
  const d0 = p?.difficulty ?? 4.5
  let stability: number
  let intervalDays: number
  if (!correct) {
    stability = Math.max(0.6, s0 * 0.4)
    intervalDays = 1
  } else if (wrongTimes > 0) {
    stability = Math.max(0.8, s0 * 0.7)
    intervalDays = 1
  } else {
    stability = s0 < 1 ? 2.3 : s0 * 1.25
    intervalDays = Math.max(1, Math.round(stability))
  }
  const difficulty = Math.min(10, Math.max(1, correct ? d0 - (wrongTimes > 0 ? 0.5 : 0.9) : d0 + 1.2))
  return {
    stability: Number(stability.toFixed(4)),
    difficulty: Number(difficulty.toFixed(4)),
    state: 2, // Review
    step: null as number | null,
    due: new Date(Date.now() + intervalDays * DAY_MS).toISOString(),
    lastReview: nowISO(),
  }
}

// ---------- 排课（与后端 VocabService.start_session 同构） ----------

const MODES = ['follow', 'dictation', 'self_test', 'spell']
const DEFAULT_NEW_LIMIT = 10
const DEFAULT_REVIEW_LIMIT = 30

function reviewPool(userId: number, limit: number): VocabProgressRow[] {
  const now = Date.now()
  return store.vocabProgress
    .filter(
      (p) =>
        p.userId === userId &&
        p.status === 'learning' &&
        !!p.due &&
        new Date(p.due).getTime() <= now,
    )
    .sort((a, b) => String(a.due).localeCompare(String(b.due)) || a.id - b.id)
    .slice(0, limit)
}

function newWords(bookId: number, userId: number, limit: number): VocabWordItem[] {
  const learned = new Set(store.vocabProgress.filter((p) => p.userId === userId).map((p) => p.wordId))
  const wordIds = store.vocabBookWords.filter((bw) => bw.bookId === bookId).sort((a, b) => a.sort - b.sort)
  const out: VocabWordItem[] = []
  for (const bw of wordIds) {
    if (learned.has(bw.wordId)) continue
    const w = store.vocabWords.find((x) => x.id === bw.wordId)
    if (w) out.push(w)
    if (out.length >= limit) break
  }
  return out
}

/** 每本词书的学习统计（按词书成员资格归桶，与后端 book_progress_stats 同构） */
function bookStats(userId: number): Record<number, { learning: number; mastered: number; due: number }> {
  const bookOfWord = new Map<number, number[]>()
  for (const bw of store.vocabBookWords) {
    const list = bookOfWord.get(bw.wordId) ?? []
    list.push(bw.bookId)
    bookOfWord.set(bw.wordId, list)
  }
  const now = Date.now()
  const stats: Record<number, { learning: number; mastered: number; due: number }> = {}
  for (const p of store.vocabProgress) {
    if (p.userId !== userId) continue
    for (const bookId of bookOfWord.get(p.wordId) ?? []) {
      const s = (stats[bookId] ??= { learning: 0, mastered: 0, due: 0 })
      if (p.status === 'mastered') s.mastered += 1
      else {
        s.learning += 1
        if (p.due && new Date(p.due).getTime() <= now) s.due += 1
      }
    }
  }
  return stats
}

function getProgress(userId: number, wordId: number): VocabProgressRow | undefined {
  return store.vocabProgress.find((p) => p.userId === userId && p.wordId === wordId)
}

export default {
  // 词书列表（附我的进度）
  books: defineMock({
    url: '/api/vocab/books',
    method: 'GET',
    response: respond(
      guard((_req, auth: AuthContext) => {
        const userId = Number(auth.userId)
        const stats = bookStats(userId)
        return ok({
          books: store.vocabBooks
            .filter((b) => b.isEnabled)
            .sort((a, b) => a.sort - b.sort || a.id - b.id)
            .map((b) => {
              const s = stats[b.id] ?? { learning: 0, mastered: 0, due: 0 }
              return {
                id: b.id,
                slug: b.slug,
                name: b.name,
                lang: b.lang,
                emoji: b.emoji,
                description: b.description,
                wordCount: b.wordCount,
                learning: s.learning,
                mastered: s.mastered,
                due: s.due,
                createdAt: b.createdAt,
              }
            }),
        })
      }),
    ),
  }),

  // 词书单词分页
  bookWords: defineMock({
    url: '/api/vocab/books/:bookId/words',
    method: 'GET',
    response: respond(
      guard((req) => {
        const bookId = Number(req.params?.bookId)
        const book = store.vocabBooks.find((b) => b.id === bookId)
        if (!book) return err(404, '词书不存在')
        const limit = Math.min(500, Math.max(1, Number(req.query?.limit) || 100))
        const offset = Math.max(0, Number(req.query?.offset) || 0)
        const ordered = store.vocabBookWords
          .filter((bw) => bw.bookId === bookId)
          .sort((a, b) => a.sort - b.sort)
          .map((bw) => store.vocabWords.find((w) => w.id === bw.wordId))
          .filter((w): w is VocabWordItem => !!w)
        return ok({ total: book.wordCount, words: ordered.slice(offset, offset + limit).map(wordDto) })
      }),
    ),
  }),

  // 开课 + 排课（source: book 词书排课 / wrong 错词本 / collect 收藏复习）
  startSession: defineMock({
    url: '/api/vocab/practice/sessions',
    method: 'POST',
    response: respond(
      guard((req, auth: AuthContext) => {
        const userId = Number(auth.userId)
        const body = (req.body ?? {}) as { bookId?: number; mode?: string; source?: string; newLimit?: number; reviewLimit?: number }
        const mode = MODES.includes(String(body.mode)) ? String(body.mode) : null
        if (!mode) return err(400, '不支持的练习模式')
        const source = ['book', 'wrong', 'collect'].includes(String(body.source)) ? String(body.source) : 'book'
        const reviewLimit = Math.min(100, Math.max(1, Number(body.reviewLimit) || DEFAULT_REVIEW_LIMIT))
        const newLimit = Math.min(100, Math.max(0, Number(body.newLimit ?? DEFAULT_NEW_LIMIT)))

        let bookName = ''
        let sessionBookId = 0
        const queue: ReturnType<typeof queueItem>[] = []
        if (source === 'wrong' || source === 'collect') {
          const rows = store.vocabProgress
            .filter((p) =>
              p.userId === userId &&
              p.status === 'learning' &&
              (source === 'wrong' ? p.wrongActive : p.collected),
            )
            .sort((a, b) =>
              source === 'wrong'
                ? String(b.lastWrongAt ?? '').localeCompare(String(a.lastWrongAt ?? '')) || b.id - a.id
                : String(b.updatedAt).localeCompare(String(a.updatedAt)),
            )
            .slice(0, reviewLimit)
          for (const p of rows) {
            const w = store.vocabWords.find((x) => x.id === p.wordId)
            if (w) queue.push(queueItem(w, p))
          }
          bookName = source === 'wrong' ? '错词本' : '收藏复习'
          sessionBookId = 0
        } else {
          const book = store.vocabBooks.find((b) => b.id === Number(body.bookId))
          if (!book) return err(404, '词书不存在')
          sessionBookId = book.id
          bookName = book.name
          for (const p of reviewPool(userId, reviewLimit)) {
            const w = store.vocabWords.find((x) => x.id === p.wordId)
            if (w) queue.push(queueItem(w, p))
          }
          if (newLimit > 0) {
            for (const w of newWords(book.id, userId, newLimit)) queue.push(queueItem(w, null))
          }
        }
        if (!queue.length) {
          return err(400, source === 'book' ? '暂无可练习的单词（到期复习与新词均为空）' : '暂无可练习的单词')
        }

        const t = nowISO()
        const session: VocabSessionRow = {
          id: nextId(store.vocabSessions),
          userId,
          bookId: sessionBookId,
          mode,
          totalCount: 0,
          correctCount: 0,
          wrongCount: 0,
          durationSec: 0,
          createdAt: t,
          updatedAt: t,
        }
        store.vocabSessions.push(session)
        return ok({ id: session.id, bookId: sessionBookId, bookName, source, mode, queue })
      }),
    ),
  }),

  // 逐词上报
  answer: defineMock({
    url: '/api/vocab/practice/sessions/:sessionId/answers',
    method: 'POST',
    response: respond(
      guard((req, auth: AuthContext) => {
        const userId = Number(auth.userId)
        const session = store.vocabSessions.find((s) => s.id === Number(req.params?.sessionId))
        if (!session || session.userId !== userId) return err(404, '练习会话不存在')
        if (session.finishedAt) return err(400, '会话已结束')
        const body = (req.body ?? {}) as { wordId?: number; correct?: boolean; wrongTimes?: number; durationMs?: number }
        const word = store.vocabWords.find((w) => w.id === Number(body.wordId))
        if (!word) return err(404, '单词不存在')

        const correct = Boolean(body.correct)
        const wrongTimes = correct ? Math.max(0, Number(body.wrongTimes) || 0) : Math.max(1, Number(body.wrongTimes) || 0)
        const passed = correct && wrongTimes === 0
        const now = nowISO()

        let progress = getProgress(userId, word.id)
        if (!progress) {
          progress = {
            id: nextId(store.vocabProgress),
            userId,
            wordId: word.id,
            bookId: session.bookId,
            status: 'learning',
            collected: false,
            wrongCount: 0,
            rightCount: 0,
            wrongActive: false,
            state: 0,
            createdAt: now,
            updatedAt: now,
          }
          store.vocabProgress.push(progress)
        }
        Object.assign(progress, schedule(progress, correct, wrongTimes), {
          rightCount: progress.rightCount + (passed ? 1 : 0),
          wrongCount: progress.wrongCount + wrongTimes,
          wrongActive: !passed,
          lastWrongAt: passed ? progress.lastWrongAt : now,
          updatedAt: now,
        })

        session.totalCount += 1
        session.correctCount += passed ? 1 : 0
        session.wrongCount += passed ? 0 : 1
        session.updatedAt = now

        store.vocabLogs.push({
          id: nextId(store.vocabLogs),
          userId,
          sessionId: session.id,
          wordId: word.id,
          mode: session.mode,
          isCorrect: passed,
          wrongTimes,
          durationMs: Math.max(0, Number(body.durationMs) || 0),
          createdAt: now,
        })
        return ok({ item: progressDto(progress) })
      }),
    ),
  }),

  // 结束会话
  finish: defineMock({
    url: '/api/vocab/practice/sessions/:sessionId/finish',
    method: 'POST',
    response: respond(
      guard((req, auth: AuthContext) => {
        const userId = Number(auth.userId)
        const session = store.vocabSessions.find((s) => s.id === Number(req.params?.sessionId))
        if (!session || session.userId !== userId) return err(404, '练习会话不存在')
        const body = (req.body ?? {}) as { durationSec?: number }
        session.durationSec = Math.max(0, Number(body.durationSec) || 0)
        session.finishedAt = nowISO()
        session.updatedAt = nowISO()
        return ok({
          item: {
            id: session.id,
            bookId: session.bookId,
            mode: session.mode,
            totalCount: session.totalCount,
            correctCount: session.correctCount,
            wrongCount: session.wrongCount,
            durationSec: session.durationSec,
            finishedAt: session.finishedAt,
            createdAt: session.createdAt,
          },
        })
      }),
    ),
  }),

  // 错词本 / 收藏
  wrongBook: defineMock({
    url: '/api/vocab/review/wrong',
    method: 'GET',
    response: respond(
      guard((req, auth: AuthContext) => {
        const userId = Number(auth.userId)
        const limit = Math.min(500, Math.max(1, Number(req.query?.limit) || 200))
        const rows = store.vocabProgress
          .filter((p) => p.userId === userId && p.wrongActive && p.status === 'learning')
          .sort((a, b) => String(b.lastWrongAt ?? '').localeCompare(String(a.lastWrongAt ?? '')) || b.id - a.id)
          .slice(0, limit)
        const words = rows
          .map((p) => store.vocabWords.find((w) => w.id === p.wordId))
          .filter((w): w is VocabWordItem => !!w)
          .map((w) => queueItem(w, getProgress(userId, w.id) ?? null))
        return ok({ words })
      }),
    ),
  }),

  collectList: defineMock({
    url: '/api/vocab/review/collect',
    method: 'GET',
    response: respond(
      guard((req, auth: AuthContext) => {
        const userId = Number(auth.userId)
        const limit = Math.min(500, Math.max(1, Number(req.query?.limit) || 200))
        const rows = store.vocabProgress
          .filter((p) => p.userId === userId && p.collected)
          .sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)))
          .slice(0, limit)
        const words = rows
          .map((p) => store.vocabWords.find((w) => w.id === p.wordId))
          .filter((w): w is VocabWordItem => !!w)
          .map((w) => queueItem(w, getProgress(userId, w.id) ?? null))
        return ok({ words })
      }),
    ),
  }),

  // 标记进度（未学过的词也可直接标记）
  updateProgress: defineMock({
    url: '/api/vocab/progress/:wordId',
    method: 'PUT',
    response: respond(
      guard((req, auth: AuthContext) => {
        const userId = Number(auth.userId)
        const wordId = Number(req.params?.wordId)
        const body = (req.body ?? {}) as { status?: string; collected?: boolean; dismissWrong?: boolean }
        if (!store.vocabWords.some((w) => w.id === wordId)) return err(404, '单词不存在')
        let progress = getProgress(userId, wordId)
        if (!progress) {
          progress = {
            id: nextId(store.vocabProgress),
            userId,
            wordId,
            bookId: 0,
            status: 'learning',
            collected: false,
            wrongCount: 0,
            rightCount: 0,
            wrongActive: false,
            state: 0,
            createdAt: nowISO(),
            updatedAt: nowISO(),
          }
          store.vocabProgress.push(progress)
        }
        const now = nowISO()
        if (body.status === 'learning' || body.status === 'mastered') progress.status = body.status
        if (body.collected !== undefined && body.collected !== null) progress.collected = Boolean(body.collected)
        if (body.dismissWrong) progress.wrongActive = false
        progress.updatedAt = now
        return ok({ item: progressDto(progress) })
      }),
    ),
  }),

  // 统计（tzOffset：本地相对 UTC 的分钟差，按本地零点算“今日”，与后端同构）
  stats: defineMock({
    url: '/api/vocab/stats',
    method: 'GET',
    response: respond(
      guard((req, auth: AuthContext) => {
        const userId = Number(auth.userId)
        const tzOffset = Math.max(-840, Math.min(840, Number(req.query?.tzOffset) || 0))
        const nowDate = new Date()
        // 与后端同构：时间平移 tz 分钟后取零点，再平移回 UTC
        const shifted = new Date(nowDate.getTime() + tzOffset * 60000)
        shifted.setUTCHours(0, 0, 0, 0)
        const dayStart = new Date(shifted.getTime() - tzOffset * 60000)
        const mine = store.vocabSessions.filter((s) => s.userId === userId)
        const today = mine.filter((s) => new Date(s.createdAt).getTime() >= dayStart.getTime())
        const progress = store.vocabProgress.filter((p) => p.userId === userId)
        const now = nowDate.getTime()
        const summarize = (rows: VocabSessionRow[]) => ({
          sessions: rows.length,
          words: rows.reduce((m, r) => m + r.totalCount, 0),
          correct: rows.reduce((m, r) => m + r.correctCount, 0),
          wrong: rows.reduce((m, r) => m + r.wrongCount, 0),
          durationSec: rows.reduce((m, r) => m + r.durationSec, 0),
        })
        return ok({
          today: summarize(today),
          total: {
            ...summarize(mine),
            learned: progress.length,
            mastered: progress.filter((p) => p.status === 'mastered').length,
            due: progress.filter(
              (p) => p.status === 'learning' && p.due && new Date(p.due).getTime() <= now,
            ).length,
          },
        })
      }),
    ),
  }),
}
