import wave
import sounddevice as sd
import numpy as np

from pyspecconst import DEFAULT_SAMPLE_RATE, DEFAULT_BLOCK_SIZE


def init_audio_device():
    """Initialize audio device with error handling and backend selection"""
    try:
        # Try to create output stream without specifying backend
        test_stream = sd.OutputStream(
            channels=2,
            samplerate=DEFAULT_SAMPLE_RATE,
            blocksize=DEFAULT_BLOCK_SIZE,
            dtype=np.float32
        )
        test_stream.close()
        return True
    except sd.PortAudioError as e:
        print(f"Audio initialization error: {e}")
        return False


def start_audio_recording(filename, sample_rate=DEFAULT_SAMPLE_RATE):
    """Start recording audio to a WAV file"""
    wav_file = wave.open(filename, 'wb')
    wav_file.setnchannels(2)  # stereo
    wav_file.setsampwidth(2)  # 2 bytes per sample
    wav_file.setframerate(sample_rate)
    return wav_file


def write_audio_samples(wav_file, samples):
    """Write audio samples to the WAV file"""
    # Convert float samples to 16-bit integers
    scaled = np.int16(samples * 32767)
    wav_file.writeframes(scaled.tobytes())


def stop_audio_recording(wav_file):
    """Close the WAV file"""
    wav_file.close()
