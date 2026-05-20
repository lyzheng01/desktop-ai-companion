type SpeechInputHandlers = {
  onStateChange?: (state: 'idle' | 'recording' | 'transcribing') => void
}

export class SpeechInputManager {
  private mediaRecorder: MediaRecorder | null = null
  private mediaStream: MediaStream | null = null
  private chunks: Blob[] = []
  private handlers: SpeechInputHandlers

  constructor(handlers: SpeechInputHandlers = {}) {
    this.handlers = handlers
  }

  private setState(state: 'idle' | 'recording' | 'transcribing') {
    this.handlers.onStateChange?.(state)
  }

  async start(): Promise<void> {
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      return
    }

    this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    this.chunks = []
    this.mediaRecorder = new MediaRecorder(this.mediaStream)
    this.mediaRecorder.addEventListener('dataavailable', (event) => {
      if (event.data.size > 0) {
        this.chunks.push(event.data)
      }
    })
    this.mediaRecorder.start()
    this.setState('recording')
  }

  async stopAndTranscribe(): Promise<string> {
    if (!this.mediaRecorder || this.mediaRecorder.state !== 'recording') {
      return ''
    }

    const recorder = this.mediaRecorder
    const stream = this.mediaStream

    const blob = await new Promise<Blob>((resolve) => {
      recorder.addEventListener('stop', () => {
        resolve(new Blob(this.chunks, { type: recorder.mimeType || 'audio/webm' }))
      }, { once: true })
      recorder.stop()
    })

    stream?.getTracks().forEach((track) => track.stop())
    this.mediaRecorder = null
    this.mediaStream = null
    this.setState('transcribing')

    const arrayBuffer = await blob.arrayBuffer()
    const bytes = Array.from(new Uint8Array(arrayBuffer))

    try {
      const path = await window.__TAURI_INTERNALS__.invoke('save_temp_audio_file', {
        payload: bytes,
        extension: blob.type.includes('wav') ? 'wav' : 'webm',
      }) as string
      const text = await window.__TAURI_INTERNALS__.invoke('transcribe_audio_file', { path }) as string
      this.setState('idle')
      return text
    } catch (error) {
      this.setState('idle')
      throw error
    }
  }
}
