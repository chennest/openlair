import type { VocabWord } from './api'

// 自测模式干扰项挑选：轻量相似度打分（TypeWords 思路的简化版）
// 词形互含 / 释义相同 / 词根关联 = 高分易混项；再加随机扰动避免每次出题固定

function commonChars(a: string, b: string): number {
  const setA = new Set(a.toLowerCase())
  const setB = new Set(b.toLowerCase())
  let n = 0
  for (const ch of setA) if (setB.has(ch)) n += 1
  return n
}

function meaningText(w: VocabWord): string {
  return w.translations.map((t) => t.cn).join('')
}

function related(w: VocabWord, other: VocabWord): boolean {
  // relWords 可能为空对象（如导入词库未填相关词字段）
  return (w.relWords?.rels ?? []).some((r) => (r.words ?? []).some((x) => x.c === other.word))
}

export function similarity(a: VocabWord, b: VocabWord): number {
  let score = 0
  if (a.word.includes(b.word) || b.word.includes(a.word)) score += 500
  if (related(a, b) || related(b, a)) score += 500
  if (meaningText(a) === meaningText(b)) score += 200
  score += commonChars(meaningText(a), meaningText(b)) * 2
  score += commonChars(a.word, b.word)
  return score + Math.random() * 50
}

/** 从词池中挑出与目标最相似的 N 个干扰项（打乱后与正确项合成选项） */
export function pickDistractors(
  target: VocabWord,
  pool: VocabWord[],
  count = 3,
): Array<{ word: VocabWord; correct: boolean }> {
  const candidates = pool
    .filter((w) => w.id !== target.id && meaningText(w) !== meaningText(target))
    .map((w) => ({ w, s: similarity(target, w) }))
    .sort((x, y) => x.s - y.s)
    .slice(-count)
  const options = [
    ...candidates.map((c) => ({ word: c.w, correct: false })),
    { word: target, correct: true },
  ]
  // 洗牌
  for (let i = options.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[options[i], options[j]] = [options[j], options[i]]
  }
  return options
}
