type SpeechInputHandlers = {
  onStateChange?: (state: 'idle' | 'recording' | 'transcribing') => void
}

export class SpeechInputManager {
  private audioContext: AudioContext | null = null
  private sourceNode: MediaStreamAudioSourceNode | null = null
  private processorNode: ScriptProcessorNode | null = null
  private mediaStream: MediaStream | null = null
  private chunks: Float32Array[] = []
  private sampleRate = 44100
  private handlers: SpeechInputHandlers

  constructor(handlers: SpeechInputHandlers = {}) {
    this.handlers = handlers
  }

  private setState(state: 'idle' | 'recording' | 'transcribing') {
    this.handlers.onStateChange?.(state)
  }

  async start(): Promise<void> {
    if (this.processorNode) {
      return
    }

    this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    this.chunks = []
    this.audioContext = new AudioContext()
    this.sampleRate = this.audioContext.sampleRate
    this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream)
    this.processorNode = this.audioContext.createScriptProcessor(4096, 1, 1)
    this.processorNode.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0)
      this.chunks.push(new Float32Array(input))
    }
    this.sourceNode.connect(this.processorNode)
    this.processorNode.connect(this.audioContext.destination)
    this.setState('recording')
  }

  async stopAndTranscribe(): Promise<string> {
    if (!this.processorNode || !this.audioContext) {
      return ''
    }

    const stream = this.mediaStream

    this.processorNode.disconnect()
    this.sourceNode?.disconnect()
    this.processorNode.onaudioprocess = null
    this.processorNode = null
    this.sourceNode = null

    const wavBytes = this.encodeWav(this.flattenChunks(), this.sampleRate)

    stream?.getTracks().forEach((track) => track.stop())
    this.mediaStream = null
    await this.audioContext.close()
    this.audioContext = null
    this.setState('transcribing')

    try {
      const path = await window.__TAURI_INTERNALS__.invoke('save_temp_audio_file', {
        payload: Array.from(wavBytes),
        extension: 'wav',
      }) as string
      const text = await window.__TAURI_INTERNALS__.invoke('transcribe_audio_file', { path }) as string
      this.setState('idle')
      return text
    } catch (error) {
      this.setState('idle')
      throw error
    }
  }

  private flattenChunks(): Float32Array {
    const totalLength = this.chunks.reduce((sum, chunk) => sum + chunk.length, 0)
    const output = new Float32Array(totalLength)
    let offset = 0
    for (const chunk of this.chunks) {
      output.set(chunk, offset)
      offset += chunk.length
    }
    return output
  }

  private encodeWav(samples: Float32Array, sampleRate: number): Uint8Array {
    const buffer = new ArrayBuffer(44 + samples.length * 2)
    const view = new DataView(buffer)
    const writeString = (offset: number, text: string) => {
      for (let i = 0; i < text.length; i++) {
        view.setUint8(offset + i, text.charCodeAt(i))
      }
    }

    writeString(0, 'RIFF')
    view.setUint32(4, 36 + samples.length * 2, true)
    writeString(8, 'WAVE')
    writeString(12, 'fmt ')
    view.setUint32(16, 16, true)
    view.setUint16(20, 1, true)
    view.setUint16(22, 1, true)
    view.setUint32(24, sampleRate, true)
    view.setUint32(28, sampleRate * 2, true)
    view.setUint16(32, 2, true)
    view.setUint16(34, 16, true)
    writeString(36, 'data')
    view.setUint32(40, samples.length * 2, true)

    let offset = 44
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]))
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
      offset += 2
    }
    return new Uint8Array(buffer)
  }
}
