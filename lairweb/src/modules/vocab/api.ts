import { get, post, put, del } from '../../api/request'

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
  /** null=系统级词书（人人可见）；非空=用户级词书（ ownerId 即导入者 id） */
  ownerId: number | null
  wordCount: number
  /** 进度统计由后端按词书成员资格计算（mock 同契约） */
  learning: number
  mastered: number
  /** 到期待复习数 */
  due: number
  createdAt: string
}

export type VocabImportScope = 'system' | 'user'

export interface ImportBooksResult {
  book: VocabBook
  /** 导入的单词数（文本内去重后） */
  imported: number
  /** 全局词库中新建的词条数（已存在的词不重复建） */
  newWords: number
  /** 识别的格式：anki / ecdict / simple */
  format: string
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

/** 练习模式覆盖：该词在四种模式里各被练过多少次（全局口径，不区分词书/来源） */
export interface VocabPracticeStat {
  follow: number
  dictation: number
  selfTest: number
  spell: number
  totalCount: number
  lastAt: string | null
}

/** 词书详情页单词：词条 + 本人进度 + 练习模式覆盖 */
export interface BookWordItem extends VocabWord {
  progress: VocabProgress | null
  practice: VocabPracticeStat
}

/** 详情页状态筛选 */
export type VocabWordFilter = 'all' | 'unlearned' | 'learning' | 'mastered' | 'wrong' | 'collected'

/** 详情页排序：order 词书顺序 / freq 词频 / wrong 错次最多 / recent 最近练习过 */
export type VocabWordSort = 'order' | 'freq' | 'wrong' | 'recent'

export interface BookWordsResult {
  /** 当前筛选条件下的条数 */
  total: number
  /** 词书总词数 */
  totalAll: number
  words: BookWordItem[]
}

export interface BookSummary {
  book: VocabBook
  total: number
  learned: number
  learning: number
  mastered: number
  due: number
  wrong: number
  collected: number
  unlearned: number
}

/** 练习来源：book 词书排课 / wrong 错词本 / collect 收藏复习 */
export type VocabSource = 'book' | 'wrong' | 'collect'

export interface StartSessionResult {
  id: number
  bookId: number
  /** 词书名；错词本/收藏练习为对应名称 */
  bookName: string
  source: VocabSource
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
  importBooks: (input: { name?: string; scope: VocabImportScope; lang?: string; text: string }) =>
    post<ImportBooksResult>('/api/vocab/books/import', input),
  deleteBook: (bookId: number) => del<{ ok: boolean }>(`/api/vocab/books/${bookId}`),
  /** 词书内单词分页（详情页用）：带进度与模式覆盖，支持状态筛选 / 关键词 / 排序 */
  bookWords: (
    bookId: number,
    limit = 100,
    offset = 0,
    filter: { status?: VocabWordFilter; keyword?: string; sort?: VocabWordSort } = {},
  ) => {
    const qs = new URLSearchParams({ limit: String(limit), offset: String(offset) })
    if (filter.status && filter.status !== 'all') qs.set('status', filter.status)
    if (filter.keyword) qs.set('keyword', filter.keyword)
    if (filter.sort) qs.set('sort', filter.sort)
    return get<BookWordsResult>(`/api/vocab/books/${bookId}/words?${qs.toString()}`)
  },
  /** 词书详情页头部汇总（词书信息 + 各状态计数） */
  bookSummary: (bookId: number) => get<BookSummary>(`/api/vocab/books/${bookId}/summary`),
  start: (input: { bookId: number; mode: VocabMode; source?: VocabSource; newLimit?: number; reviewLimit?: number }) =>
    post<StartSessionResult>('/api/vocab/practice/sessions', input),
  answer: (sessionId: number, input: AnswerInput) =>
    post<{ item: VocabProgress }>(`/api/vocab/practice/sessions/${sessionId}/answers`, input),
  finish: (sessionId: number, durationSec: number) =>
    post<{ item: VocabSessionSummary }>(`/api/vocab/practice/sessions/${sessionId}/finish`, { durationSec }),
  wrong: () => get<{ words: QueueItem[] }>('/api/vocab/review/wrong'),
  collect: () => get<{ words: QueueItem[] }>('/api/vocab/review/collect'),
  updateProgress: (wordId: number, patch: { status?: 'learning' | 'mastered'; collected?: boolean; dismissWrong?: boolean }) =>
    put<{ item: VocabProgress }>(`/api/vocab/progress/${wordId}`, patch),
  /** tzOffset：本地相对 UTC 的分钟差（东区为正），后端按本地零点算“今日” */
  stats: () => get<VocabStats>(`/api/vocab/stats?tzOffset=${-new Date().getTimezoneOffset()}`),
}
