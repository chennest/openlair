#!/usr/bin/env node
/**
 * gen-holidays.mjs —— 节假日配置年更脚本
 *
 * 用途：每年 11 月国务院办公厅发布次年放假安排后，一条命令生成
 *       lairweb/src/lib/holidays/<year>.ts，避免手抄日期出错。
 *
 * 数据源（二选一）：
 *   --remote   从 holiday-cn 拉取（CI 每日抓取 gov.cn，带 papers 溯源，推荐）
 *   --file <p> 从本地 holiday-cn 格式 JSON 读取（离线/内网环境用）
 *   --paper <u> 指定国务院通知原文 URL（默认沿用 holiday-cn 的 papers[0]）
 *
 * 用法：
 *   node scripts/gen-holidays.mjs --year 2027 --remote
 *   node scripts/gen-holidays.mjs --year 2027 --file ./2027.json
 *   node scripts/gen-holidays.mjs --year 2027 --remote --check   # 只校验不写文件
 *
 * 生成后务必人工抽查 3~5 个日期（尤其春节/国庆的调休首尾日），再提交。
 *
 * 参考实现：NateScarlet/holiday-cn（数据）、JayceChant/goliday（稀疏表 + 校验思路）
 */

import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '..')
const OUT_DIR = resolve(ROOT, 'lairweb/src/lib/holidays')
const CDN = 'https://cdn.jsdelivr.net/gh/NateScarlet/holiday-cn@master'

// ── 参数解析 ──
function parseArgs(argv) {
  const args = { year: null, remote: false, file: null, paper: null, check: false }
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    if (a === '--year') args.year = Number(argv[++i])
    else if (a === '--remote') args.remote = true
    else if (a === '--file') args.file = argv[++i]
    else if (a === '--paper') args.paper = argv[++i]
    else if (a === '--check') args.check = true
    else if (a === '-h' || a === '--help') args.help = true
  }
  return args
}

function usage() {
  console.log(`
gen-holidays.mjs —— 节假日配置年更脚本

  node scripts/gen-holidays.mjs --year <年> [--remote | --file <json路径>] [--check]

  --year <年>     目标年份，必填（如 2027）
  --remote        从 holiday-cn CDN 拉取数据
  --file <路径>   从本地 holiday-cn 格式 JSON 读取
  --paper <URL>   覆盖国务院通知原文 URL（用于溯源注释）
  --check         只校验，不写文件
  -h, --help      显示帮助
`)
}

// ── 数据获取 ──
async function loadData(args) {
  if (args.file) {
    const p = resolve(process.cwd(), args.file)
    if (!existsSync(p)) throw new Error(`文件不存在：${p}`)
    return JSON.parse(readFileSync(p, 'utf8'))
  }
  const url = `${CDN}/${args.year}.json`
  console.log(`拉取 ${url} …`)
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(
      `拉取失败（HTTP ${res.status}）。可能该年份安排尚未发布——\n` +
        `国办通知一般在放假前一年 11 月左右发布，请稍后再试，或用 --file 指定本地数据。`,
    )
  }
  return res.json()
}

// ── 校验 ──
function validate(year, days) {
  const errors = []
  const seen = new Set()
  const weekCN = ['日', '一', '二', '三', '四', '五', '六']

  for (const d of days) {
    const { date, name, isOffDay } = d
    if (!date || !name || typeof isOffDay !== 'boolean') {
      errors.push(`字段缺失：${JSON.stringify(d)}`)
      continue
    }
    const m = date.match(/^(\d{4})-(\d{2})-(\d{2})$/)
    if (!m) {
      errors.push(`日期格式非 YYYY-MM-DD：${date}`)
      continue
    }
    if (Number(m[1]) !== year) {
      errors.push(`年份与目标不一致：${date}（目标 ${year}）`)
      continue
    }
    if (seen.has(date)) errors.push(`日期重复：${date}`)
    seen.add(date)

    const dow = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])).getDay()
    const isWeekend = dow === 0 || dow === 6

    // 调休补班必须落在周末，否则官方数据有误
    if (!isOffDay && !isWeekend) {
      errors.push(`调休补班的日期不是周末：${date}（周${weekCN[dow]}）`)
    }
    // 休息日方向反向校验：连续放假段里应当至少有一个自然日不是周末
    // （若某次放假全部落在周末，说明假期本身没带来额外休息，需人工确认）
  }

  // 年度总量合理性：大陆调休安排下，调整条目通常在 10~50 条
  if (days.length < 5 || days.length > 60) {
    errors.push(`条目数异常：${days.length} 条（预期 5~60）。请确认数据源是否为完整年度数据。`)
  }

  return errors
}

// ── 生成 TS ──
function renderTs(year, days, paper) {
  const festivals = days.filter((d) => d.isOffDay).sort((a, b) => a.date.localeCompare(b.date))
  const workdays = days.filter((d) => !d.isOffDay).sort((a, b) => a.date.localeCompare(b.date))

  // 按节日分组渲染，便于人工比对
  const groupBy = (list) => {
    const map = new Map()
    for (const d of list) {
      if (!map.has(d.name)) map.set(d.name, [])
      map.get(d.name).push(d)
    }
    return map
  }

  const fGroups = groupBy(festivals)
  const wGroups = groupBy(workdays)

  const renderGroup = (map) => {
    const lines = []
    for (const [name, items] of map) {
      lines.push(`    // ${name}`)
      for (const d of items) {
        lines.push(`    '${d.date.slice(5)}': '${name}',`)
      }
    }
    return lines.join('\n')
  }

  const paperLine = paper ? ` * ${paper}\n` : ''

  return `import type { YearConfig } from './types'

/**
 * ${year} 年中国大陆节假日调整配置（稀疏表）
 *
 * 数据来源：国务院办公厅《关于 ${year} 年部分节假日安排的通知》
${paperLine} *
 * 由 scripts/gen-holidays.mjs 生成，数据取自 NateScarlet/holiday-cn（CI 每日抓取 gov.cn）。
 * 生成后请人工抽查春节/国庆的调休首尾日，确认无误再提交。
 *
 * 统计：放假 ${festivals.length} 天 + 调休补班 ${workdays.length} 天 = ${days.length} 条
 */
export const HOLIDAYS_${year}: YearConfig = {
  year: ${year},
  source: '${paper ?? ''}',

  // ── 法定节假日（放假） ──
  festivals: {
${renderGroup(fGroups)}
  },

  // ── 调休补班（周末上班） ──
  workdays: {
${renderGroup(wGroups)}
  },
}
`
}

// ── 主流程 ──
async function main() {
  const args = parseArgs(process.argv.slice(2))
  if (args.help || !args.year) {
    usage()
    if (!args.year && !args.help) process.exitCode = 1
    return
  }
  if (!args.remote && !args.file) {
    console.error('错误：需指定 --remote 或 --file <路径>')
    usage()
    process.exitCode = 1
    return
  }

  const data = await loadData(args)
  const days = data.days ?? []
  const paper = args.paper ?? data.papers?.[0] ?? ''

  console.log(`年份：${data.year ?? args.year}`)
  console.log(`来源：${paper || '（未提供）'}`)
  console.log(`条目：${days.length} 条（放假 ${days.filter((d) => d.isOffDay).length} + 补班 ${days.filter((d) => !d.isOffDay).length}）`)

  const errors = validate(args.year, days)
  if (errors.length) {
    console.error('\n❌ 校验未通过：')
    for (const e of errors) console.error('  - ' + e)
    process.exitCode = 1
    return
  }
  console.log('✅ 校验通过')

  if (args.check) {
    console.log('（--check 模式，未写文件）')
    return
  }

  const out = resolve(OUT_DIR, `${args.year}.ts`)
  if (existsSync(out)) {
    console.warn(`\n⚠️  已存在 ${out}，将被覆盖。`)
  }
  writeFileSync(out, renderTs(args.year, days, paper), 'utf8')
  console.log(`\n已写入：${out}`)
  console.log(`\n下一步（两处都要改，否则新配置不生效）：`)
  console.log(`  1. 在 lairweb/src/lib/holidays/index.ts 的 REGISTRY 中登记：`)
  console.log(`       ${args.year}: HOLIDAYS_${args.year},`)
  console.log(`     并补上 import { HOLIDAYS_${args.year} } from './${args.year}'`)
  console.log(`  2. 抽查春节/国庆调休首尾日后提交。`)
}

main().catch((e) => {
  console.error('❌ ' + e.message)
  process.exitCode = 1
})
