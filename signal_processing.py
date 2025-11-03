import numpy as np
from scipy.signal import butter, lfilter
from scipy.signal import firwin
from scipy.signal import hilbert
from scipy.signal import decimate
from scipy.signal import bilinear
from scipy.signal import resample_poly


# Filter to cut freq below/higher than 300/3000hz
def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a


def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a


def lowpass_filter(data, cutoff=3000, fs=44100, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = lfilter(b, a, data)
    return y


def bandpass_filter(data, lowcut, highcut, sample_rate):
    """Apply a bandpass filter to the data."""
    from scipy.signal import butter, sosfilt
    if lowcut <= 0:
        # Use a lowpass filter if lowcut is not valid
        sos = butter(10, highcut / (sample_rate / 2), btype='low', output='sos')
    else:
        sos = butter(10, [lowcut / (sample_rate / 2), highcut / (sample_rate / 2)], btype='band', output='sos')
    return sosfilt(sos, data)


# Run this function before using the rtl-sdr samples to remove dc offset and correct iq
def iq_correction(samples: np.ndarray) -> np.ndarray:
    # Remove DC and calculate input power
    centered_samples = samples - np.mean(samples)
    input_power = np.var(centered_samples)

    # Calculate scaling factor for Q
    q_amplitude = np.sqrt(2 * np.mean(samples.imag ** 2))

    # Normalize Q component
    normalized_samples = samples / q_amplitude

    i_samples, q_samples = normalized_samples.real, normalized_samples.imag

    # Estimate alpha and sin_phi
    alpha_est = np.sqrt(2 * np.mean(i_samples ** 2))
    sin_phi_est = (2 / alpha_est) * np.mean(i_samples * q_samples)

    # Estimate cos_phi
    cos_phi_est = np.sqrt(1 - sin_phi_est ** 2)

    # Apply phase and amplitude correction
    i_new = (1 / alpha_est) * i_samples
    q_new = (-sin_phi_est / alpha_est) * i_samples + q_samples

    # Corrected signal
    corrected_samples = (i_new + 1j * q_new) / cos_phi_est

    # Calculate and print phase and amplitude errors
    # phase_error_deg = np.round(np.abs(np.arccos(cos_phi_est) * 180 / np.pi), 4)
    # amplitude_error_db = np.round(np.abs(20 * np.log10(alpha_est)), 4)
    # Print phase and amplitude errors
    # print(f"Phase Error: {phase_error_deg}")
    # print(f"Amplitude Error: {amplitude_error_db}")

    return corrected_samples * np.sqrt(input_power / np.var(corrected_samples))


def mono_to_stereo(mono_audio):
    """Convert mono audio to stereo by duplicating the mono signal."""
    stereo_audio = np.zeros((len(mono_audio), 2))  # Initialize stereo array
    stereo_audio[:, 0] = mono_audio  # Left channel
    stereo_audio[:, 1] = mono_audio  # Right channel (duplicate)
    return stereo_audio
    

def demodulate_nfm(samples, sample_rate, target_rate=44100):
    """Simplified FM demodulation"""
    # Basic FM demodulation
    demod = np.angle(samples[1:] * np.conj(samples[:-1]))

    # Simple scaling
    demod = demod * (sample_rate / (2 * np.pi))

    # Apply the bandpass filter for NFM
    # lowcut = 300.0  # Low cutoff frequency
    # highcut = 3000.0  # High cutoff frequency
    # filtered_demod = bandpass_filter(demod, lowcut, highcut, sample_rate)

    # Basic lowpass filter
    nyq = sample_rate / 2
    cutoff = 15000
    taps = firwin(numtaps=65, cutoff=cutoff/nyq)
    filtered = lfilter(taps, 1.0, demod)

    # Simple decimation
    decimation_factor = int(sample_rate / target_rate)
    audio = decimate(filtered, decimation_factor)

    # Basic normalization
    audio = audio / np.max(np.abs(audio)) * 0.95
    return mono_to_stereo(audio)


def demodulate_wfm(samples, sample_rate, target_rate=44100):
    """Wide FM demodulation with stereo decoding."""
    # Step 1: FM demodulation
    demod = np.angle(samples[1:] * np.conj(samples[:-1]))

    # Step 2: Extract the baseband (L+R), pilot, and stereo difference (L-R) signals
    # Lowpass filter for L+R (0-15 kHz)
    l_plus_r = bandpass_filter(demod, 0, 15000, sample_rate)

    # Bandpass filter for the 19 kHz pilot tone
    pilot = bandpass_filter(demod, 19000 - 200, 19000 + 200, sample_rate)
    pilot = np.sin(np.unwrap(np.angle(lfilter([1], [1, -0.99], pilot))))  # Extract phase

    # Bandpass filter for the 38 kHz L-R signal
    l_minus_r = bandpass_filter(demod, 38000 - 15000, 38000 + 15000, sample_rate)
    l_minus_r = l_minus_r * (2 * pilot)  # Demodulate using the pilot tone

    # Lowpass filter the demodulated L-R signal to remove high-frequency artifacts
    l_minus_r = bandpass_filter(l_minus_r, 0, 15000, sample_rate)

    # Step 3: Combine L+R and L-R to get L and R
    left = (l_plus_r + l_minus_r) / 2
    right = (l_plus_r - l_minus_r) / 2

    # Step 4: De-emphasis filter (75 µs time constant)
    deemph_tc = 75e-6  # 75 µs (FM standard)
    alpha = np.exp(-1 / (deemph_tc * sample_rate))
    b = [1 - alpha]
    a = [1, -alpha]
    left = lfilter(b, a, left)
    right = lfilter(b, a, right)

    # Step 5: Decimate to target sample rate
    decimation_factor = int(sample_rate / target_rate)
    if decimation_factor > 1:
        left = decimate(left, decimation_factor, zero_phase=True)
        right = decimate(right, decimation_factor, zero_phase=True)

    # Step 6: Normalize the audio
    max_val = max(np.max(np.abs(left)), np.max(np.abs(right)))
    left /= max_val
    right /= max_val

    # Step 7: Combine into stereo
    audio = np.column_stack((left, right))

    # --- RDS extraction ---
    try:
        rds_baseband, rds_rate = extract_rds(demod, sample_rate)
        rds_bits = demodulate_rds_bpsk(rds_baseband, rds_rate)
        # Store or return RDS bits for later decoding
        if len(rds_bits) > 0:
            global last_rds_bits
            last_rds_bits = rds_bits
    except Exception as e:
        pass

    return audio


def demodulate_am(samples):
    """AM demodulation using envelope detection"""
    # Get the amplitude envelope
    envelope = np.abs(samples)

    # DC removal (high-pass filter)
    envelope = envelope - np.mean(envelope)

    # Apply the bandpass filter to remove low and high frequency harmonics
    fs = 44100  # Sample rate (adjust as necessary)
    lowcut = 300.0  # Low cutoff frequency
    highcut = 3000.0  # High cutoff frequency
    filtered_envelope = bandpass_filter(envelope, lowcut, highcut, fs)

    # Normalize
    audio = filtered_envelope / np.max(np.abs(filtered_envelope)) * 0.95 
    return mono_to_stereo(audio)


def demodulate_ssb(samples, sample_rate, lower=True):
    """Single-sideband demodulation"""
    # Complex bandpass filter
    if lower:
        # LSB: negative frequencies only
        taps = firwin(65, 3000/sample_rate, window='hamming')
        analytical = lfilter(taps, 1.0, samples)
        analytical = hilbert(np.real(analytical))
    else:
        # USB: positive frequencies only
        taps = firwin(65, 3000/sample_rate, window='hamming')
        analytical = lfilter(taps, 1.0, samples)
        analytical = hilbert(np.real(analytical))

    # Demodulate
    demod = np.real(analytical)

    # Normalize
    audio = demod / np.max(np.abs(demod)) * 0.95 
    return mono_to_stereo(audio)


def demodulate_signal(samples, sample_rate, mode='NFM'):
    """Advanced demodulation function supporting multiple modes"""
    samples = iq_correction(samples)
    if mode == 'NFM':
        return demodulate_nfm(samples, sample_rate)
    elif mode == 'WFM':
        return demodulate_wfm(samples, sample_rate)
    elif mode == 'AM':
        return demodulate_am(samples)
    elif mode == 'USB':
        return demodulate_ssb(samples, sample_rate, lower=False)
    elif mode == 'LSB':
        return demodulate_ssb(samples, sample_rate, lower=True)
    elif mode == 'RAW':
        return np.real(samples)  # Return raw I samples
    # return np.zeros_like(samples)  # Return silence if mode not recognized
    return np.zeros((len(samples), 2))  # Ensure it returns a shape of (n, 2)


def compute_fft(samples):
    """Compute normalized FFT with proper scaling"""
    # Apply window function to reduce spectral leakage
    window = np.hamming(len(samples))
    windowed_samples = samples * window

    # Compute FFT and shift zero frequency to center
    fft = np.fft.fftshift(np.fft.fft(windowed_samples))

    # Convert to power spectrum in dB, with proper scaling
    power_db = 20 * np.log10(np.abs(fft) + 1e-10)

    # Apply calibration factors
    system_gain = -30  # Adjustment for system gain
    ref_level = -70   # Reference level adjustment

    # Apply calibration and clip to reasonable range
    power_db = np.clip(power_db + system_gain + ref_level, -100, -20)

    return power_db


def estimate_bandwidth(psd, freqs, threshold_db=-20):
    """Estimate signal bandwidth using power spectral density"""
    # Convert to dB
    psd_db = 10 * np.log10(psd + 1e-10)
    max_power = np.max(psd_db)

    # Find frequencies above threshold
    mask = psd_db > (max_power + threshold_db)
    if not np.any(mask):
        return 0

    # Calculate bandwidth
    freq_range = freqs[mask]
    return freq_range[-1] - freq_range[0]


def estimate_modulation_index(samples):
    """Estimate modulation index using amplitude variation"""
    # Use magnitude of complex samples instead of Hilbert transform
    amplitude_env = np.abs(samples)
    phase_env = np.unwrap(np.angle(samples))

    # Calculate variance ratios
    amp_var = np.var(amplitude_env)
    phase_var = np.var(np.diff(phase_env))

    return phase_var / (amp_var + 1e-10)


def classify_signal(samples, sample_rate, bandwidth):
    """Classify signal type based on spectral characteristics"""
    # Calculate power spectral density
    freqs, psd = welch(samples, fs=sample_rate, nperseg=1024)

    # Calculate basic signal characteristics
    signal_bw = estimate_bandwidth(psd, freqs)
    modulation_index = estimate_modulation_index(samples)
    spectral_flatness = np.exp(np.mean(np.log(psd + 1e-10))) / np.mean(psd)

    # Classification logic
    if signal_bw > 150e3:
        if modulation_index > 0.8:
            return 'FM_BROADCAST'
    elif 8e3 <= signal_bw <= 16e3:
        if modulation_index < 0.3:
            return 'NARROW_FM'
    elif 8e3 <= signal_bw <= 10e3:
        if modulation_index < 0.2 and spectral_flatness < 0.3:
            return 'AM_BROADCAST'
    elif 2e3 <= signal_bw <= 3e3:
        if spectral_flatness < 0.2:
            return 'SSB'
    elif spectral_flatness > 0.7:
        return 'DIGITAL'

    return 'UNKNOWN'


def measure_signal_power(samples):
    """Calculate average power of signal in dB"""
    power = np.mean(np.abs(samples)**2)
    return 10 * np.log10(power + 1e-10)  # Add small value to prevent log(0)


def decode_mono(samples: np.ndarray, fs: int):
    """Decode FM modulation to mono audio."""
    demod_gain = fs / (2 * np.pi * np.pi * 75e3)  # 75e3 is the frequency deviation

    # FM Demodulation
    demod = demod_gain * np.angle(samples[:-1] * samples.conj()[1:])

    # Sample rate after decimation will be 41666.67
    decimation = 6

    # Decimate to get mono audio
    # mono = signal.decimate(demod, decimation, ftype="fir")
    mono = decimate(demod, decimation, ftype="fir")

    # De-emphasis is 75e-6 for North America, 50e-6 for everywhere else
    deemphasis = 75e-6

    # Create filter coefficients for de-emphasis
    bz, az = bilinear([1], [deemphasis, 1], fs=fs)

    # Apply the de-emphasis filter
    mono = lfilter(bz, az, mono)
    mono -= mono.mean()

    mono *= 0.75  # Volume factor
    mono *= 32768
    mono = mono.astype(np.int16)

    return mono
