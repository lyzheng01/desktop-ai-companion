import type { VoicePackMeta } from './voice-types'

export class VoiceManager {
  private currentVoicePack = ''
  private meta: VoicePackMeta | null = null
  private currentAudio: HTMLAudioElement | null = null
  private enabled = true

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
    if (!this.currentAudio) return
    this.currentAudio.pause()
    this.currentAudio.currentTime = 0
    this.currentAudio = null
  }

  hasPhrase(text: string): boolean {
    if (!this.meta) return false
    return Boolean(this.meta.phrases[text])
  }

  async playPhrase(text: string): Promise<boolean> {
    if (!this.enabled) return false
    if (!this.meta || !this.currentVoicePack) return false

    const fileName = this.meta.phrases[text]
    if (!fileName) return false

    this.stop()

    const audio = new Audio(`/voice-packs/${this.currentVoicePack}/${fileName}`)
    this.currentAudio = audio

    try {
      await audio.play()
      return true
    } catch (error) {
      console.warn('Voice playback failed:', error)
      return false
    }
  }
}
