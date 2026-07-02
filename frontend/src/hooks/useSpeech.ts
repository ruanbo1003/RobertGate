import { useCallback, useEffect, useState } from 'react'

// 封装浏览器 SpeechSynthesis：朗读英文/中文
export function useSpeech() {
  const [supported, setSupported] = useState(false)
  const [speaking, setSpeaking] = useState(false)

  useEffect(() => {
    setSupported(typeof window !== 'undefined' && 'speechSynthesis' in window)
  }, [])

  const speak = useCallback(
    (text: string, lang: 'en-US' | 'zh-CN' = 'en-US') => {
      if (!supported) return
      window.speechSynthesis.cancel()
      const utter = new SpeechSynthesisUtterance(text)
      utter.lang = lang
      utter.rate = 0.9
      utter.onstart = () => setSpeaking(true)
      utter.onend = () => setSpeaking(false)
      utter.onerror = () => setSpeaking(false)
      window.speechSynthesis.speak(utter)
    },
    [supported]
  )

  const stop = useCallback(() => {
    if (!supported) return
    window.speechSynthesis.cancel()
    setSpeaking(false)
  }, [supported])

  return { supported, speaking, speak, stop }
}
