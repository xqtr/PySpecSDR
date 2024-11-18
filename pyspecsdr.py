#!/usr/bin/python3

'''
 ____        ____                  ____  ____  ____  
|  _ \ _   _/ ___| _ __   ___  ___/ ___||  _ \|  _ \ 
| |_) | | | \___ \| '_ \ / _ \/ __\___ \| | | | |_) |
|  __/| |_| |___) | |_) |  __/ (__ ___) | |_| |  _ < 
|_|    \__, |____/| .__/ \___|\___|____/|____/|_| \_\
       |___/      |_|                                

PySpecSDR - Python SDR Spectrum Analyzer and Signal Processor
===========================================================

A feature-rich Software Defined Radio (SDR) spectrum analyzer with real-time 
visualization, demodulation, and signal analysis capabilities.

Features:
- Real-time spectrum analysis and waterfall display
- Multiple visualization modes (spectrum, waterfall, persistence, surface, gradient)
- FM, AM, SSB demodulation with audio output
- Frequency scanning and signal classification
- Bookmark management for frequencies of interest
- Automatic Gain Control (AGC)
- Recording capabilities for both RF and audio
- Band presets for common frequency ranges
- Configurable display and processing parameters

Requirements:
- RTL-SDR compatible device
- Python 3.7 or higher
- Dependencies listed in installation.txt

License: GPL-3.0-or-later

Copyright (c) 2024 [XQTR]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Author: XQTR
Email: xqtr@gmx.com // xqtr.xqtr@gmail.com
GitHub: https://github.com/xqtr/PySpecSDR
Version: 1.0.0
Last Updated: 2024/11/18

Usage:
    python3 pyspecsdr.py

Key Bindings:
    q - Quit
    h - Show help menu
    For full list of controls, press 'h' while running
'''

import numpy as np
import curses
from rtlsdr import RtlSdr
from scipy.signal import decimate
import sounddevice as sd
from scipy.signal import butter, lfilter
from scipy.signal import firwin
from scipy.signal import hilbert
from scipy.signal import welch
#import queue
#import threading
from collections import deque
import time
import os
import configparser
import json
import os.path
import wave
import struct

audio_buffer = deque(maxlen=24)  # Increased from 16 for better continuity
SAMPLES = 7
INTENSITY_CHARS = ' .,:|\\'  # Simple ASCII characters for intensity levels
BOOKMARK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sdr_bookmarks.json")
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sdr_settings.ini")

# Add global flag for audio availability
AUDIO_AVAILABLE = False
try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    pass

# Add these constants near the top of the file
AGC_TARGET_POWER = -30  # Target power level in dB
AGC_ENABLED = False     # Global flag for AGC state
AGC_UPDATE_INTERVAL = 0.5  # Seconds between AGC updates
AGC_STEP = 1.0         # Gain adjustment step size
last_agc_update = 0    # Track last AGC update time
SIGNAL_THRESHOLD = -40  # dB threshold for signal detection
SCAN_STEP = 100e3      # 100 kHz steps by default
MIN_SIGNAL_BANDWIDTH = 50e3  # Minimum bandwidth to consider as a signal
SCAN_DWELL_TIME = 0.1  # Seconds to dwell on each frequency
SCAN_ACTIVE = False    # Global flag for scan state

# Add near the top of the file with other constants
BAND_PRESETS = {
    'FM': (88e6, 108e6, "FM Radio"),
    'AM': (535e3, 1.7e6, "AM Radio"),
    'AIR': (118e6, 137e6, "Aircraft Band"),
    'WX': (162.4e6, 162.55e6, "Weather Radio"),
    'HAM2M': (144e6, 148e6, "2m Amateur Radio"),
    'HAM70CM': (420e6, 450e6, "70cm Amateur Radio"),
    'NOAA': (137e6, 138e6, "NOAA Weather Satellites"),
    'ADS-B': (1090e6, 1090e6, "ADS-B Aircraft Tracking"),
    'DAB': (174e6, 240e6, "Digital Audio Broadcasting"),
    'ISM': (433.05e6, 434.79e6, "ISM Band")
}

# Add these constants near the top with other constants
WATERFALL_HISTORY = []
WATERFALL_MAX_LINES = 30  # Number of history lines to keep
WATERFALL_MODE = False    # Toggle between spectrum and waterfall
WATERFALL_COLORS = [
    curses.COLOR_BLACK,   # Weakest signal
    curses.COLOR_BLUE,
    curses.COLOR_CYAN,
    curses.COLOR_GREEN,
    curses.COLOR_YELLOW,
    curses.COLOR_RED,     # Strongest signal
]

# Add these constants near the top with other constants
DEMOD_MODES = {
    'FM': {'name': 'FM', 'bandwidth': 200e3, 'description': 'Narrow FM'},
    'WFM': {'name': 'Wide FM', 'bandwidth': 180e3, 'description': 'Wide FM (Broadcast)'},
    'AM': {'name': 'AM', 'bandwidth': 10e3, 'description': 'Amplitude Modulation'},
    'USB': {'name': 'USB', 'bandwidth': 3e3, 'description': 'Upper Sideband'},
    'LSB': {'name': 'LSB', 'bandwidth': 3e3, 'description': 'Lower Sideband'},
    'RAW': {'name': 'RAW', 'bandwidth': None, 'description': 'Raw IQ Samples'}
}
CURRENT_DEMOD = 'FM'  # Default demodulation mode

# Add this with other constants near the top of the file
zoom_step = 0.1e6  # 100 kHz zoom step

# Add near the top with other constants
SIGNAL_TYPES = {
    'FM_BROADCAST': {
        'bandwidth': (150e3, 200e3),
        'pattern': 'wideband_fm',
        'description': 'FM Radio Broadcast'
    },
    'NARROW_FM': {
        'bandwidth': (10e3, 16e3),
        'pattern': 'narrowband_fm',
        'description': 'Narrow FM (Amateur/Business)'
    },
    'AM_BROADCAST': {
        'bandwidth': (8e3, 10e3),
        'pattern': 'am',
        'description': 'AM Radio Broadcast'
    },
    'SSB': {
        'bandwidth': (2.4e3, 3e3),
        'pattern': 'ssb',
        'description': 'Single Sideband'
    },
    'DIGITAL': {
        'bandwidth': (6e3, 50e3),
        'pattern': 'digital',
        'description': 'Digital Signal'
    }
}

# Add near other constants
PERSISTENCE_HISTORY = []
PERSISTENCE_ALPHA = 0.7  # Decay factor
PERSISTENCE_LENGTH = 10  # Number of traces to keep
PERSISTENCE_MODE = False

# Add near other constants
SURFACE_MODE = False
SURFACE_ANGLE = 45  # Viewing angle in degrees

# Add near other constants
GRADIENT_COLORS = [
    (0, 0, 0),      # Black
    (0, 0, 139),    # Dark Blue
    (0, 0, 255),    # Blue
    (0, 255, 255),  # Cyan
    (0, 255, 0),    # Green
    (255, 255, 0),  # Yellow
    (255, 0, 0),    # Red
]

# Add with other constants
DISPLAY_MODES = ['SPECTRUM', 'WATERFALL', 'PERSISTENCE', 'SURFACE', 'GRADIENT', 'VECTOR']
current_display_mode = 'SPECTRUM'

def init_colors():
    curses.start_color()
    curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_BLUE, curses.COLOR_BLACK)
    # Add waterfall color pairs (starting from 10 to avoid conflicts)
    for i, color in enumerate(WATERFALL_COLORS):
        curses.init_pair(10 + i, color, curses.COLOR_BLACK)

def showhelp(stdscr):
    stdscr.clear()
    stdscr.addstr("Help:   q - Quit\n")
    stdscr.addstr("B/b - increase/reduce bandwidth\n")
    stdscr.addstr("F/f - Change frequency up/down\n")
    stdscr.addstr("S/s - Increase/decrease samples\n")
    stdscr.addstr("G/g - Increase/decrease gain\n")
    stdscr.addstr("T/t - Increase/Decrease step\n")
    stdscr.addstr("x - Set Frequency\n")
    stdscr.addstr("k/l - Save/Load bookmark\n")
    stdscr.addstr("a - Toggle audio on/off\n")
    stdscr.addstr("Up/Down - Inc/decrease freq. by 1 MHz\n")
    stdscr.addstr("Right/Left - Inc/decrease freq. by 0.5 MHz\n")
    stdscr.addstr("R - Start/Stop audio recording\n")
    stdscr.addstr("A - Toggle AGC\n")
    stdscr.addstr("p - Band presets\n")
    stdscr.addstr("c - Frequency scanner\n")
    stdscr.addstr("w - Save settings\n")
    stdscr.addstr("d - Demodulation modes\n")
    stdscr.addstr("m - Cycle display modes\n")
    stdscr.addstr("1/2/3/4/5 - Choose display mode\n")
    stdscr.addstr("Press a key to continue\n")

    stdscr.nodelay(False)
    stdscr.getch()
    stdscr.nodelay(True)
    stdscr.clear()

def setfreq(stdscr):
    max_height, max_width = stdscr.getmaxyx()
    stdscr.addstr(0,0," "*(max_width-1))
    stdscr.addstr(0,0,"Enter frequency in Hz: ",curses.color_pair(1) | curses.A_BOLD)
    # Enable echo and cursor
    curses.echo()
    curses.curs_set(1)
    stdscr.nodelay(False) 
    freq = stdscr.getstr()
    # Disable echo and cursor after input
    curses.noecho()
    curses.curs_set(0)
    stdscr.nodelay(True)
    return freq.decode('utf-8')  # Convert bytes to string

def draw_spectrogram(stdscr, freq_data, frequencies, center_freq, bandwidth, gain, step, is_recording=False, recording_duration=None):
    """
    Draw the spectrogram and header information in the terminal using curses.
    """
    global SAMPLES
    stdscr.clear()
    max_height, max_width = stdscr.getmaxyx()

    # Modify the header display to accommodate recording status
    x_pos = 0
    if is_recording:
        recording_text = f"Recording: {recording_duration:.1f}s"
        stdscr.addstr(0, max_width - len(recording_text) - 1, recording_text, 
                     curses.color_pair(3) | curses.A_BOLD)
        # Adjust available width for other header items
        available_width = max_width - len(recording_text) - 2
    else:
        available_width = max_width

    # Draw the colored header
    freq_text = f"req: {center_freq/1e6:.6f} MHz"
    bw_text = f"andwidth: {bandwidth/1e6:.2f} MHz"
    gain_text = f"ain: {gain}"
    samples_text = f"amples: {2**SAMPLES}"
    step_text = f"ep: {step/1e6:.3f} MHz"
    
    x_pos = 0
    stdscr.addstr(0, x_pos, "F", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, freq_text, curses.color_pair(2) )
    x_pos += len(freq_text) + 3
    stdscr.addstr(0, x_pos, "B", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, bw_text, curses.color_pair(2))
    x_pos += len(bw_text) + 3
    stdscr.addstr(0, x_pos, "G", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, gain_text, curses.color_pair(2))
    x_pos = 0
    stdscr.addstr(1, x_pos, "S", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+1, samples_text, curses.color_pair(2))
    x_pos += len(samples_text) + 3
    stdscr.addstr(1, x_pos, "S", curses.color_pair(2))
    stdscr.addstr(1, x_pos+1, "t", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+2, step_text, curses.color_pair(2))
    x_pos += len(step_text) + 4
    stdscr.addstr(1, x_pos, "H", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+1, "elp", curses.color_pair(2))

    # Select the range of frequencies within the desired bandwidth
    half_bw = bandwidth / 2
    mask = (frequencies >= center_freq - half_bw) & (frequencies <= center_freq + half_bw)

    if not np.any(mask):
        stdscr.addstr(2, 0, "No data to display in the selected range.", curses.A_BOLD)
        stdscr.refresh()
        return

    freq_data = freq_data[mask]
    frequencies = frequencies[mask]

    # Resample the data to fit the screen width
    resampled_data = np.interp(
        np.linspace(0, len(freq_data) - 1, max_width - 1),
        np.arange(len(freq_data)),
        freq_data
    )
    resampled_freqs = np.linspace(
        center_freq - half_bw,
        center_freq + half_bw,
        max_width - 1
    )

    # Normalize data for spectrogram display
    min_val = np.min(resampled_data[np.isfinite(resampled_data)])  # Ignore NaN values
    max_val = np.max(resampled_data[np.isfinite(resampled_data)])  # Ignore NaN values
    
    # Handle case where min_val equals max_val
    if min_val == max_val:
        normalized_data = np.zeros_like(resampled_data)
    else:
        # Replace NaN values with min_val before normalizing
        resampled_data = np.nan_to_num(resampled_data, nan=min_val)
        normalized_data = (resampled_data - min_val) / (max_val - min_val)

    # Ensure all values are finite
    normalized_data = np.clip(normalized_data, 0, 1)

    # Add dB scale on the y-axis
    db_range = max_val - min_val
    db_step = db_range / (max_height - 4)
    for y in range(3, max_height - 1):
        db_value = max_val - (y - 3) * db_step
        if y % 3 == 0:
            db_label = f"{db_value:4.0f}dB"
            try:
                stdscr.addstr(y, 0, db_label, curses.color_pair(2))
            except curses.error:
                pass

    # Adjust the x position of the spectrogram
    x_offset = 7
    for x in range(len(normalized_data)):
        value = normalized_data[x]
        if np.isfinite(value):  # Check if value is valid
            height = int(value * (max_height - 3))
            
            # Draw vertical bars with simple ASCII characters
            for y in range(max_height - 2, max_height - 2 - height, -1):
                intensity = value * (1 - ((max_height - 2 - y) / max_height))
                char_idx = min(len(INTENSITY_CHARS) - 1, 
                             int(intensity * len(INTENSITY_CHARS)))
                
                try:
                    stdscr.addstr(y, x + x_offset, INTENSITY_CHARS[char_idx])
                except curses.error:
                    pass

    # Adjust frequency labels position
    step = max(1, (max_width - 1 - x_offset) // 5)
    label_positions = range(x_offset, max_width - 1, step)
    label_freqs = np.linspace(center_freq - half_bw, center_freq + half_bw, len(label_positions))
    
    label_line = ""
    current_pos = 0
    for pos, freq in zip(label_positions, label_freqs):
        label = f"{freq/1e6:.2f}MHz"
        if current_pos + len(label) <= max_width - 1:
            label_line += " " * (pos - current_pos) + label
            current_pos = pos + len(label)

    stdscr.addstr(max_height - 1, 0, label_line[:max_width - 1])
    stdscr.refresh()

    # Add signal strength indicator
    peak_power = np.max(freq_data)
    avg_power = np.mean(freq_data)
    strength_text = f"Peak: {peak_power:.1f} dB Avg: {avg_power:.1f} dB"
    stdscr.addstr(1, max_width - len(strength_text) - 1, strength_text, curses.color_pair(2))

    # Add AGC status to header
    agc_text = "AGC: ON" if AGC_ENABLED else "AGC: OFF"
    stdscr.addstr(1, max_width - len(agc_text) - len(strength_text) - 3, 
                 agc_text, 
                 curses.color_pair(4) if AGC_ENABLED else curses.color_pair(2))

def demodulate_signal(samples, sample_rate, mode='FM'):
    """Advanced demodulation function supporting multiple modes"""
    if mode == 'FM':
        return demodulate_fm(samples, sample_rate)
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
    return np.zeros_like(samples)  # Return silence if mode not recognized

def demodulate_fm(samples, sample_rate, target_rate=44100):
    """Simplified FM demodulation"""
    # Basic FM demodulation
    demod = np.angle(samples[1:] * np.conj(samples[:-1]))
    
    # Simple scaling
    demod = demod * (sample_rate / (2 * np.pi))

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
    return audio

def demodulate_wfm(samples, sample_rate, target_rate=44100):
    """Wide FM demodulation optimized for broadcast FM"""
    # Pre-emphasis correction filter
    emphasis = firwin(65, 2.125e3/sample_rate, window='hamming')
    samples = lfilter(emphasis, 1.0, samples)
    
    # FM demodulation with wider deviation
    demod = np.angle(samples[1:] * np.conj(samples[:-1]))
    demod = demod * (sample_rate / (2 * np.pi))
    
    # De-emphasis filter (75µs time constant)
    deemph_tc = 75e-6
    deemph = np.exp(-1/(deemph_tc * sample_rate))
    demod = lfilter([1-deemph], [1, -deemph], demod)
    
    # Decimate to target rate
    decimation_factor = int(sample_rate / target_rate)
    audio = decimate(demod, decimation_factor)
    
    return audio / np.max(np.abs(audio)) * 0.95

def demodulate_am(samples):
    """AM demodulation using envelope detection"""
    # Get the amplitude envelope
    envelope = np.abs(samples)
    
    # DC removal (high-pass filter)
    envelope = envelope - np.mean(envelope)
    
    # Normalize
    return envelope / np.max(np.abs(envelope)) * 0.95

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
    return demod / np.max(np.abs(demod)) * 0.95

def audio_callback(outdata, frames, time, status):
    """Simplified audio callback"""
    if len(audio_buffer) > 0:
        data = np.concatenate(list(audio_buffer))
        if len(data) >= frames:
            outdata[:] = data[:frames].reshape(-1, 1)
            audio_buffer.clear()
            if len(data) > frames:
                audio_buffer.append(data[frames:])
        else:
            outdata[:] = np.zeros((frames, 1))
    else:
        outdata[:] = np.zeros((frames, 1))

def load_bookmarks():
    try:
        with open(BOOKMARK_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_bookmark(name, freq):
    bookmarks = load_bookmarks()
    bookmarks[name] = freq
    with open(BOOKMARK_FILE, 'w') as f:
        json.dump(bookmarks, f, indent=2)

def add_bookmark(stdscr, freq):
    max_height, max_width = stdscr.getmaxyx()
    stdscr.addstr(0, 0, " "*(max_width-1))
    stdscr.addstr(0, 0, "Enter bookmark name: ", curses.color_pair(1) | curses.A_BOLD)
    curses.echo()
    curses.curs_set(1)
    stdscr.nodelay(False)
    name = stdscr.getstr().decode('utf-8')
    curses.noecho()
    curses.curs_set(0)
    stdscr.nodelay(True)
    if name:
        save_bookmark(name, freq)

def show_bookmarks(stdscr):
    bookmarks = load_bookmarks()
    if not bookmarks:
        return None
    
    stdscr.clear()
    stdscr.addstr("Bookmarks:\n\n")
    for i, (name, freq) in enumerate(bookmarks.items()):
        stdscr.addstr(f"{i+1}. {name}: {freq/1e6:.3f} MHz\n")
    stdscr.addstr("\nEnter number to select (or any other key to cancel): ")
    curses.echo()
    curses.curs_set(1)

    stdscr.nodelay(False)
    try:
        choice = int(stdscr.getstr().decode('utf-8'))
        if 1 <= choice <= len(bookmarks):
            return list(bookmarks.values())[choice-1]
    except (ValueError, IndexError):
        pass
    finally:
        stdscr.nodelay(True)
        curses.noecho()
        curses.curs_set(0)
    return None

def record_signal(sdr, duration, filename):
    """Record raw IQ samples to a file"""
    samples = sdr.read_samples(int(duration * sdr.sample_rate))
    np.save(filename, samples)
    return samples

def play_recorded_signal(filename):
    """Play back recorded IQ samples"""
    samples = np.load(filename)
    return samples

def start_audio_recording(filename, sample_rate=44100):
    """Start recording audio to a WAV file"""
    wav_file = wave.open(filename, 'wb')
    wav_file.setnchannels(1)  # Mono
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

def save_settings(sdr, bandwidth, freq_step, samples, agc_enabled):
    """Save current SDR settings to a config file"""
    config = configparser.ConfigParser()
    
    # Find current band (if any)
    current_band = None
    for band, (start, end, _) in BAND_PRESETS.items():
        if start <= sdr.center_freq <= end:
            current_band = band
            break
    
    config['SDR'] = {
        'frequency': str(sdr.center_freq),
        'sample_rate': str(sdr.sample_rate),
        'gain': str(sdr.gain),
        'bandwidth': str(bandwidth),
        'freq_step': str(freq_step),
        'samples': str(samples),
        'agc_enabled': str(agc_enabled),
        'current_band': str(current_band) if current_band else ''
    }
    
    with open(SETTINGS_FILE, 'w') as configfile:
        config.write(configfile)

def load_settings():
    """Load SDR settings from config file"""
    config = configparser.ConfigParser()
    default_settings = {
        'frequency': '92.5e6',
        'sample_rate': '1.024e6',
        'gain': 'auto',  # Keep as string for 'auto'
        'bandwidth': '2e6',
        'freq_step': '0.1e6',
        'samples': '7',
        'agc_enabled': 'False',
        'current_band': ''
    }
    
    if os.path.exists(SETTINGS_FILE):
        config.read(SETTINGS_FILE)
        if 'SDR' in config:
            return {
                'frequency': float(config['SDR'].get('frequency', default_settings['frequency'])),
                'sample_rate': float(config['SDR'].get('sample_rate', default_settings['sample_rate'])),
                'gain': config['SDR'].get('gain', default_settings['gain']),  # Keep as string
                'bandwidth': float(config['SDR'].get('bandwidth', default_settings['bandwidth'])),
                'freq_step': float(config['SDR'].get('freq_step', default_settings['freq_step'])),
                'samples': int(config['SDR'].get('samples', default_settings['samples'])),
                'agc_enabled': config['SDR'].get('agc_enabled', default_settings['agc_enabled']) == 'True',
                'current_band': config['SDR'].get('current_band', default_settings['current_band'])
            }
    
    # Convert default settings to appropriate types
    return {
        'frequency': float(default_settings['frequency']),
        'sample_rate': float(default_settings['sample_rate']),
        'gain': default_settings['gain'],  # Keep as string
        'bandwidth': float(default_settings['bandwidth']),
        'freq_step': float(default_settings['freq_step']),
        'samples': int(default_settings['samples']),
        'agc_enabled': default_settings['agc_enabled'] == 'True',
        'current_band': default_settings['current_band']
    }

def measure_signal_power(samples):
    """Calculate average power of signal in dB"""
    power = np.mean(np.abs(samples)**2)
    return 10 * np.log10(power + 1e-10)  # Add small value to prevent log(0)

def adjust_gain(sdr, current_power, gainindex):
    """Adjust gain to reach target power level"""
    power_diff = AGC_TARGET_POWER - current_power
    
    # Only adjust if difference is significant
    if abs(power_diff) < 2:  # 2 dB threshold
        return gainindex

    if power_diff > 0:  # Signal too weak, increase gain
        gainindex += 1
        if gainindex <= len(sdr.valid_gains_db) - 1:
            sdr.gain = sdr.valid_gains_db[gainindex]
        else:
            gainindex = len(sdr.valid_gains_db) - 1
    else:  # Signal too strong, decrease gain
        gainindex -= 1
        if gainindex >= 0:
            sdr.gain = sdr.valid_gains_db[gainindex]
        else:
            gainindex = 0
            
    return gainindex

def show_band_presets(stdscr):
    """Display and select from available band presets"""
    stdscr.clear()
    stdscr.addstr("Available Band Presets:\n\n", curses.color_pair(1) | curses.A_BOLD)
    
    for i, (key, (start, end, description)) in enumerate(BAND_PRESETS.items(), 1):
        line = f"{i}. {key}: {description} ({start/1e6:.3f}-{end/1e6:.3f} MHz)\n"
        stdscr.addstr(line, curses.color_pair(2))
    
    stdscr.addstr("\nEnter number to select (or any other key to cancel): ", 
                 curses.color_pair(1) | curses.A_BOLD)
    
    curses.echo()
    curses.curs_set(1)
    stdscr.nodelay(False)
    
    try:
        choice = int(stdscr.getstr().decode('utf-8'))
        if 1 <= choice <= len(BAND_PRESETS):
            band_key = list(BAND_PRESETS.keys())[choice-1]
            start, end, _ = BAND_PRESETS[band_key]
            center_freq = start + (end - start)/2
            bandwidth = min(end - start, 2e6)  # Limit bandwidth to 2MHz or band width
            return center_freq, bandwidth
    except (ValueError, IndexError):
        pass
    finally:
        stdscr.nodelay(True)
        curses.noecho()
        curses.curs_set(0)
    
    return None, None

def scan_frequencies(sdr, start_freq, end_freq, threshold, step=SCAN_STEP):
    """Scan frequency range and detect signals above threshold"""
    signals = []
    current_freq = start_freq
    samples_per_scan = int(SCAN_DWELL_TIME * sdr.sample_rate)
    
    while current_freq <= end_freq:
        try:
            sdr.center_freq = current_freq
            time.sleep(0.01)  # Small delay to let SDR settle
            samples = sdr.read_samples(samples_per_scan)
            
            if len(samples) == 0:
                continue
            
            # Compute power spectrum
            spectrum = np.fft.fftshift(np.fft.fft(samples))
            power_db = 10 * np.log10(np.abs(spectrum)**2 + 1e-10)
            max_power = np.max(power_db)
            
            if max_power > threshold:
                # Estimate signal bandwidth
                mask = power_db > threshold
                bandwidth = np.sum(mask) * (sdr.sample_rate / len(power_db))
                
                if bandwidth > MIN_SIGNAL_BANDWIDTH:
                    # Classify signal
                    signal_type = classify_signal(samples, sdr.sample_rate, bandwidth)
                    
                    signals.append({
                        'frequency': current_freq,
                        'power': max_power,
                        'bandwidth': bandwidth,
                        'type': signal_type
                    })
        
        except Exception as e:
            stdscr.addstr(max_height-1, 0, f"Error: {str(e)}", curses.color_pair(3))
            stdscr.refresh()
            time.sleep(0.5)
        
        current_freq += step
    
    # Remove duplicates and sort by frequency
    unique_signals = []
    seen_freqs = set()
    for signal in sorted(signals, key=lambda x: x['frequency']):
        rounded_freq = round(signal['frequency'] / 100e3) * 100e3
        if rounded_freq not in seen_freqs:
            seen_freqs.add(rounded_freq)
            unique_signals.append(signal)
    
    return unique_signals

def show_scanner_menu(stdscr):
    """Display scanner configuration menu"""
    stdscr.clear()
    stdscr.addstr("Frequency Scanner Configuration:\n\n", curses.color_pair(1) | curses.A_BOLD)
    
    # Get signal threshold
    stdscr.addstr("Enter signal strength threshold ", curses.color_pair(2))
    stdscr.addstr("(dB, recommended -40 to -20): ", curses.color_pair(2))
    curses.echo()
    stdscr.nodelay(False)
    try:
        threshold = float(stdscr.getstr().decode('utf-8'))
    except ValueError:
        threshold = -40  # Default value if invalid input
    
    stdscr.clear()
    stdscr.addstr("\nAvailable Band Presets:\n\n", curses.color_pair(1) | curses.A_BOLD)
    
    # Show band presets
    for i, (key, (start, end, description)) in enumerate(BAND_PRESETS.items(), 1):
        line = f"{i}. Scan {key}: {description} ({start/1e6:.3f}-{end/1e6:.3f} MHz)\n"
        stdscr.addstr(line, curses.color_pair(2))
    
    # Custom range option
    stdscr.addstr(f"{len(BAND_PRESETS) + 1}. Custom frequency range\n", curses.color_pair(2))
    
    stdscr.addstr("\nEnter choice (or any other key to cancel): ", 
                 curses.color_pair(1) | curses.A_BOLD)
    
    try:
        choice = int(stdscr.getstr().decode('utf-8'))
        if 1 <= choice <= len(BAND_PRESETS):
            band_key = list(BAND_PRESETS.keys())[choice-1]
            start, end, _ = BAND_PRESETS[band_key]
            return start, end, threshold
        elif choice == len(BAND_PRESETS) + 1:
            # Get custom range
            stdscr.addstr("\nEnter start frequency (MHz): ")
            start = float(stdscr.getstr().decode('utf-8')) * 1e6
            stdscr.addstr("Enter end frequency (MHz): ")
            end = float(stdscr.getstr().decode('utf-8')) * 1e6
            return start, end, threshold
    except (ValueError, IndexError):
        pass
    finally:
        stdscr.nodelay(True)
        curses.noecho()
        curses.curs_set(0)
        stdscr.clear()
    
    return None, None, None

def display_scan_results(stdscr, signals, threshold):
    """Display scanner results and allow selection"""
    try:
        if not signals:
            stdscr.addstr("\nNo signals found above threshold.\n", curses.color_pair(3))
            stdscr.addstr("\nPress any key to continue...", curses.color_pair(2))
            stdscr.getch()
            return None
        
        stdscr.clear()
        max_height, max_width = stdscr.getmaxyx()
        current_line = 0
        
        header = f"Detected Signals ({len(signals)} found):\n\n"
        stdscr.addstr(current_line, 0, header, curses.color_pair(1) | curses.A_BOLD)
        current_line += 2
        
        for i, signal in enumerate(signals, 1):
            if current_line >= max_height - 3:
                break
            
            # Format signal information with type
            power_str = f"{signal['power']:.1f}".rjust(6)
            freq_str = f"{signal['frequency']/1e6:.3f}".rjust(8)
            bw_str = f"{signal['bandwidth']/1e3:.1f}".rjust(6)
            type_str = signal['type'].ljust(15)
            
            line = f"{str(i).rjust(3)}. {freq_str} MHz  Power: {power_str} dB  BW: {bw_str} kHz  Type: {type_str}"
            
            # Color code by signal type
            if signal['type'] == 'FM_BROADCAST':
                color = curses.color_pair(4)  # Green
            elif signal['type'] == 'DIGITAL':
                color = curses.color_pair(5)  # Cyan
            elif signal['type'] == 'UNKNOWN':
                color = curses.color_pair(2)  # White
            else:
                color = curses.color_pair(1)  # Yellow
            
            if len(line) > max_width - 1:
                line = line[:max_width - 4] + "..."
            
            stdscr.addstr(current_line, 0, line, color)
            current_line += 1
        
        # Add selection prompt
        if current_line < max_height - 2:
            prompt = "\nEnter number to tune to signal (or any other key to cancel): "
            stdscr.addstr(current_line + 1, 0, prompt, 
                         curses.color_pair(1) | curses.A_BOLD)
        
        stdscr.refresh()
        curses.echo()
        curses.curs_set(1)
        stdscr.nodelay(False)
        
        try:
            choice = int(stdscr.getstr().decode('utf-8'))
            if 1 <= choice <= len(signals):
                return signals[choice-1]['frequency']
        except (ValueError, IndexError):
            pass
        finally:
            stdscr.nodelay(True)
            curses.noecho()
            curses.curs_set(0)
        
    except curses.error:
        pass
    
    return None

def draw_scanning_status(stdscr, current_freq, start_freq, end_freq):
    """Draw scanning progress at the top of the screen"""
    try:
        max_height, max_width = stdscr.getmaxyx()
        progress = (current_freq - start_freq) / (end_freq - start_freq)
        
        # Calculate progress bar width (70% of screen width)
        bar_width = int(max_width * 0.7)
        filled = int(bar_width * progress)
        
        # Create the status text
        status_text = f"Scanning: {current_freq/1e6:8.3f} MHz "
        progress_bar = "[" + "=" * filled + " " * (bar_width - filled) + "]"
        percentage = f" {progress * 100:3.0f}%"
        
        # Calculate starting position to center the display
        total_length = len(status_text) + len(progress_bar) + len(percentage)
        start_pos = max(0, (max_width - total_length) // 2)
        
        # Draw the components
        stdscr.addstr(0, 0, " " * max_width)  # Clear the line
        stdscr.addstr(0, start_pos, status_text, curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(1, start_pos, progress_bar, curses.color_pair(2))
        stdscr.addstr(1, start_pos + len(progress_bar), percentage, curses.color_pair(4))
        stdscr.refresh()
    except curses.error:
        pass  # Ignore curses errors

def draw_waterfall(stdscr, freq_data, frequencies, center_freq, bandwidth, gain, step, 
                  is_recording=False, recording_duration=None):
    """Draw the waterfall display"""
    global WATERFALL_HISTORY
    max_height, max_width = stdscr.getmaxyx()

    # Add current data to history
    WATERFALL_HISTORY.append(freq_data)
    if len(WATERFALL_HISTORY) > WATERFALL_MAX_LINES:
        WATERFALL_HISTORY.pop(0)

    # Draw header (reuse from spectrum display)
    x_pos = 0
    if is_recording:
        recording_text = f"Recording: {recording_duration:.1f}s"
        stdscr.addstr(0, max_width - len(recording_text) - 1, recording_text, 
                     curses.color_pair(3) | curses.A_BOLD)
        available_width = max_width - len(recording_text) - 2
    else:
        available_width = max_width

    # Draw the colored header (similar to spectrum display)
    freq_text = f"req: {center_freq/1e6:.6f} MHz"
    bw_text = f"andwidth: {bandwidth/1e6:.2f} MHz"
    gain_text = f"ain: {gain}"
    samples_text = f"amples: {2**SAMPLES}"
    step_text = f"ep: {step/1e6:.3f} MHz"
    
    x_pos = 0
    stdscr.addstr(0, x_pos, "F", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, freq_text, curses.color_pair(2) )
    x_pos += len(freq_text) + 3
    stdscr.addstr(0, x_pos, "B", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, bw_text, curses.color_pair(2))
    x_pos += len(bw_text) + 3
    stdscr.addstr(0, x_pos, "G", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, gain_text, curses.color_pair(2))
    x_pos = 0
    stdscr.addstr(1, x_pos, "S", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+1, samples_text, curses.color_pair(2))
    x_pos += len(samples_text) + 3
    stdscr.addstr(1, x_pos, "S", curses.color_pair(2))
    stdscr.addstr(1, x_pos+1, "t", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+2, step_text, curses.color_pair(2))
    x_pos += len(step_text) + 4
    stdscr.addstr(1, x_pos, "H", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+1, "elp", curses.color_pair(2))

    # Draw waterfall
    display_height = max_height - 3  # Reserve space for header and labels
    display_width = max_width - 8    # Reserve space for dB scale

    # Normalize all data for consistent coloring
    all_data = np.array(WATERFALL_HISTORY)
    min_val = np.min(all_data[np.isfinite(all_data)])
    max_val = np.max(all_data[np.isfinite(all_data)])
    
    # Draw dB scale on the left
    db_range = max_val - min_val
    for i in range(display_height):
        db_value = max_val - (i * db_range / display_height)
        if i % 3 == 0:  # Show scale every 3 lines
            db_label = f"{db_value:4.0f}dB"
            try:
                stdscr.addstr(i + 2, 0, db_label, curses.color_pair(2))
            except curses.error:
                pass

    # Draw each line of the waterfall
    for y, line_data in enumerate(reversed(WATERFALL_HISTORY)):
        if y >= display_height:
            break

        # Resample data to fit screen width
        resampled = np.interp(
            np.linspace(0, len(line_data) - 1, display_width),
            np.arange(len(line_data)),
            line_data
        )

        # Draw each point in the line
        for x, value in enumerate(resampled):
            if not np.isfinite(value):
                continue

            # Normalize value and select color
            norm_value = (value - min_val) / (max_val - min_val)
            color_idx = min(len(WATERFALL_COLORS) - 1,
                          int(norm_value * len(WATERFALL_COLORS)))
            
            try:
                stdscr.addstr(y + 2, x + 8, "▀",  # Use unicode block character
                            curses.color_pair(10 + color_idx))
            except curses.error:
                pass

    # Draw frequency labels at bottom
    freq_step = bandwidth / 5
    for i in range(6):
        freq = center_freq - bandwidth/2 + i * freq_step
        label = f"{freq/1e6:.2f}"
        pos = int(8 + (i * display_width/5))
        try:
            stdscr.addstr(display_height + 2, pos, label, curses.color_pair(2))
        except curses.error:
            pass

    stdscr.refresh()

def show_demod_menu(stdscr):
    """Display demodulation mode selection menu"""
    stdscr.clear()
    stdscr.addstr("Select Demodulation Mode:\n\n", curses.color_pair(1) | curses.A_BOLD)
    
    for i, (mode, info) in enumerate(DEMOD_MODES.items(), 1):
        line = f"{i}. {info['name']}: {info['description']}"
        if mode == CURRENT_DEMOD:
            line += " (Current)"
            stdscr.addstr(line + "\n", curses.color_pair(4) | curses.A_BOLD)
        else:
            stdscr.addstr(line + "\n", curses.color_pair(2))
    
    stdscr.addstr("\nEnter choice (or any other key to cancel): ", 
                 curses.color_pair(1) | curses.A_BOLD)
    
    curses.echo()
    curses.curs_set(1)
    stdscr.nodelay(False)
    
    try:
        choice = int(stdscr.getstr().decode('utf-8'))
        if 1 <= choice <= len(DEMOD_MODES):
            return list(DEMOD_MODES.keys())[choice-1]
    except (ValueError, IndexError):
        pass
    finally:
        stdscr.nodelay(True)
        curses.noecho()
        curses.curs_set(0)
    
    return None

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

def draw_persistence(stdscr, freq_data, frequencies, center_freq, bandwidth, gain, step):
    """Draw spectrum with persistence effect"""
    global PERSISTENCE_HISTORY
    max_height, max_width = stdscr.getmaxyx()
    
    # Draw the header (copied from spectrum display)
    x_pos = 0
    freq_text = f"req: {center_freq/1e6:.6f} MHz"
    bw_text = f"andwidth: {bandwidth/1e6:.2f} MHz"
    gain_text = f"ain: {gain}"
    samples_text = f"amples: {2**SAMPLES}"
    step_text = f"ep: {step/1e6:.3f} MHz"
    
    x_pos = 0
    stdscr.addstr(0, x_pos, "F", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, freq_text, curses.color_pair(2))
    x_pos += len(freq_text) + 3
    stdscr.addstr(0, x_pos, "B", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, bw_text, curses.color_pair(2))
    x_pos += len(bw_text) + 3
    stdscr.addstr(0, x_pos, "G", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, gain_text, curses.color_pair(2))
    x_pos = 0
    stdscr.addstr(1, x_pos, "S", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+1, samples_text, curses.color_pair(2))
    x_pos += len(samples_text) + 3
    stdscr.addstr(1, x_pos, "S", curses.color_pair(2))
    stdscr.addstr(1, x_pos+1, "t", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+2, step_text, curses.color_pair(2))
    x_pos += len(step_text) + 4
    stdscr.addstr(1, x_pos, "H", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+1, "elp", curses.color_pair(2))

    # Add current data to history
    PERSISTENCE_HISTORY.append(freq_data)
    if len(PERSISTENCE_HISTORY) > PERSISTENCE_LENGTH:
        PERSISTENCE_HISTORY.pop(0)

    # Draw each trace with decreasing intensity
    for i, historical_data in enumerate(PERSISTENCE_HISTORY):
        alpha = PERSISTENCE_ALPHA ** (PERSISTENCE_LENGTH - i)
        color_pair = int(1 + (5 * (1 - alpha)))  # Map alpha to color pairs 1-6
        
        # Draw spectrum line
        for x in range(max_width):
            try:
                y = int(max_height - 2 - (historical_data[x] / 100 * (max_height - 3)))
                if 2 <= y < max_height - 1:
                    stdscr.addstr(y, x, '▪', curses.color_pair(color_pair))
            except curses.error:
                pass

def draw_surface_plot(stdscr, freq_data, frequencies, center_freq, bandwidth, gain, step):
    """Draw spectrum as pseudo-3D surface"""
    max_height, max_width = stdscr.getmaxyx()
        
    # Draw the colored header (similar to spectrum display)
    freq_text = f"req: {center_freq/1e6:.6f} MHz"
    bw_text = f"andwidth: {bandwidth/1e6:.2f} MHz"
    gain_text = f"ain: {gain}"
    samples_text = f"amples: {2**SAMPLES}"
    step_text = f"ep: {step/1e6:.3f} MHz"
    
    x_pos = 0
    stdscr.addstr(0, x_pos, "F", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, freq_text, curses.color_pair(2) )
    x_pos += len(freq_text) + 3
    stdscr.addstr(0, x_pos, "B", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, bw_text, curses.color_pair(2))
    x_pos += len(bw_text) + 3
    stdscr.addstr(0, x_pos, "G", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, gain_text, curses.color_pair(2))
    x_pos = 0
    stdscr.addstr(1, x_pos, "S", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+1, samples_text, curses.color_pair(2))
    x_pos += len(samples_text) + 3
    stdscr.addstr(1, x_pos, "S", curses.color_pair(2))
    stdscr.addstr(1, x_pos+1, "t", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+2, step_text, curses.color_pair(2))
    x_pos += len(step_text) + 4
    stdscr.addstr(1, x_pos, "H", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+1, "elp", curses.color_pair(2))
    
    # Calculate isometric projection
    angle_rad = np.radians(SURFACE_ANGLE)
    for x in range(max_width):
        magnitude = freq_data[x]
        for y in range(int(magnitude)):
            screen_x = int(x - y * np.cos(angle_rad))
            screen_y = int(max_height - y * np.sin(angle_rad))
            
            if 0 <= screen_x < max_width and 0 <= screen_y < max_height:
                try:
                    stdscr.addstr(screen_y, screen_x, '█', 
                                curses.color_pair(1 + (y % 5)))
                except curses.error:
                    pass

def interpolate_color(color1, color2, factor):
    """Interpolate between two RGB colors"""
    return tuple(int(color1[i] + (color2[i] - color1[i]) * factor) for i in range(3))

def get_gradient_color(value):
    """Get smooth color from gradient for given value between 0 and 1"""
    if value <= 0:
        return GRADIENT_COLORS[0]
    if value >= 1:
        return GRADIENT_COLORS[-1]
    
    segment_size = 1.0 / (len(GRADIENT_COLORS) - 1)
    segment = int(value / segment_size)
    factor = (value - segment * segment_size) / segment_size
    
    return interpolate_color(GRADIENT_COLORS[segment], 
                           GRADIENT_COLORS[segment + 1], 
                           factor)

def draw_gradient_waterfall(stdscr, freq_data, frequencies, center_freq, bandwidth, gain, step):
    """Draw waterfall with smooth color gradients"""
    global WATERFALL_HISTORY
    max_height, max_width = stdscr.getmaxyx()
    
    # Draw the colored header (similar to spectrum display)
    freq_text = f"req: {center_freq/1e6:.6f} MHz"
    bw_text = f"andwidth: {bandwidth/1e6:.2f} MHz"
    gain_text = f"ain: {gain}"
    samples_text = f"amples: {2**SAMPLES}"
    step_text = f"ep: {step/1e6:.3f} MHz"
    
    x_pos = 0
    stdscr.addstr(0, x_pos, "F", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, freq_text, curses.color_pair(2) )
    x_pos += len(freq_text) + 3
    stdscr.addstr(0, x_pos, "B", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, bw_text, curses.color_pair(2))
    x_pos += len(bw_text) + 3
    stdscr.addstr(0, x_pos, "G", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, gain_text, curses.color_pair(2))
    x_pos = 0
    stdscr.addstr(1, x_pos, "S", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+1, samples_text, curses.color_pair(2))
    x_pos += len(samples_text) + 3
    stdscr.addstr(1, x_pos, "S", curses.color_pair(2))
    stdscr.addstr(1, x_pos+1, "t", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+2, step_text, curses.color_pair(2))
    x_pos += len(step_text) + 4
    stdscr.addstr(1, x_pos, "H", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+1, "elp", curses.color_pair(2))

    # Add current data to history
    WATERFALL_HISTORY.append(freq_data)
    if len(WATERFALL_HISTORY) > WATERFALL_MAX_LINES:
        WATERFALL_HISTORY.pop(0)

    # Normalize data
    all_data = np.array(WATERFALL_HISTORY)
    min_val = np.min(all_data[np.isfinite(all_data)])
    max_val = np.max(all_data[np.isfinite(all_data)])
    
    # Draw each line with smooth color gradient
    for y, line_data in enumerate(reversed(WATERFALL_HISTORY)):
        if y >= max_height - 3:
            break
            
        for x, value in enumerate(line_data):
            if x >= max_width - 1:
                break
                
            if np.isfinite(value):
                normalized = (value - min_val) / (max_val - min_val)
                color = get_gradient_color(normalized)
                
                # Map RGB color to nearest terminal color
                color_index = (int(color[0] / 86) * 36 + 
                             int(color[1] / 86) * 6 + 
                             int(color[2] / 86))
                
                try:
                    stdscr.addstr(y + 2, x, '▀', 
                                curses.color_pair(10 + (color_index % 6)))
                except curses.error:
                    pass

def draw_vector_display(stdscr, samples, center_freq, bandwidth, gain, step):
    """Draw I/Q samples as vector constellation"""
    max_height, max_width = stdscr.getmaxyx()
    
    # Create coordinate system
    center_x = max_width // 2
    center_y = max_height // 2
    scale = min(max_width, max_height) // 4
    
    # Draw the colored header (similar to spectrum display)
    freq_text = f"req: {center_freq/1e6:.6f} MHz"
    bw_text = f"andwidth: {bandwidth/1e6:.2f} MHz"
    gain_text = f"ain: {gain}"
    samples_text = f"amples: {2**SAMPLES}"
    step_text = f"ep: {step/1e6:.3f} MHz"
    
    x_pos = 0
    stdscr.addstr(0, x_pos, "F", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, freq_text, curses.color_pair(2) )
    x_pos += len(freq_text) + 3
    stdscr.addstr(0, x_pos, "B", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, bw_text, curses.color_pair(2))
    x_pos += len(bw_text) + 3
    stdscr.addstr(0, x_pos, "G", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, x_pos+1, gain_text, curses.color_pair(2))
    x_pos = 0
    stdscr.addstr(1, x_pos, "S", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+1, samples_text, curses.color_pair(2))
    x_pos += len(samples_text) + 3
    stdscr.addstr(1, x_pos, "S", curses.color_pair(2))
    stdscr.addstr(1, x_pos+1, "t", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+2, step_text, curses.color_pair(2))
    x_pos += len(step_text) + 4
    stdscr.addstr(1, x_pos, "H", curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(1, x_pos+1, "elp", curses.color_pair(2))
    
    # Draw axes
    for i in range(max_width):
        try:
            stdscr.addstr(center_y, i, '─')
        except curses.error:
            pass
    for i in range(max_height):
        try:
            stdscr.addstr(i, center_x, '│')
        except curses.error:
            pass
    
    # Plot I/Q samples
    for i, q in zip(np.real(samples), np.imag(samples)):
        x = int(center_x + i * scale)
        y = int(center_y - q * scale)
        
        if 0 <= x < max_width and 0 <= y < max_height:
            try:
                stdscr.addstr(y, x, '•', curses.color_pair(1))
            except curses.error:
                pass

def main(stdscr):
    global SCAN_ACTIVE, AGC_ENABLED, last_agc_update, SAMPLES, WATERFALL_MODE, CURRENT_DEMOD, current_display_mode
    init_colors()
    gainindex = -1
    
    # Initialize display mode
    current_display_mode = 'SPECTRUM'
    
    # Get screen dimensions
    max_height, max_width = stdscr.getmaxyx()
    
    # Add audio state variable
    audio_enabled = False
    stream = None

    # Add new variables for audio recording
    audio_recording = False
    wav_file = None
    recording_start_time = None

    # Initialize SDR
    sdr = RtlSdr()

    try:
        # Load saved settings if available
        settings = load_settings()
        sdr.sample_rate = settings['sample_rate']
        sdr.center_freq = settings['frequency']
        
        # Handle gain setting properly
        if settings['gain'] == 'auto':
            sdr.gain = 'auto'
            gainindex = -1
        else:
            try:
                gain_value = float(settings['gain'])
                # Find the closest valid gain value
                valid_gains = sdr.valid_gains_db
                gainindex = min(range(len(valid_gains)), 
                              key=lambda i: abs(valid_gains[i] - gain_value))
                sdr.gain = valid_gains[gainindex]
            except (ValueError, TypeError):
                # If there's any error, default to auto gain
                sdr.gain = 'auto'
                gainindex = -1
        
        bandwidth = settings['bandwidth']
        freq_step = settings['freq_step']
        SAMPLES = settings['samples']
        AGC_ENABLED = settings['agc_enabled']
        
        # Enable non-blocking input
        stdscr.nodelay(True)

        while True:
            current_time = time.time()
            
            # Read samples and compute FFT
            samples = sdr.read_samples((2**SAMPLES) * 256)

            # Handle AGC if enabled
            if AGC_ENABLED and (current_time - last_agc_update) >= AGC_UPDATE_INTERVAL:
                current_power = measure_signal_power(samples)
                gainindex = adjust_gain(sdr, current_power, gainindex)
                last_agc_update = current_time

            # Update screen dimensions in case terminal was resized
            max_height, max_width = stdscr.getmaxyx()
            
            # Update audio processing logic
            if AUDIO_AVAILABLE and audio_enabled:
                audio = demodulate_signal(samples, sdr.sample_rate, CURRENT_DEMOD)
                audio_buffer.append(audio)

            # Calculate frequency bins
            num_bins = 1024  # Reduced from 2048
            freq_bins = np.fft.fftshift(np.fft.fftfreq(num_bins, d=1/sdr.sample_rate)) + sdr.center_freq

            # Compute FFT
            fft_data = np.fft.fftshift(np.fft.fft(samples[:num_bins], num_bins))
            power_spectrum = 10 * np.log10(np.abs(fft_data)**2)

            # Update the draw_spectrogram call to include recording status
            recording_duration = time.time() - recording_start_time if audio_recording else None
            if current_display_mode == 'SPECTRUM':
                draw_spectrogram(stdscr, power_spectrum, freq_bins, sdr.center_freq, 
                               bandwidth, sdr.gain, freq_step, 
                               audio_recording, recording_duration)
            elif current_display_mode == 'WATERFALL':
                draw_waterfall(stdscr, power_spectrum, freq_bins, sdr.center_freq, 
                             bandwidth, sdr.gain, freq_step, 
                             audio_recording, recording_duration)
            elif current_display_mode == 'PERSISTENCE':
                draw_persistence(stdscr, power_spectrum, freq_bins, sdr.center_freq,
                               bandwidth, sdr.gain, freq_step)
            elif current_display_mode == 'SURFACE':
                draw_surface_plot(stdscr, power_spectrum, freq_bins, sdr.center_freq,
                                bandwidth, sdr.gain, freq_step)
            elif current_display_mode == 'GRADIENT':
                draw_gradient_waterfall(stdscr, power_spectrum, freq_bins, sdr.center_freq,
                                     bandwidth, sdr.gain, freq_step)
            elif current_display_mode == 'VECTOR':
                draw_vector_display(stdscr, samples, sdr.center_freq,
                                 bandwidth, sdr.gain, freq_step)


            # Handle user input
            key = stdscr.getch()
            if key == ord('q'):  # Quit
                break
            elif key == curses.KEY_UP:  # Increase frequency by 1 MHz
                sdr.center_freq += 1e6
            elif key == curses.KEY_DOWN:  # Decrease frequency by 1 MHz
                sdr.center_freq = max(0, sdr.center_freq - 1e6)
            elif key == curses.KEY_RIGHT:  # Increase frequency by 0.5 MHz
                sdr.center_freq += 0.5e6
            elif key == curses.KEY_LEFT:  # Decrease frequency by 0.5 MHz
                sdr.center_freq = max(0, sdr.center_freq - 0.5e6)
            elif key == ord('x'):  # Set Frequency
                freq = setfreq(stdscr)
                if freq[-1] in 'mM  ':
                    freq = float(freq[:-1]) * 1e6
                elif freq[-1] in 'kK':
                    freq = float(freq[:-1]) * 1e3
                sdr.center_freq = int(freq)
            elif key == ord('t'):  # Decrease step
                freq_step = max(0.01e6, freq_step - 0.01e6)
            elif key == ord('T'):  # Increase step
                freq_step = min(sdr.sample_rate / 2, freq_step + 0.01e6)
            elif key == ord('h'):  # Help
                showhelp(stdscr)
            elif key == ord('b'):  # Zoom in (reduce bandwidth)
                bandwidth = max(0.1e6, bandwidth - zoom_step)
            elif key == ord('B'):  # Zoom out (increase bandwidth)
                bandwidth = min(sdr.sample_rate, bandwidth + zoom_step)
            elif key == ord('f'):  # Shift center frequency down
                sdr.center_freq = max(0, sdr.center_freq - freq_step)
            elif key == ord('F'):  # Shift center frequency up
                sdr.center_freq += freq_step
            elif key == ord('s'):  # Decrease samples
                SAMPLES -= 1
                if SAMPLES < 5:
                    SAMPLES = 5
            elif key == ord('S'):  # Increase samples
                SAMPLES += 1
                if SAMPLES > 12:
                    SAMPLES = 12
            elif key == ord('G'):
                gainindex +=1
                if gainindex <= len(sdr.valid_gains_db)-1:
                    sdr.gain = sdr.valid_gains_db[gainindex]
                else:
                    sdr.gain = "auto"
                    gainindex = -1
            elif key == ord('g'):
                gainindex -= 1
                if gainindex < 0:
                    sdr.gain = sdr.valid_gains_db[0]
                    gainindex = 0
                else:
                    sdr.gain = sdr.valid_gains_db[gainindex]
            elif key == ord('k'):  # Save bookmark
                add_bookmark(stdscr, sdr.center_freq)
            elif key == ord('l'):  # Load bookmark
                new_freq = show_bookmarks(stdscr)
                if new_freq is not None:
                    sdr.center_freq = new_freq
            elif key == ord('a'):  # Toggle audio
                if AUDIO_AVAILABLE:
                    audio_enabled = not audio_enabled
                    if audio_enabled and stream is None:
                        stream = sd.OutputStream(
                            channels=1,
                            samplerate=44100,
                            callback=audio_callback,
                            blocksize=2048,
                            latency=0.1,
                            dtype=np.float32,
                            prime_output_buffers_using_stream_callback=True
                        )
                        stream.start()
                    elif not audio_enabled and stream is not None:
                        stream.stop()
                        stream.close()
                        stream = None
                        audio_buffer.clear()
            elif key == ord('R'):  # Start/Stop recording
                if not audio_recording and AUDIO_AVAILABLE and audio_enabled:
                    # Start recording
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    filename = f"sdr_recording_{timestamp}.wav"
                    wav_file = start_audio_recording(filename)
                    audio_recording = True
                    recording_start_time = time.time()
                    stdscr.addstr(max_height-1, 0, f"Started recording to {filename}", 
                                curses.color_pair(4))
                elif audio_recording:
                    # Stop recording
                    stop_audio_recording(wav_file)
                    audio_recording = False
                    wav_file = None
                    stdscr.addstr(max_height-1, 0, "Recording stopped", 
                                curses.color_pair(4))
                else:
                    stdscr.addstr(max_height-1, 0, 
                                "Audio must be enabled to record (press 'a' first)", 
                                curses.color_pair(3))
                stdscr.refresh()
            elif key == ord('w'):  # Save settings
                save_settings(sdr, bandwidth, freq_step, SAMPLES, AGC_ENABLED)
                stdscr.addstr(max_height-1, 0, "Settings saved", curses.color_pair(4))
                stdscr.refresh()
                time.sleep(1)  # Show message briefly
            elif key == ord('v'):  # Toggle waterfall mode
                WATERFALL_MODE = not WATERFALL_MODE
                WATERFALL_HISTORY.clear()  # Clear history when switching modes
                stdscr.clear()
            elif key == ord('r'):  # Load settings
                settings = load_settings()
                sdr.sample_rate = settings['sample_rate']
                sdr.center_freq = settings['frequency']
                sdr.gain = settings['gain']
                bandwidth = settings['bandwidth']
                freq_step = settings['freq_step']
                SAMPLES = settings['samples']
                AGC_ENABLED = settings['agc_enabled']
                stdscr.addstr(max_height-1, 0, "Settings loaded", curses.color_pair(4))
                stdscr.refresh()
                time.sleep(1)  # Show message briefly
            elif key == ord('A'):  # Toggle AGC
                AGC_ENABLED = not AGC_ENABLED
                if not AGC_ENABLED:
                    # Reset to manual gain mode
                    if gainindex >= 0 and gainindex < len(sdr.valid_gains_db):
                        sdr.gain = sdr.valid_gains_db[gainindex]
                    else:
                        sdr.gain = 'auto'
                        gainindex = -1
            elif key == ord('p'):  # Band presets
                new_freq, new_bandwidth = show_band_presets(stdscr)
                if new_freq is not None:
                    sdr.center_freq = new_freq
                    bandwidth = new_bandwidth
                    # Adjust gain for the new frequency range
                    if AGC_ENABLED:
                        # Force an immediate AGC update
                        last_agc_update = 0
                    stdscr.addstr(max_height-1, 0, f"Switched to band: {new_freq/1e6:.3f} MHz", 
                                curses.color_pair(4))
                    stdscr.refresh()
                    time.sleep(1)
            elif key == ord('c'):  # Start scanner
                start_freq, end_freq, threshold = show_scanner_menu(stdscr)
                if start_freq is not None and end_freq is not None and threshold is not None:
                    # Store current settings
                    old_freq = sdr.center_freq
                    old_gain = sdr.gain
                    new_freq = None
                    
                    # Configure for scanning
                    if AGC_ENABLED:
                        sdr.gain = 'auto'
                    
                    SCAN_ACTIVE = True
                    
                    try:
                        signals = []
                        current_freq = start_freq
                        while current_freq <= end_freq and SCAN_ACTIVE:
                            # Update progress at top of screen
                            draw_scanning_status(stdscr, current_freq, start_freq, end_freq)
                            
                            # Check for cancel key
                            if stdscr.getch() == ord('q'):
                                SCAN_ACTIVE = False
                                break
                            
                            # Scan chunk with user-defined threshold
                            chunk_end = min(current_freq + sdr.sample_rate/2, end_freq)
                            new_signals = scan_frequencies(sdr, current_freq, chunk_end, threshold)
                            signals.extend(new_signals)
                            current_freq = chunk_end + SCAN_STEP
                        
                        # Show results if not cancelled
                        if SCAN_ACTIVE:
                            # Sort signals by power
                            signals.sort(key=lambda x: x['power'], reverse=True)
                            new_freq = display_scan_results(stdscr, signals, threshold)
                            if new_freq is not None:
                                sdr.center_freq = new_freq
                    
                    finally:
                        # Restore settings
                        SCAN_ACTIVE = False
                        sdr.gain = old_gain
                        if new_freq is None:
                            sdr.center_freq = old_freq
            elif key == ord('d'):  # Change demodulation mode
                new_mode = show_demod_menu(stdscr)
                if new_mode is not None:
                    CURRENT_DEMOD = new_mode
                    # Update bandwidth based on mode
                    if DEMOD_MODES[CURRENT_DEMOD]['bandwidth']:
                        bandwidth = DEMOD_MODES[CURRENT_DEMOD]['bandwidth']
                    stdscr.addstr(max_height-1, 0, 
                                f"Switched to {DEMOD_MODES[CURRENT_DEMOD]['name']} mode", 
                                curses.color_pair(4))
                    stdscr.refresh()
                    time.sleep(1)
            elif key == ord('m'):  # Mode switch
                current_mode_index = DISPLAY_MODES.index(current_display_mode)
                current_display_mode = DISPLAY_MODES[(current_mode_index + 1) % len(DISPLAY_MODES)]
                stdscr.clear()
            elif key == ord('1'):  # Spectrum Mode switch
                current_mode_index = 0
                current_display_mode = DISPLAY_MODES[0]
                stdscr.clear()
            elif key == ord('2'):  # Waterfall Mode switch
                current_mode_index = 1
                current_display_mode = DISPLAY_MODES[1]
                stdscr.clear()
            elif key == ord('3'):  # Persistence Mode switch
                current_mode_index = 2
                current_display_mode = DISPLAY_MODES[2]
                stdscr.clear()
            elif key == ord('4'):  # Surface Mode switch
                current_mode_index = 3
                current_display_mode = DISPLAY_MODES[3]
                stdscr.clear()
            elif key == ord('5'):  # Gradient Mode switch
                current_mode_index = 4
                current_display_mode = DISPLAY_MODES[4]
                stdscr.clear()
            elif key == ord('6'):  # Vector Mode switch
                current_mode_index = 5
                current_display_mode = DISPLAY_MODES[5]
                stdscr.clear()

            # Remove the separate recording duration display since it's now handled in draw_spectrogram
            if audio_recording and AUDIO_AVAILABLE and audio_enabled:
                if len(audio_buffer) > 0:
                    audio_data = np.concatenate(list(audio_buffer))
                    write_audio_samples(wav_file, audio_data)
                    audio_buffer.clear()

    except KeyboardInterrupt:
        pass
    finally:
        sdr.close()
        if stream:
            stream.stop()
            stream.close()

        # Make sure to close the WAV file if we exit while recording
        if wav_file:
            stop_audio_recording(wav_file)

if __name__ == "__main__":
    curses.wrapper(main)
