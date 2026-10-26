// Web Speech API 封装。中文语音朗读；不可用时静默 no-op。

let cachedVoice: SpeechSynthesisVoice | null = null
let warnedUnsupported = false
let pendingTimer: number | null = null

function pickVoice(): SpeechSynthesisVoice | null {
  if (cachedVoice) return cachedVoice
  const voices = window.speechSynthesis.getVoices()
  if (!voices.length) return null
  const normalized = (v: SpeechSynthesisVoice) => v.lang.toLowerCase().replace('_', '-')
  const preferred =
    voices.find((v) => normalized(v) === 'zh-cn') ||
    voices.find((v) => normalized(v).startsWith('zh')) ||
    voices.find((v) => normalized(v).startsWith('cmn')) ||
    null
  if (preferred) cachedVoice = preferred
  return preferred
}

function fireSpeak(text: string) {
  const synth = window.speechSynthesis
  const utter = new SpeechSynthesisUtterance(text)
  utter.lang = 'zh-CN'
  utter.rate = 0.85
  utter.pitch = 1
  const voice = pickVoice()
  if (voice) utter.voice = voice
  utter.onerror = (e) => {
    // canceled / interrupted 是用户主动打断的正常时序，不是错误
    if (e.error === 'canceled' || e.error === 'interrupted') return
    // eslint-disable-next-line no-console
    console.warn('[tts] utterance error:', e.error, 'text=', text, 'voice=', voice?.name)
  }
  // 某些浏览器会把合成器停在 paused 状态，需要 resume 才能出声
  if (synth.paused) synth.resume()
  synth.speak(utter)
}

function ensureVoicesThenSpeak(text: string) {
  const synth = window.speechSynthesis
  if (synth.getVoices().length > 0) {
    fireSpeak(text)
    return
  }
  let fired = false
  const runOnce = () => {
    if (fired) return
    fired = true
    synth.removeEventListener('voiceschanged', runOnce)
    fireSpeak(text)
  }
  synth.addEventListener('voiceschanged', runOnce)
  setTimeout(runOnce, 300)
}

export function speak(text: string): void {
  if (!text?.trim()) return
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    if (!warnedUnsupported) {
      warnedUnsupported = true
      // eslint-disable-next-line no-console
      console.warn('[tts] speechSynthesis 不可用')
    }
    return
  }
  const synth = window.speechSynthesis

  // 有排队/正在播放：先 cancel，等一小段再 speak，规避 Chromium 里 cancel+同 tick speak 双双静音的 bug
  if (synth.speaking || synth.pending) {
    synth.cancel()
    if (pendingTimer) clearTimeout(pendingTimer)
    pendingTimer = window.setTimeout(() => {
      pendingTimer = null
      ensureVoicesThenSpeak(text)
    }, 80)
    return
  }

  ensureVoicesThenSpeak(text)
}
