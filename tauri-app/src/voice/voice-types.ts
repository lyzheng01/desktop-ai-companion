export type VoiceAutoPlayMode = 'off' | 'phrases-only' | 'all'

export type VoiceSettings = {
  voice_enabled: boolean
  voice_pack: string
  voice_auto_play_mode: VoiceAutoPlayMode
}

export type VoicePackMeta = {
  id: string
  name: string
  phrases: Record<string, string>
}
