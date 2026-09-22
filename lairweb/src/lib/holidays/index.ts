/**
 * 中国节假日 / 工作日判定
 *
 * 判定优先级（配置优先，未覆盖回退星期几）：
 *   1. 当年配置的 festivals 命中 → 法定节假日
 *   2. 当年配置的 workdays  命中 → 调休补班（周末上班）
 *   3. 周六 / 周日              → 休息
 *   4. 其余                    → 上班
 *
 * 边界处理：
 * - **跨年**：配置按「日期所属的日历年」索引。日历跨月渲染时，
 *   每个单元格必须用自身的年份取配置，不能沿用当前展示月份/年份。
 * - **年份缺失**：不静默当作周末——返回 degraded: true 让调用方可区分，
 *   同时在控制台给出一次性告警，提示补充该年份配置。
 * - **地区**：本模型只覆盖中国大陆（国办通知）。中国香港 / 中国澳门 / 中国台湾
 *   的节假日体系相互独立，需各自维护配置，勿混用本表。
 */

import { HOLIDAYS_2026 } from './2026'
import type { DayInfo, DayKind, YearConfig } from './types'

/** 年份 → 配置。新年份在发布后于此登记（年更脚本会生成对应文件）。 */
const REGISTRY: Record<number, YearConfig> = {
  2026: HOLIDAYS_2026,
}

/** 已告警过的年份，避免重复刷控制台 */
const warnedYears = new Set<number>()

/** 'MM-DD' 键（补零，与配置表一致） */
function monthDayKey(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${m}-${day}`
}

/** 取某年的配置；缺失时返回 undefined */
export function configOf(year: number): YearConfig | undefined {
  return REGISTRY[year]
}

/** 是否周六或周日 */
function isWeekend(d: Date): boolean {
  const w = d.getDay()
  return w === 0 || w === 6
}

/**
 * 判定某天的性质。
 * @param date 目标日期（使用其本地年/月/日，只取日期部分，忽略时间）
 */
export function dayInfo(date: Date): DayInfo {
  const cfg = configOf(date.getFullYear())
  const key = monthDayKey(date)

  if (!cfg) {
    // 配置缺失：按周末规则估算，并显式标记为降级结果
    if (!warnedYears.has(date.getFullYear())) {
      warnedYears.add(date.getFullYear())
      console.warn(
        `[holidays] 缺少 ${date.getFullYear()} 年的节假日配置，已按周末规则降级估算。` +
          `请在 lairweb/src/lib/holidays/ 下补充该年份配置并登记到 REGISTRY。`,
      )
    }
    return { kind: isWeekend(date) ? 'rest' : 'work', isMakeupWorkday: false, degraded: true }
  }

  const festival = cfg.festivals[key]
  if (festival) {
    return { kind: 'holiday', name: festival, isMakeupWorkday: false, degraded: false }
  }

  const makeup = cfg.workdays[key]
  if (makeup) {
    return { kind: 'work', name: makeup, isMakeupWorkday: true, degraded: false }
  }

  return { kind: isWeekend(date) ? 'rest' : 'work', isMakeupWorkday: false, degraded: false }
}

/** 便捷版：只要最终性质 */
export function dayKind(date: Date): DayKind {
  return dayInfo(date).kind
}

/** 是否休息日（法定节假日 + 周末 + 调休放假） */
export function isRestDay(date: Date): boolean {
  return dayKind(date) !== 'work'
}

/** 是否上班日（含调休补班） */
export function isWorkday(date: Date): boolean {
  return dayKind(date) === 'work'
}

/**
 * 徽标文案与语义（UI 消费）。
 * 三档：法定节假日 → 节日名；休息 → 休息；上班 → 上班。
 */
export interface DayBadge {
  /** 短文案，直接上屏 */
  label: string
  /** 语义档位，供样式类使用 */
  kind: DayKind | 'makeup'
  /** 是否调休补班（周末上班），UI 可弱提示 */
  isMakeupWorkday: boolean
}

export function dayBadge(date: Date): DayBadge {
  const info = dayInfo(date)
  if (info.kind === 'holiday') {
    return { label: info.name ?? '节日', kind: 'holiday', isMakeupWorkday: false }
  }
  if (info.kind === 'work') {
    return info.isMakeupWorkday
      ? { label: '上班', kind: 'makeup', isMakeupWorkday: true }
      : { label: '上班', kind: 'work', isMakeupWorkday: false }
  }
  return { label: '休息', kind: 'rest', isMakeupWorkday: false }
}

/**
 * 距下一个休息日还有几天（今天不算；今天已是休息日则返回 0）。
 * 用于顶栏「距下个休息日 N 天」提示。上限 400 天兜底，避免配置空档死循环。
 */
export function daysToNextRest(date: Date): number {
  const start = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  if (isRestDay(start)) return 0
  for (let i = 1; i <= 400; i++) {
    const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i)
    if (isRestDay(d)) return i
  }
  return -1
}
