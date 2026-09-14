// 词汇模块展示语义的唯一来源：状态色调 + 行内文案
//
// 使用方式：
// 1) Badge 根是 reka Primitive，父组件 scoped 类不可靠（本仓 overview/index.vue 有原始注释），
//    配色一律走这里的 Tailwind utility。
// 2) 带色调的 Badge 用 variant="ghost" —— ghost 不带基础 bg-/text-，
//    无需依赖 cn/twMerge 的覆盖顺序就能让色调稳稳落地。
// 3) 不要拿构建产 CSS 的字节顺序去推断类冲突：cn() = clsx + twMerge，
//    冲突在合并期就按「后者胜」消解了，根本不会同时落到 DOM 上。

import type { VocabProgress, VocabTranslation } from './api'

type VocabTone = 'gray' | 'blue' | 'green' | 'red' | 'gold'

const TONES: Record<VocabTone, string> = {
  gray: 'text-[var(--text-2)] bg-[rgba(0,0,0,0.05)]',
  blue: 'text-[var(--accent)] bg-[rgba(var(--accent-rgb),0.1)]',
  green: 'text-[#0a5a2c] bg-[rgba(48,209,88,0.16)]',
  red: 'text-[var(--heat)] bg-[var(--heat-bg)]',
  gold: 'text-white bg-[var(--accent)]',
}

/** 取 Badge 的色调 utility */
export function tone(t: VocabTone): string {
  return TONES[t]
}

interface StatusMeta {
  label: string
  tone: VocabTone
}

/** 单词学习状态：未学（无进度记录）/ 学习中 / 已记住 */
const STATUS_META: Record<'unlearned' | NonNullable<VocabProgress['status']>, StatusMeta> = {
  unlearned: { label: '未学', tone: 'gray' },
  learning: { label: '学习中', tone: 'blue' },
  mastered: { label: '已记住', tone: 'green' },
}

export function statusMeta(status?: VocabProgress['status'] | null): StatusMeta {
  return status ? STATUS_META[status] : STATUS_META.unlearned
}

/**
 * 人工标记文案（动词在前）。
 * 状态标签说「已记住」，动作按钮说「标记记住 / 取消记住」——
 * 两者措辞必须分离，否则一排按钮会被读成「这些词我已经记住了」。
 */
export const MASTER_LABEL = '标记记住'
export const UNMASTER_LABEL = '取消记住'

/** 单词行释义摘要：默认取前 2 条，拼成 `pos cn；pos cn` */
export function wordMeaning(translations: VocabTranslation[], limit = 2): string {
  return translations
    .slice(0, limit)
    .map((t) => `${t.pos} ${t.cn}`)
    .join('；')
}

/** 复习时间文案：待复习 / 明天复习 / N 天后复习；无到期时间返回空串 */
export function reviewDueText(due?: string | null): string {
  if (!due) return ''
  const days = Math.ceil((new Date(due).getTime() - Date.now()) / 86400000)
  if (days <= 0) return '待复习'
  if (days === 1) return '明天复习'
  return `${days} 天后复习`
}

/**
 * 掌握进度文案：「已连对 1/3 · 还差 2 次」/「已记住 · 不再安排复习」。
 *
 * 掌握与否由**连续答对次数**决定（答对 +1、答错清零），不看 FSRS 的 stability ——
 * 否则一次答对就会被排到很久以后，体感等同于「一次就对就掌握了」。
 * requiredStreak=0 表示还没做过首次识词判断，返回空串（不展示）。
 */
export function masteryText(p?: VocabProgress | null): string {
  if (!p || p.requiredStreak <= 0) return ''
  if (p.status === 'mastered') return '已记住 · 不再安排复习'
  const left = Math.max(0, p.requiredStreak - p.correctStreak)
  return `已连对 ${p.correctStreak}/${p.requiredStreak} · 还差 ${left} 次`
}
