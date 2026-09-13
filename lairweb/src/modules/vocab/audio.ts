// 发音工具：单词走有道词典公共朗读接口（免费、无需 key），例句走浏览器内置 TTS

/** 播放单词发音（type=1 英音 / 2 美音，默认美音） */
export function playWord(word: string, uk = false): void {
  if (!word) return
  const url = `https://dict.youdao.com/dictvoice?audio=${encodeURIComponent(word)}&type=${uk ? 1 : 2}`
  void new Audio(url).play().catch(() => {})
}

/** 播放英文例句（浏览器 SpeechSynthesis，无声时多为系统缺少英文声色） */
export function playSentence(text: string): void {
  if (!text || !('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  const utter = new SpeechSynthesisUtterance(text)
  utter.lang = 'en-US'
  window.speechSynthesis.speak(utter)
}
