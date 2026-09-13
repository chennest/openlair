import { get, post, put } from '../../api/request'

/** 练习模式：follow 跟打 / dictation 听写 / self_test 自测 / spell 默写 */
export type VocabMode = 'follow' | 'dictation' | 'self_test' | 'spell'

export const VOCAB_MODES: Array<{ value: VocabMode; label: string }> = [
  { value: 'follow', label: '跟打' },
  { value: 'dictation', label: '听写' },
  { value: 'self_test', label: '自测' },
  { value: 'spell', label: '默写' },
]

export interface VocabBook {
  id: number
  slug: string
  name: string
  lang: string
  emoji: string
  description: string
  wordCount: number
  /** 进度统计由后端按词书成员资格计算（mock 同契约） */
  learning: number
  mastered: number
  /** 到期待复习数 */
  due: number
  createdAt: string
}

export interface VocabTranslation {
  pos: string
  cn: string
}
export interface VocabSentence {
  en: string
  cn: string
}

/** 单词 DTO（不含时间戳字段） */
export interface VocabWord {
  id: number
  word: string
  phoneticUs: string
  phoneticUk: string
  translations: VocabTranslation[]
  sentences: VocabSentence[]
  phrases: string[]
  synos: Array<{ pos: string; ws: string[] }>
  relWords: { root: string; rels: Array<{ pos: string; words: Array<{ c: string; cn: string }> }> }
  freq: number
}

/** 学习进度（FSRS 卡片）：due 为下次到期时间，state 0=未复习 1=Learning 2=Review 3=Relearning */
export interface VocabProgress {
  wordId: number
  bookId: number
  status: 'learning' | 'mastered'
  collected: boolean
  wrongCount: number
  rightCount: number
  wrongActive: boolean
  due: string | null
  lastReview: string | null
  lastWrongAt: string | null
  state: number
  stability: number | null
  difficulty: number | null
  updatedAt: string
}

/** 练习队列项：单词 + 当前进度（新词为 null） */
export interface QueueItem extends VocabWord {
  progress: VocabProgress | null
}

export interface StartSessionResult {
  id: number
  bookId: number
  mode: VocabMode
  queue: QueueItem[]
}

export interface VocabSessionSummary {
  id: number
  bookId: number
  mode: VocabMode
  totalCount: number
  correctCount: number
  wrongCount: number
  durationSec: number
  finishedAt: string | null
  createdAt: string
}

export interface VocabStats {
  today: { sessions: number; words: number; correct: number; wrong: number; durationSec: number }
  total: { sessions: number; words: number; correct: number; wrong: number; durationSec: number; learned: number; mastered: number; due: number }
}

export interface AnswerInput {
  wordId: number
  correct: boolean
  /** 本次作答打错次数（自测选错传 1） */
  wrongTimes: number
  durationMs: number
}

export const vocabApi = {
  books: () => get<{ books: VocabBook[] }>('/api/vocab/books'),
  bookWords: (bookId: number, limit = 100, offset = 0) =>
    get<{ total: number; words: VocabWord[] }>(`/api/vocab/books/${bookId}/words?limit=${limit}&offset=${offset}`),
  start: (input: { bookId: number; mode: VocabMode; newLimit?: number; reviewLimit?: number }) =>
    post<StartSessionResult>('/api/vocab/practice/sessions', input),
  answer: (sessionId: number, input: AnswerInput) =>
    post<{ item: VocabProgress }>(`/api/vocab/practice/sessions/${sessionId}/answers`, input),
  finish: (sessionId: number, durationSec: number) =>
    post<{ item: VocabSessionSummary }>(`/api/vocab/practice/sessions/${sessionId}/finish`, { durationSec }),
  wrong: () => get<{ words: QueueItem[] }>('/api/vocab/review/wrong'),
  collect: () => get<{ words: QueueItem[] }>('/api/vocab/review/collect'),
  updateProgress: (wordId: number, patch: { status?: 'learning' | 'mastered'; collected?: boolean; dismissWrong?: boolean }) =>
    put<{ item: VocabProgress }>(`/api/vocab/progress/${wordId}`, patch),
  stats: () => get<VocabStats>('/api/vocab/stats'),
}
