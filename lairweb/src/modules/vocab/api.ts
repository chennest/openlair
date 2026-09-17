import { get, post, put, del } from '../../api/request'

/**
 * 练习模式（四种模式测的是不同能力，别混）：
 * - follow 跟打     看词跟打 + **释义四选一**（不直显释义，答对才交卷）
 * - dictation 听写  只听发音拼写，释义直显当解题线索
 * - self_test 自测  看词选释义，不打字
 * - spell 默写      只给中文释义拼写（释义即题面，不能藏）
 */
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
  /** 连续答对次数：答对 +1，答错清零。掌握与否由它决定，不看 FSRS 的 stability */
  correctStreak: number
  /** 该词要求的连续答对次数：首次识词判断对=3、判断错/不认识=5；0=还没做过首次判断 */
  requiredStreak: number
  /** 首次识词判断结果：'' 未判断 / know 选对（眼熟）/ unsure 选错或点了不认识 */
  identifyResult: '' | 'know' | 'unsure'
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
  /**
   * newLearned/reviewed 来自进度表首学时间（不是作答次数）：
   * 同一个词在一节课里答多次只算「记了 1 个」，与每日目标口径一致。
   */
  today: {
    sessions: number
    words: number
    correct: number
    wrong: number
    durationSec: number
    newLearned: number
    reviewed: number
  }
  total: { sessions: number; words: number; correct: number; wrong: number; durationSec: number; learned: number; mastered: number; due: number }
}

/**
 * 每日背词目标（每用户一条，未设过则回缺省值 newTarget=10 / reviewTarget=30）。
 * 新词 / 复习两侧字段完全对称，两者都是「每日累计」配额：达标后该类词不再发放。
 */
export interface VocabDailyGoal {
  /** 每日新词目标 */
  newTarget: number
  /** 每日复习目标 */
  reviewTarget: number
  /** 今日已真正记住的新词数（首学时间落在今日的进度行） */
  todayNew: number
  /** 今日已复习的旧词数（今日回顾、且首次学习更早的词） */
  todayReviewed: number
  /** 今日新词还差几个达标（下限 0） */
  remaining: number
  /** 今日新词是否已达标 */
  achieved: boolean
  /** 今日复习还差几个达标（下限 0） */
  reviewRemaining: number
  /** 今日复习是否已达标 */
  reviewAchieved: boolean
  /** 从未改过目标时为 null */
  updatedAt: string | null
}

export interface AnswerInput {
  wordId: number
  correct: boolean
  /** 本次作答打错次数（自测选错传 1） */
  wrongTimes: number
  durationMs: number
}

/** 本地相对 UTC 的分钟差（东区为正）：后端据此折算「今天」零点与每日目标 */
const tzOffsetMinutes = () => -new Date().getTimezoneOffset()

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
  /**
   * 开课排课。不传 newLimit 时后端按「每日目标剩余量」发新词（达标后只发到期复习）；
   * 显式传值仍优先（留给「今天想多学一轮」）。tzOffset 默认带上，避免东区算错「今天」。
   */
  start: (input: { bookId: number; mode: VocabMode; source?: VocabSource; newLimit?: number; reviewLimit?: number }) =>
    post<StartSessionResult>('/api/vocab/practice/sessions', { tzOffset: tzOffsetMinutes(), ...input }),
  answer: (sessionId: number, input: AnswerInput) =>
    // tzOffset 必传：没掌握的词要压到「本地次日零点」再复习，不带时区就不知道次日零点在哪
    post<{ item: VocabProgress }>(`/api/vocab/practice/sessions/${sessionId}/answers`, {
      tzOffset: tzOffsetMinutes(),
      ...input,
    }),
  finish: (sessionId: number, durationSec: number) =>
    post<{ item: VocabSessionSummary }>(`/api/vocab/practice/sessions/${sessionId}/finish`, { durationSec }),
  wrong: () => get<{ words: QueueItem[] }>('/api/vocab/review/wrong'),
  collect: () => get<{ words: QueueItem[] }>('/api/vocab/review/collect'),
  updateProgress: (wordId: number, patch: { status?: 'learning' | 'mastered'; collected?: boolean; dismissWrong?: boolean }) =>
    put<{ item: VocabProgress }>(`/api/vocab/progress/${wordId}`, patch),
  /** tzOffset：本地相对 UTC 的分钟差（东区为正），后端按本地零点算“今日” */
  stats: () => get<VocabStats>(`/api/vocab/stats?tzOffset=${tzOffsetMinutes()}`),
  /** 每日背词目标 + 今日进度 */
  dailyGoal: () => get<VocabDailyGoal>(`/api/vocab/daily-goal?tzOffset=${tzOffsetMinutes()}`),
  /** 改每日目标（只提交出现的字段），返回改后的完整视图 */
  setDailyGoal: (patch: { newTarget?: number; reviewTarget?: number }) =>
    put<VocabDailyGoal>(`/api/vocab/daily-goal?tzOffset=${tzOffsetMinutes()}`, patch),
}
