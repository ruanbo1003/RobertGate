// Web Speech API 封装。中文语音朗读；不可用时静默 no-op。

let cachedVoice: SpeechSynthesisVoice | null = null
let warned = false

function pickVoice(): SpeechSynthesisVoice | null {
  if (cachedVoice) return cachedVoice
  const voices = window.speechSynthesis.getVoices()
  const zh = voices.find((v) => v.lang.toLowerCase().startsWith('zh'))
  if (zh) {
    cachedVoice = zh
    return zh
  }
  return null
}

function warnOnce(msg: string) {
  if (warned) return
  warned = true
  // eslint-disable-next-line no-console
  console.warn(msg)
}

export function speak(text: string): void {
  if (!text?.trim()) return
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    warnOnce('speechSynthesis 不可用')
    return
  }
  const synth = window.speechSynthesis
  const doSpeak = () => {
    synth.cancel()
    const utter = new SpeechSynthesisUtterance(text)
    utter.lang = 'zh-CN'
    utter.rate = 0.85
    utter.pitch = 1
    const voice = pickVoice()
    if (voice) utter.voice = voice
    synth.speak(utter)
  }
  // 首次调用 voices 可能为空，等 voiceschanged 后重试一次
  if (synth.getVoices().length === 0) {
    const once = () => {
      synth.removeEventListener('voiceschanged', once)
      doSpeak()
    }
    synth.addEventListener('voiceschanged', once)
    // 保险起见，200ms 后无论有没有 voice 都尝试一次
    setTimeout(doSpeak, 200)
    return
  }
  doSpeak()
}
