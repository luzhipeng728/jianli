/**
 * AudioWorklet Processor for real-time audio capture
 * Resamples from browser sample rate to 16kHz and converts to 16-bit PCM
 */

class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.inputSampleRate = sampleRate // Browser's sample rate (usually 44100 or 48000)
    this.outputSampleRate = 16000 // Target sample rate for Qwen-Omni
    this.buffer = []
  }

  /**
   * Resample audio from input sample rate to output sample rate
   */
  resample(inputData, inputRate, outputRate) {
    if (inputRate === outputRate) {
      return inputData
    }

    const ratio = inputRate / outputRate
    const outputLength = Math.floor(inputData.length / ratio)
    const output = new Float32Array(outputLength)

    for (let i = 0; i < outputLength; i++) {
      const srcIndex = i * ratio
      const srcIndexFloor = Math.floor(srcIndex)
      const srcIndexCeil = Math.min(srcIndexFloor + 1, inputData.length - 1)
      const t = srcIndex - srcIndexFloor

      // Linear interpolation
      output[i] = inputData[srcIndexFloor] * (1 - t) + inputData[srcIndexCeil] * t
    }

    return output
  }

  /**
   * Convert Float32Array to Int16Array (PCM 16-bit)
   */
  floatTo16BitPCM(float32Array) {
    const int16Array = new Int16Array(float32Array.length)
    for (let i = 0; i < float32Array.length; i++) {
      // Clamp to [-1, 1] and scale to 16-bit range
      const s = Math.max(-1, Math.min(1, float32Array[i]))
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
    }
    return int16Array
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0]
    if (input && input.length > 0 && input[0].length > 0) {
      const inputData = input[0] // Mono channel

      // Resample to 16kHz
      const resampled = this.resample(inputData, this.inputSampleRate, this.outputSampleRate)

      // Convert to 16-bit PCM
      const pcm16 = this.floatTo16BitPCM(resampled)

      // Send to main thread
      this.port.postMessage({
        type: 'audio',
        audio: pcm16.buffer
      }, [pcm16.buffer])
    }

    return true // Keep processor alive
  }
}

registerProcessor('audio-processor', AudioProcessor)
