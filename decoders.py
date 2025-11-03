import numpy as np
import pyspecconst
from signal_processing import bandpass_filter


def decode_ax25_frame(bit_stream):
    """
    Decode AX.25 frame from bit stream
    Returns decoded packet or None if invalid
    """
    try:
        # Find flag pattern (01111110)
        flag = [0, 1, 1, 1, 1, 1, 1, 0]

        # Find start and end flags
        start = -1
        for i in range(len(bit_stream) - 7):
            if bit_stream[i:i+8] == flag:
                start = i + 8
                break

        if start == -1:
            return None

        # Extract data between flags
        frame_bits = []
        ones_count = 0
        i = start

        while i < len(bit_stream) - 7:
            bit = bit_stream[i]
            frame_bits.append(bit)

            if bit == 1:
                ones_count += 1
            else:
                ones_count = 0

            # Skip stuffed bits
            if ones_count == 5 and i + 1 < len(bit_stream) and bit_stream[i+1] == 0:
                i += 2
                ones_count = 0
                continue

            i += 1

            # Check for end flag
            if frame_bits[-8:] == flag:
                frame_bits = frame_bits[:-8]
                break

        # Convert bits to bytes
        frame_bytes = []
        for i in range(0, len(frame_bits), 8):
            if i + 8 <= len(frame_bits):
                byte = 0
                for j in range(8):
                    byte |= frame_bits[i+j] << j
                frame_bytes.append(byte)

        return decode_aprs_payload(frame_bytes)

    except Exception:
        return None


def decode_aprs_payload(frame_bytes):
    """
    Decode APRS packet payload
    """
    try:
        if len(frame_bytes) < 14:  # Minimum length for valid packet
            return None

        # Extract addresses
        dest = ''.join([chr((b >> 1) & 0x7F) for b in frame_bytes[0:6]]).strip()
        source = ''.join([chr((b >> 1) & 0x7F) for b in frame_bytes[7:13]]).strip()

        # Control and PID fields
        # ctrl = frame_bytes[13]
        # pid = frame_bytes[14] if len(frame_bytes) > 14 else None

        # Information field
        info = ''
        if len(frame_bytes) > 15:
            info = ''.join([chr(b) for b in frame_bytes[15:]])

        return f"{source}>{dest}:{info}"

    except Exception:
        return None


def decode_afsk(samples, sample_rate):
    """
    Demodulate Bell 202 AFSK (1200/2200 Hz)
    Returns bit stream
    """
    # Filter for AFSK tones
    filtered_1200 = bandpass_filter(samples, 1100, 1300, sample_rate)
    filtered_2200 = bandpass_filter(samples, 2100, 2300, sample_rate)

    # Calculate energy in each band
    window = int(sample_rate / 1200)  # One bit period
    bits = []

    for i in range(0, len(samples) - window, window):
        e1200 = np.sum(filtered_1200[i:i+window]**2)
        e2200 = np.sum(filtered_2200[i:i+window]**2)
        bits.append(1 if e2200 > e1200 else 0)

    return bits


def decode_aprs(samples, sample_rate):
    """
    Decode APRS packets from audio samples
    Returns list of decoded packets
    """
    # Convert to real if complex
    if np.iscomplexobj(samples):
        samples = np.real(samples)

    # Normalize audio
    samples = samples / np.max(np.abs(samples))

    # Demodulate AFSK to get bit stream
    bits = decode_afsk(samples, sample_rate)

    # Decode AX.25 frame
    packet = decode_ax25_frame(bits)

    return [packet] if packet else []


def decode_morse(samples, sample_rate, threshold=-20):
    """
    Decode Morse code from audio samples

    Args:
        samples: numpy array of audio samples (complex IQ data)
        sample_rate: sampling rate in Hz
        threshold: signal detection threshold in dB

    Returns:
        decoded_text: string of decoded text
        timing_data: dict with timing statistics
    """
    # Convert complex samples to magnitude
    envelope = np.abs(samples)

    # Normalize and convert to dB
    envelope = envelope / np.max(envelope)
    envelope_db = 20 * np.log10(envelope + 1e-10)

    # Rest of the function remains the same...
    # Detect signals above threshold
    signals = envelope_db > threshold

    # Find transitions
    transitions = np.diff(signals.astype(int))
    rise_times = np.where(transitions == 1)[0]
    fall_times = np.where(transitions == -1)[0]

    if len(rise_times) == 0 or len(fall_times) == 0:
        return "", {"dot": 0, "dash": 0, "gap": 0}

    # Ensure we have matching rises and falls
    if fall_times[0] < rise_times[0]:
        fall_times = fall_times[1:]
    if len(rise_times) > len(fall_times):
        rise_times = rise_times[:-1]

    # Calculate pulse durations
    durations = (fall_times - rise_times) / sample_rate
    gaps = (rise_times[1:] - fall_times[:-1]) / sample_rate

    if len(durations) == 0:
        return "", {"dot": 0, "dash": 0, "gap": 0}

    # Estimate dot/dash threshold using k-means clustering
    if len(durations) > 1:
        from scipy.cluster import vq
        centroids, _ = vq.kmeans(durations.reshape(-1, 1), 2)
        dot_duration = np.min(centroids)
        dash_duration = np.max(centroids)
    else:
        dot_duration = np.min(durations)
        dash_duration = dot_duration * 3

    # Classify dots and dashes
    morse_symbols = []
    current_letter = []

    for i, duration in enumerate(durations):
        # Add symbol
        if duration < (dot_duration + dash_duration) / 2:
            current_letter.append('.')
        else:
            current_letter.append('-')

        # Check for letter gaps
        if i < len(gaps):
            if gaps[i] > dot_duration * 3:
                morse_symbols.append(''.join(current_letter))
                current_letter = []
                # Check for word gaps
                if gaps[i] > dot_duration * 7:
                    morse_symbols.append(' ')

    # Add final letter if present
    if current_letter:
        morse_symbols.append(''.join(current_letter))

    # Translate to text
    decoded_text = ''
    for symbol in morse_symbols:
        if symbol == ' ':
            decoded_text += ' '
        elif symbol in pyspecconst.MORSE_CODE:
            decoded_text += pyspecconst.MORSE_CODE[symbol]
        else:
            decoded_text += '?'

    timing_data = {
        "dot": dot_duration,
        "dash": dash_duration,
        "gap": np.mean(gaps) if len(gaps) > 0 else 0
    }

    return decoded_text, timing_data

