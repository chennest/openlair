/** 金额格式化：¥ + 千分位 + 固定位数小数；负号置于 ¥ 前（-¥1,046.00 而非 ¥-1046.00） */
export function money(n: number, decimals = 2): string {
  const v = Number(n ?? 0)
  const abs = Math.abs(v).toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
  return `${v < 0 ? '-' : ''}¥${abs}`
}
