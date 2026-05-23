import type { VoicePackMeta } from './voice-types'

export class VoiceManager {
  private currentVoicePack = ''
  private meta: VoicePackMeta | null = null
  private currentAudio: HTMLAudioElement | null = null
  private enabled = true
  private unlocked = false
  private currentUtterance: SpeechSynthesisUtterance | null = null
  private preferredVoice: SpeechSynthesisVoice | null = null

  setEnabled(enabled: boolean) {
    this.enabled = enabled
    if (!enabled) {
      this.stop()
    }
  }

  async setVoicePack(voicePack: string): Promise<void> {
    if (!voicePack) {
      this.currentVoicePack = ''
      this.meta = null
      return
    }

    if (this.currentVoicePack === voicePack && this.meta) {
      return
    }

    try {
      const response = await fetch(`/voice-packs/${voicePack}/meta.json`)
      if (!response.ok) {
        throw new Error(`Failed to load voice pack meta: ${response.status}`)
      }

      this.meta = await response.json() as VoicePackMeta
      this.currentVoicePack = voicePack
    } catch (error) {
      console.warn('Voice pack load failed:', error)
      this.currentVoicePack = ''
      this.meta = null
    }
  }

  stop(): void {
    if (this.currentUtterance) {
      window.speechSynthesis.cancel()
      this.currentUtterance = null
    }
    if (!this.currentAudio) return
    this.currentAudio.pause()
    this.currentAudio.currentTime = 0
    this.currentAudio = null
  }

  async unlock(): Promise<void> {
    if (this.unlocked) return

    try {
      const audio = new Audio()
      audio.muted = true
      audio.src = this.createSilentWavUrl(180)
      await audio.play()
      audio.pause()
      audio.currentTime = 0
      this.unlocked = true
      this.refreshPreferredVoice()
      console.log('[voice] unlocked')
    } catch (error) {
      console.warn('Voice unlock failed:', error)
    }
  }

  private refreshPreferredVoice(): void {
    if (!('speechSynthesis' in window)) {
      this.preferredVoice = null
      return
    }

    const voices = window.speechSynthesis.getVoices()
    const preferred = [...voices]
      .filter((voice) => /zh|cmn|chinese/i.test(`${voice.lang} ${voice.name}`))
      .sort((left, right) => this.scoreVoice(right) - this.scoreVoice(left))[0] ?? null
    this.preferredVoice = preferred
  }

  private scoreVoice(voice: SpeechSynthesisVoice): number {
    const label = `${voice.name} ${voice.lang}`.toLowerCase()
    let score = 0
    if (voice.lang.toLowerCase().startsWith('zh-cn')) score += 40
    if (label.includes('xiaoxiao')) score += 30
    if (label.includes('xiaoyi')) score += 24
    if (label.includes('female') || label.includes('女')) score += 12
    if (label.includes('natural')) score += 10
    if (voice.default) score += 6
    return score
  }

  private sanitizeSpokenText(text: string): string {
    return text
      .replace(/`+/g, '')
      .replace(/[*_~>#-]/g, ' ')
      .replace(/https?:\/\/\S+/g, '这个链接')
      .replace(/\s+/g, ' ')
      .replace(/[A-Za-z0-9_]{18,}/g, '这段内容')
      .trim()
  }

  private createSilentWavUrl(durationMs: number): string {
    const sampleRate = 44100
    const numChannels = 1
    const bitsPerSample = 16
    const numSamples = Math.max(1, Math.floor(sampleRate * durationMs / 1000))
    const blockAlign = numChannels * bitsPerSample / 8
    const byteRate = sampleRate * blockAlign
    const dataSize = numSamples * blockAlign
    const buffer = new ArrayBuffer(44 + dataSize)
    const view = new DataView(buffer)
    const writeString = (offset: number, text: string) => {
      for (let i = 0; i < text.length; i++) {
        view.setUint8(offset + i, text.charCodeAt(i))
      }
    }

    writeString(0, 'RIFF')
    view.setUint32(4, 36 + dataSize, true)
    writeString(8, 'WAVE')
    writeString(12, 'fmt ')
    view.setUint32(16, 16, true)
    view.setUint16(20, 1, true)
    view.setUint16(22, numChannels, true)
    view.setUint32(24, sampleRate, true)
    view.setUint32(28, byteRate, true)
    view.setUint16(32, blockAlign, true)
    view.setUint16(34, bitsPerSample, true)
    writeString(36, 'data')
    view.setUint32(40, dataSize, true)

    return URL.createObjectURL(new Blob([buffer], { type: 'audio/wav' }))
  }

  hasPhrase(text: string): boolean {
    if (!this.meta) return false
    return Boolean(this.meta.phrases[text])
  }

  async playPhrase(text: string): Promise<boolean> {
    if (!this.enabled) return false
    if (!this.meta || !this.currentVoicePack) return false
    if (!this.unlocked) return false

    const fileName = this.meta.phrases[text]
    if (!fileName) return false

    this.stop()

    const audio = new Audio(`/voice-packs/${this.currentVoicePack}/${fileName}`)
    this.currentAudio = audio
    audio.preload = 'auto'
    audio.volume = 1

    try {
      console.log('[voice] play', text, fileName)
      await audio.play()
      return true
    } catch (error) {
      console.warn('Voice playback failed:', error)
      return false
    }
  }

  async speakText(text: string): Promise<boolean> {
    if (!this.enabled) return false
    const sanitized = this.sanitizeSpokenText(text)
    if (!sanitized) return false

    if (await this.playPhrase(sanitized)) {
      await this.waitForAudioEnd()
      return true
    }

    if (!('speechSynthesis' in window)) {
      return false
    }

    this.stop()
    this.refreshPreferredVoice()

    return await new Promise<boolean>((resolve) => {
      const utterance = new SpeechSynthesisUtterance(sanitized)
      utterance.lang = 'zh-CN'
      utterance.rate = 0.95
      utterance.pitch = 1.03
      utterance.volume = 1
      if (this.preferredVoice) {
        utterance.voice = this.preferredVoice
        utterance.lang = this.preferredVoice.lang
      }
      this.currentUtterance = utterance
      utterance.onend = () => {
        this.currentUtterance = null
        resolve(true)
      }
      utterance.onerror = () => {
        this.currentUtterance = null
        resolve(false)
      }
      window.speechSynthesis.speak(utterance)
    })
  }

  private async waitForAudioEnd(): Promise<void> {
    const audio = this.currentAudio
    if (!audio) {
      return
    }

    await new Promise<void>((resolve) => {
      const cleanup = () => {
        audio.removeEventListener('ended', onEnded)
        audio.removeEventListener('error', onEnded)
        if (this.currentAudio === audio) {
          this.currentAudio = null
        }
        resolve()
      }
      const onEnded = () => cleanup()
      if (audio.ended) {
        cleanup()
        return
      }
      audio.addEventListener('ended', onEnded, { once: true })
      audio.addEventListener('error', onEnded, { once: true })
    })
  }
}
