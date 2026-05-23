type SpeechInputHandlers = {
  onStateChange?: (state: 'idle' | 'recording' | 'transcribing') => void
}

type ContinuousCaptureOptions = {
  silenceMs?: number
  minSpeechMs?: number
  threshold?: number
  maxWaitForSpeechMs?: number
  maxCaptureMs?: number
  preRollChunks?: number
}

export class SpeechInputManager {
  private static readonly TARGET_SAMPLE_RATE = 16000
  private audioContext: AudioContext | null = null
  private sourceNode: MediaStreamAudioSourceNode | null = null
  private processorNode: ScriptProcessorNode | null = null
  private mediaStream: MediaStream | null = null
  private chunks: Float32Array[] = []
  private sampleRate = 44100
  private handlers: SpeechInputHandlers
  private continuousResolver: ((value: string) => void) | null = null
  private continuousRejecter: ((reason?: unknown) => void) | null = null
  private continuousOptions: Required<ContinuousCaptureOptions> | null = null
  private lastSpeechAt = 0
  private speechStartedAt = 0
  private captureStartedAt = 0
  private detectedSpeech = false
  private stopRequested = false

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

    this.resetContinuousSession()
    this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    this.chunks = []
    this.audioContext = new AudioContext()
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume()
    }
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

  async startContinuousCapture(options: ContinuousCaptureOptions = {}): Promise<string> {
    if (this.processorNode) {
      throw new Error('语音采集正在进行中，请稍后再试。')
    }

    this.resetContinuousSession()
    this.continuousOptions = {
      silenceMs: options.silenceMs ?? 1400,
      minSpeechMs: options.minSpeechMs ?? 450,
      threshold: options.threshold ?? 0.008,
      maxWaitForSpeechMs: options.maxWaitForSpeechMs ?? 7000,
      maxCaptureMs: options.maxCaptureMs ?? 12000,
      preRollChunks: options.preRollChunks ?? 8,
    }

    return await new Promise<string>(async (resolve, reject) => {
      this.continuousResolver = resolve
      this.continuousRejecter = reject

      try {
        this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
        this.chunks = []
        this.audioContext = new AudioContext()
        if (this.audioContext.state === 'suspended') {
          await this.audioContext.resume()
        }
        this.sampleRate = this.audioContext.sampleRate
        this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream)
        this.processorNode = this.audioContext.createScriptProcessor(4096, 1, 1)
        this.captureStartedAt = Date.now()
        this.processorNode.onaudioprocess = (event) => {
          const input = event.inputBuffer.getChannelData(0)
          const copy = new Float32Array(input)
          const now = Date.now()
          let sum = 0
          for (let i = 0; i < copy.length; i += 1) {
            sum += copy[i] * copy[i]
          }
          const rms = Math.sqrt(sum / Math.max(1, copy.length))

          this.chunks.push(copy)
          if (!this.detectedSpeech && this.chunks.length > this.continuousOptions!.preRollChunks) {
            this.chunks.splice(0, this.chunks.length - this.continuousOptions!.preRollChunks)
          }

          if (!this.detectedSpeech && now - this.captureStartedAt >= this.continuousOptions!.maxWaitForSpeechMs) {
            this.stopRequested = true
            void this.cancelContinuousCapture(new Error('长时间没有检测到说话声，请靠近麦克风后重试。'))
            return
          }

          if (rms >= this.continuousOptions!.threshold) {
            if (!this.detectedSpeech) {
              this.detectedSpeech = true
              this.speechStartedAt = now
            }
            this.lastSpeechAt = now
            if (now - this.speechStartedAt >= this.continuousOptions!.maxCaptureMs) {
              this.stopRequested = true
              void this.finishContinuousCapture()
            }
            return
          }

          if (!this.detectedSpeech || this.stopRequested) {
            return
          }

          if (now - this.lastSpeechAt >= this.continuousOptions!.silenceMs && now - this.speechStartedAt >= this.continuousOptions!.minSpeechMs) {
            this.stopRequested = true
            void this.finishContinuousCapture()
          }
        }
        this.sourceNode.connect(this.processorNode)
        this.processorNode.connect(this.audioContext.destination)
        this.setState('recording')
      } catch (error) {
        this.resetContinuousSession()
        reject(error)
      }
    })
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

    const pcmSamples = this.flattenChunks()

    stream?.getTracks().forEach((track) => track.stop())
    this.mediaStream = null
    await this.audioContext.close()
    this.audioContext = null

    if (pcmSamples.length === 0) {
      this.setState('idle')
      throw new Error('未采集到麦克风音频，请检查麦克风权限后重试。')
    }

    const normalizedSamples = this.resampleToTargetRate(pcmSamples, this.sampleRate, SpeechInputManager.TARGET_SAMPLE_RATE)
    const wavBytes = this.encodeWav(normalizedSamples, SpeechInputManager.TARGET_SAMPLE_RATE)
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

  async cancel(): Promise<void> {
    this.stopRequested = true
    await this.teardownAudioPipeline()
    this.setState('idle')
    this.resetContinuousSession()
  }

  private async finishContinuousCapture(): Promise<void> {
    const resolve = this.continuousResolver
    const reject = this.continuousRejecter

    try {
      const text = await this.stopAndTranscribe()
      resolve?.(text)
    } catch (error) {
      reject?.(error)
    } finally {
      this.resetContinuousSession()
    }
  }

  private async cancelContinuousCapture(error: Error): Promise<void> {
    const reject = this.continuousRejecter
    await this.teardownAudioPipeline()
    this.setState('idle')
    reject?.(error)
    this.resetContinuousSession()
  }

  private async teardownAudioPipeline(): Promise<void> {
    const stream = this.mediaStream

    this.processorNode?.disconnect()
    this.sourceNode?.disconnect()
    if (this.processorNode) {
      this.processorNode.onaudioprocess = null
    }
    this.processorNode = null
    this.sourceNode = null

    stream?.getTracks().forEach((track) => track.stop())
    this.mediaStream = null

    if (this.audioContext) {
      await this.audioContext.close()
      this.audioContext = null
    }
  }

  private resetContinuousSession() {
    this.continuousResolver = null
    this.continuousRejecter = null
    this.continuousOptions = null
    this.lastSpeechAt = 0
    this.speechStartedAt = 0
    this.captureStartedAt = 0
    this.detectedSpeech = false
    this.stopRequested = false
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

  private resampleToTargetRate(samples: Float32Array, inputSampleRate: number, targetSampleRate: number): Float32Array {
    if (inputSampleRate === targetSampleRate) {
      return samples
    }

    const ratio = inputSampleRate / targetSampleRate
    const outputLength = Math.max(1, Math.round(samples.length / ratio))
    const output = new Float32Array(outputLength)

    for (let i = 0; i < outputLength; i += 1) {
      const position = i * ratio
      const leftIndex = Math.floor(position)
      const rightIndex = Math.min(samples.length - 1, leftIndex + 1)
      const blend = position - leftIndex
      output[i] = samples[leftIndex] * (1 - blend) + samples[rightIndex] * blend
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
