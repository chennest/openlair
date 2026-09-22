/**
 * 节假日数据模型 —— 稀疏配置（sparse config）
 *
 * 设计参考 JayceChant/goliday 的「稀疏表 + 最终态」思路：
 * 只记录**被官方调整过**的日期，普通工作日与普通周末一律由星期几推导，
 * 永不落盘。所以一年份的配置只有 20~40 条，人工可审计。
 *
 * 术语（易混，务必按此口径）：
 * - 法定节假日 festivals：有节日名的放假日子（如 10-01 国庆节）
 * - 调休放假            ：工作日被调成休息（如 10-05 周一 → 休），首版并入「休息」展示
 * - 调休补班 workdays  ：周末被调成上班（如 09-20 周日 → 班），最需要提醒的一类
 *
 * 注意：口语里的「补休」与规范用词「调休补班」方向相反，本模型统一用「调休补班」。
 */

/** 日期键：'MM-DD'（省略年份，因为配置本身按年组织） */
export type MonthDay = string

/** 单个年份的节假日调整配置 */
export interface YearConfig {
  /** 完整年份，如 2026 */
  year: number
  /** 数据来源（国务院办公厅通知原文 URL），便于溯源与年更核对 */
  source: string
  /**
   * 法定节假日（放假）：'MM-DD' → 节日名
   * 只收节日当天，以及由调休换来的放假日在 UI 上并入「休息」，故此表只放有名字的节日
   */
  festivals: Record<MonthDay, string>
  /** 调休补班（周末上班）：'MM-DD' → 所补的节日名 */
  workdays: Record<MonthDay, string>
}

/** 一天的最终性质（UI 直接消费） */
export type DayKind = 'holiday' | 'rest' | 'work'

/** 判定结果：性质 + 可选的节日名/所补节日名 */
export interface DayInfo {
  kind: DayKind
  /** 节日名（kind === 'holiday' 时存在；调休补班时为所补的节日名） */
  name?: string
  /** 是否为调休补班（周末上班），UI 可用于弱提示 */
  isMakeupWorkday: boolean
  /**
   * 该结果是否来自降级路径（当年份配置缺失时按周日/周六规则估算）
   * 用于 UI/日志区分「确定结果」与「估算结果」
   */
  degraded: boolean
}
