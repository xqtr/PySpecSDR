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
    
    2024/11/18 // Initial Release
    2024/11/22 // Ver 1.0.1
      + Added PPM function
      ! Fixed: All characters are lower ASCII
      + Added more band presets
      ! Fixed: All visual modes have frequency labels and the same look
      + Added scrolling capability in the Help screen 
      + Added pagination to scan results
      + Pressing the C key, the last scan results will re-appear
      + Added pagination to Bookmarks page
      + Added the ability to delete a bookmark. To edit one, just re-insert
        a bookmark with the same description
      ! Fixed/Improved signal detection (hopefully)   
      
    
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
import SoapySDR
from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32

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
    'FM': (87.5e6, 108e6, 'FM Broadcast Radio'),
    'AIR': (108e6, 137e6, 'Aircraft Band'),
    'NOAA': (137e6, 138e6, 'Weather Satellites'),
    'MARINE': (156e6, 162e6, 'Marine VHF'),
    'POLICE': (162e6, 174e6, 'Police/Emergency'),
    'DAB': (174e6, 240e6, 'Digital Audio Broadcasting'),
    'ISM433': (433.05e6, 434.79e6, '433MHz ISM Band'),
    'HAM70': (420e6, 450e6, '70cm Amateur Band'),
    'TELE': (470e6, 862e6, 'TV Broadcasting'),
    'GSM900': (880e6, 960e6, 'GSM 900 Band'),
    'ADS-B': (1090e6, 1091e6, 'Aircraft Tracking'),
    'HAM23': (1240e6, 1300e6, '23cm Amateur Band'),
    'GPS': (1575.42e6, 1576.42e6, 'GPS L1'),
    'INMAR': (1525e6, 1559e6, 'Inmarsat'),
    'RADIO': (1452e6, 1492e6, 'Digital Radio'),
    'GSM1800': (1710e6, 1880e6, 'GSM 1800 Band'),
    'LTE': (1920e6, 2170e6, '3G/4G Mobile'),
    'WIFI': (2400e6, 2500e6, 'WiFi/Bluetooth'),
    'SAT': (2500e6, 2700e6, 'Satellite Services'),
    'ISM5G': (5725e6, 5875e6, '5.8GHz ISM Band')
}

# Optional: Add specific bandwidth recommendations for certain bands
BAND_BANDWIDTHS = {
    'FM': 200e3,      # FM broadcast channels are ~200kHz wide
    'NOAA': 40e3,     # NOAA APT signals are ~40kHz wide
    'ISM433': 100e3,  # Common bandwidth for 433MHz devices
    'ADS-B': 2e6,     # ADS-B requires wider bandwidth
    'GPS': 2e6,       # GPS signals need wider bandwidth
    'WIFI': 20e6      # WiFi channels are typically 20MHz wide
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

# Add near the top with other constants
DEFAULT_PPM = 0  # Default PPM correction value

# Add near the top with other global variables
LAST_SCAN_RESULTS = []  # Store the last scan results

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
    """Display help information with scrolling capability"""
    max_height, max_width = stdscr.getmaxyx()
    
    # Define help content with categories
    help_content = [
        ("General Controls", [
            ("q", "Quit program"),
            ("h", "Show this help screen"),
            ("w", "Save current settings"),
            ("m", "Cycle through display modes"),
            ("1-6", "Quick switch display modes"),
        ]),
        ("Frequency Controls", [
            ("F/f", "Change frequency up/down by step"),
            ("Up/Down", "Change frequency by 1 MHz"),
            ("Right/Left", "Change frequency by 0.5 MHz"),
            ("x", "Set exact frequency"),
            ("T/t", "Increase/decrease frequency step"),
        ]),
        ("Signal Controls", [
            ("B/b", "Increase/reduce bandwidth"),
            ("S/s", "Increase/decrease samples"),
            ("G/g", "Increase/decrease gain"),
            ("A", "Toggle Automatic Gain Control (AGC)"),
        ]),
        ("Frequency Correction", [
            ("P/p", "Increase/decrease PPM correction"),
            ("O", "Set exact PPM correction value"),
        ]),
        ("Audio Controls", [
            ("a", "Toggle audio on/off"),
            ("d", "Change demodulation mode"),
            ("R", "Start/Stop audio recording"),
        ]),
        ("Frequency Management", [
            ("k/l", "Save/Load frequency bookmark"),
            ("n", "Access band presets"),
            ("c", "Start frequency scanner"),
            ("C", "Show scan results"),
        ]),
    ]

    # Calculate total content height
    total_height = sum(2 + len(section[1]) for section in help_content) + 15
    # Initialize scroll position
    scroll_pos = 0
    max_scroll = max(0, total_height - (max_height - 2))
    
    stdscr.nodelay(0)
    
    while True:
        # Clear screen
        stdscr.clear()
        current_line = 0
        
        # Draw title
        title = "PySpecSDR Help"
        stdscr.addstr(0, 2, title, curses.color_pair(1) | curses.A_BOLD)
        current_line += 1
        
        # Draw horizontal line
        stdscr.addstr(1, 1, "-" * (max_width - 2), curses.color_pair(2))
        current_line += 1
        
        # Draw visible content
        visible_line = 0
        startline = 2
        for section_title, commands in help_content:
            if current_line - scroll_pos >= 0 and current_line - scroll_pos < max_height - 3:
                try:
                    stdscr.addstr(startline + current_line - scroll_pos, 2, 
                                "+" + "-" * (len(section_title) + 2) + "+", 
                                curses.color_pair(4))
                except curses.error:
                    pass
            current_line += 1
            
            if current_line - scroll_pos >= 0 and current_line - scroll_pos < max_height - 3:
                try:
                    stdscr.addstr(startline + current_line - scroll_pos, 2, 
                                "| " + section_title + " |", 
                                curses.color_pair(4) | curses.A_BOLD)
                except curses.error:
                    pass
            current_line += 1
            
            if current_line - scroll_pos >= 0 and current_line - scroll_pos < max_height - 3:
                try:
                    stdscr.addstr(startline + current_line - scroll_pos, 2, 
                                "+" + "-" * (len(section_title) + 2) + "+", 
                                curses.color_pair(4))
                except curses.error:
                    pass
            current_line += 1
            
            for key, description in commands:
                if current_line - scroll_pos >= 0 and current_line - scroll_pos < max_height - 3:
                    try:
                        key_str = f"[ {key:6} ]"
                        stdscr.addstr(startline + current_line - scroll_pos, 4, key_str, 
                                    curses.color_pair(1) | curses.A_BOLD)
                        stdscr.addstr(startline + current_line - scroll_pos, 15, "->", 
                                    curses.color_pair(2))
                        stdscr.addstr(startline + current_line - scroll_pos, 18, description, 
                                    curses.color_pair(2))
                    except curses.error:
                        pass
                current_line += 1
            current_line += 1

        # Draw scrollbar
        if total_height > max_height - 2:
            for y in range(2, max_height - 1):
                pos = int((y - 2) * total_height / (max_height - 3))
        if pos >= scroll_pos and pos <= scroll_pos + max_height:
            char = "#"
        else:
            char = "|"
        try:
            stdscr.addstr(y, max_width - 1, char, curses.color_pair(2))
        except curses.error:
            pass

        # Draw navigation instructions
        nav_text = "[ UP/DOWN | PgUp/PgDn | q:Exit ]"
        nav_pos = (max_width - len(nav_text)) // 2
        try:
            stdscr.addstr(max_height - 1, nav_pos, nav_text, 
                         curses.color_pair(5) | curses.A_BOLD)
        except curses.error:
            pass

        stdscr.refresh()
        
        # Handle input
        key = stdscr.getch()
        if key == ord('q'):
            break
        elif key == curses.KEY_UP and scroll_pos > 0:
            scroll_pos = max(0, scroll_pos - 1)
        elif key == curses.KEY_DOWN and scroll_pos < max_scroll:
            scroll_pos = min(max_scroll, scroll_pos + 1)
        elif key == curses.KEY_PPAGE:  # Page Up
            scroll_pos = max(0, scroll_pos - (max_height - 3))
        elif key == curses.KEY_NPAGE:  # Page Down
            scroll_pos = min(max_scroll, scroll_pos + (max_height - 3))
    
    # Restore original nodelay state
    stdscr.nodelay(True)

def setfreq(stdscr):
    draw_clearheader(stdscr)
    stdscr.addstr(0,0,"Enter frequency in Hz: ",curses.color_pair(1) | curses.A_BOLD)
    # Enable echo and cursor
    curses.echo()
    curses.curs_set(1)
    stdscr.nodelay(False) 
    freq = stdscr.getstr()
    draw_clearheader(stdscr)
    # Disable echo and cursor after input
    curses.noecho()
    curses.curs_set(0)
    stdscr.nodelay(True)
    return freq.decode('utf-8')  # Convert bytes to string


def draw_clearheader(stdscr):
    max_height, max_width = stdscr.getmaxyx()
    stdscr.addstr(0, 0, " "*(max_width-1))
    stdscr.addstr(1, 0, " "*(max_width-1))
    
def draw_header(stdscr, freq_data, frequencies, center_freq, bandwidth, gain, step, 
                    sdr, is_recording=False, recording_duration=None):
    
    max_height, max_width = stdscr.getmaxyx()

    x_pos = 0
    if is_recording:
        recording_text = f"Recording: {recording_duration:.1f}s"
        stdscr.addstr(0, max_width - len(recording_text) - 1, recording_text, 
                     curses.color_pair(3) | curses.A_BOLD)
        available_width = max_width - len(recording_text) - 2
    else:
        available_width = max_width
    
    # Draw the colored header
    freq_text = f"req: {center_freq/1e6:.6f} MHz"
    bw_text = f"andwidth: {bandwidth/1e6:.2f} MHz"
    gain_text = f"ain: {gain}"
    samples_text = f"amples: {2**SAMPLES}"
    step_text = f"ep: {step/1e6:.3f} MHz"
    ppm_text = f"PM: {sdr.ppm}"  # Add PPM text
    
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
    try:
        stdscr.addstr(1, x_pos, "P", curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(1, x_pos+1, ppm_text, curses.color_pair(2))
    except curses.error:
        pass  # Ignore if screen is too small
    #x_pos += len(ppm_text) + 3
    #stdscr.addstr(1, x_pos, "H", curses.color_pair(1) | curses.A_BOLD)
    #stdscr.addstr(1, x_pos+1, "elp", curses.color_pair(2))
    
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

def draw_spectrogram(stdscr, freq_data, frequencies, center_freq, bandwidth, gain, step, 
                    sdr, is_recording=False, recording_duration=None):
    """Draw the spectrum display with improved signal-to-noise ratio visualization"""
    max_height, max_width = stdscr.getmaxyx()
    
    # Calculate display dimensions
    display_width = max_width - 10  # Reserve space for dB scale
    display_height = max_height - 4  # Reserve space for header and labels
    
    # Clear the display area (preserve header)
    for y in range(2, max_height-1):
        try:
            stdscr.addstr(y, 0, " " * (max_width-1), curses.color_pair(1))
        except curses.error:
            pass
    
    # Set fixed dB range for display with noise floor adjustment
    min_db = np.min(freq_data[np.isfinite(freq_data)])
    max_db = np.max(freq_data[np.isfinite(freq_data)])
    
    # Calculate noise floor (using lower percentile)
    noise_floor = np.percentile(freq_data[np.isfinite(freq_data)], 20)
    
    # Adjust dynamic range to emphasize signals above noise
    db_range = max_db - noise_floor
    display_min = noise_floor - (db_range * 0.1)  # Show some noise below floor
    display_max = max_db + (db_range * 0.05)  # Add headroom
    
    # Draw dB scale on the left
    for i in range(display_height):
        db_value = display_max - (i * (display_max - display_min) / display_height)
        if i % 3 == 0:  # Show scale every 3 lines
            db_label = f"{db_value:4.0f}dB"
            try:
                stdscr.addstr(i + 2, 0, db_label, curses.color_pair(2))
                # Add scale markers
                stdscr.addstr(i + 2, 8, "|", curses.color_pair(2))
            except curses.error:
                pass

    # Normalize data for display using adjusted range
    normalized_data = np.clip((freq_data - display_min) / (display_max - display_min), 0, 1)
    
    # Apply non-linear scaling to emphasize signals
    normalized_data = np.power(normalized_data, 0.7)  # Adjust exponent to taste
    
    # Resample data to fit display width
    resampled = np.interp(
        np.linspace(0, len(normalized_data) - 1, display_width),
        np.arange(len(normalized_data)),
        normalized_data
    )
    
    # Draw spectrum with improved character selection
    for x, value in enumerate(resampled):
        if np.isfinite(value):
            # Calculate height in display units
            height = int(value * display_height)
            height = min(height, display_height)
            
            # First clear the entire column
            for y in range(display_height):
                try:
                    stdscr.addstr(y + 2, x + 9, " ", curses.color_pair(1))
                except curses.error:
                    pass
            
            # Then draw the bar with varied characters based on signal strength
            for y in range(display_height - height, display_height):
                try:
                    # Calculate relative position in the bar
                    rel_pos = (y - (display_height - height)) / height if height > 0 else 0
                    
                    # Select character based on signal strength and position
                    if value > 0.8:  # Strong signals
                        char = "#" if rel_pos > 0.5 else "="
                    elif value > 0.4:  # Medium signals
                        char = "=" if rel_pos > 0.5 else "-"
                    elif value > 0.2:  # Weak signals
                        char = "-" if rel_pos > 0.5 else "."
                    else:  # Noise level
                        char = "." if rel_pos > 0.7 else " "
                    
                    stdscr.addstr(y + 2, x + 9, char, curses.color_pair(1))
                except curses.error:
                    pass

    # Use standardized frequency labels
    draw_frequency_labels(stdscr, center_freq, bandwidth, display_height, display_width)

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
    draw_clearheader(stdscr)
    stdscr.addstr(0, 0, "Enter bookmark name: ", curses.color_pair(1) | curses.A_BOLD)
    curses.echo()
    curses.curs_set(1)
    stdscr.nodelay(False)
    name = stdscr.getstr().decode('utf-8')
    draw_clearheader(stdscr)
    curses.noecho()
    curses.curs_set(0)
    stdscr.nodelay(True)
    if name:
        save_bookmark(name, freq)

def show_bookmarks(stdscr):
    """Display bookmarks with pagination and deletion capability"""
    bookmarks = load_bookmarks()
    if not bookmarks:
        show_popup_msg(stdscr, "No bookmarks found!", error=True)
        return None
    
    # Initialize pagination variables
    max_height, max_width = stdscr.getmaxyx()
    items_per_page = max_height - 7  # Reserve space for header and footer
    total_items = len(bookmarks)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    current_page = 0
    
    while True:
        stdscr.clear()
        
        # Draw header
        header = "Bookmarks"
        stdscr.addstr(0, 2, header, curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(1, 2, "-" * len(header), curses.color_pair(2))
        
        # Calculate slice for current page
        start_idx = current_page * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        current_items = list(bookmarks.items())[start_idx:end_idx]
        
        # Display bookmarks for current page
        for i, (name, freq) in enumerate(current_items, 1):
            abs_index = start_idx + i
            line = f"{abs_index:2d}. {name:<20}: {freq/1e6:.3f} MHz"
            try:
                stdscr.addstr(i + 2, 2, line, curses.color_pair(2))
            except curses.error:
                pass
        
        # Draw footer with navigation help
        footer = f"Page {current_page + 1}/{total_pages} | [n]ext/[p]rev page | [d]elete | [q]uit | Enter number to select"
        try:
            stdscr.addstr(max_height-2, 2, footer, curses.color_pair(5))
            stdscr.addstr(max_height-1, 2, "Choice: ", curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass
        
        # Handle input
        curses.echo()
        curses.curs_set(1)
        stdscr.nodelay(False)
        
        try:
            choice = stdscr.getstr().decode('utf-8').lower()
            
            if choice == 'q':
                break
            elif choice == 'n' and current_page < total_pages - 1:
                current_page += 1
                continue
            elif choice == 'p' and current_page > 0:
                current_page -= 1
                continue
            elif choice == 'd':
                # Handle bookmark deletion
                stdscr.addstr(max_height-1, 2, "Enter number to delete: ", 
                            curses.color_pair(3) | curses.A_BOLD)
                try:
                    del_choice = int(stdscr.getstr().decode('utf-8'))
                    if 1 <= del_choice <= total_items:
                        # Get bookmark name and delete it
                        del_name = list(bookmarks.keys())[del_choice - 1]
                        del bookmarks[del_name]
                        # Save updated bookmarks
                        with open(BOOKMARK_FILE, 'w') as f:
                            json.dump(bookmarks, f, indent=2)
                        # Update pagination variables
                        total_items = len(bookmarks)
                        total_pages = (total_items + items_per_page - 1) // items_per_page
                        current_page = min(current_page, total_pages - 1)
                        show_popup_msg(stdscr, f"Deleted bookmark: {del_name}")
                        if not bookmarks:
                            return None
                except ValueError:
                    show_popup_msg(stdscr, "Invalid selection!", error=True)
            else:
                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= total_items:
                        return list(bookmarks.values())[choice_num - 1]
                except ValueError:
                    show_popup_msg(stdscr, "Invalid selection!", error=True)
                    
        except curses.error:
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
        'current_band': str(current_band) if current_band else '',
        'ppm': str(sdr.ppm)  # Add PPM to saved settings
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
        'current_band': '',
        'ppm': '0'  # Add default PPM value
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
                'current_band': config['SDR'].get('current_band', default_settings['current_band']),
                'ppm': int(config['SDR'].get('ppm', default_settings['ppm']))
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
        'current_band': default_settings['current_band'],
        'ppm': int(default_settings['ppm'])
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

def show_popup_msg(stdscr,msg,error=False):
    draw_clearheader(stdscr)
    if error:
        stdscr.addstr(0, 0, msg, curses.color_pair(3))
    else:
        stdscr.addstr(0, 0, msg, curses.color_pair(4))
    stdscr.refresh()
    time.sleep(2)
    draw_clearheader(stdscr)

def show_band_presets(stdscr):
    """Display and select from available band presets with scrolling support"""
    max_height, max_width = stdscr.getmaxyx()
    available_height = max_height - 6  # Reserve space for header and footer
    
    # Calculate total entries and pages
    total_entries = len(BAND_PRESETS)
    entries_per_page = available_height
    total_pages = (total_entries + entries_per_page - 1) // entries_per_page
    current_page = 0
    
    while True:
        stdscr.clear()
        
        # Draw header
        header = "Available Band Presets"
        stdscr.addstr(0, 2, header, curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(1, 2, "-" * len(header), curses.color_pair(2))
        
        # Calculate slice for current page
        start_idx = current_page * entries_per_page
        end_idx = min(start_idx + entries_per_page, total_entries)
        
        # Display current page of presets
        current_items = list(BAND_PRESETS.items())[start_idx:end_idx]
        for i, (key, (start, end, description)) in enumerate(current_items, 1):
            # Calculate absolute index for selection
            abs_index = start_idx + i
            # Add recommended bandwidth to display if available
            if key in BAND_BANDWIDTHS:
                bw_info = f" (BW: {BAND_BANDWIDTHS[key]/1e3:.0f}kHz)"
            else:
                bw_info = ""
            line = f"{abs_index:2d}. {key:<8} : {description:<25}{bw_info} ({start/1e6:.3f}-{end/1e6:.3f} MHz)"
            try:
                stdscr.addstr(i + 2, 2, line, curses.color_pair(2))
            except curses.error:
                pass
        
        # Draw footer with navigation help
        footer = f"Page {current_page + 1}/{total_pages} | [n]ext/[p]rev page | [q]uit | Enter number to select"
        try:
            stdscr.addstr(max_height-2, 2, footer, curses.color_pair(5))
            stdscr.addstr(max_height-1, 2, "Choice: ", curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass
        
        # Handle input
        curses.echo()
        curses.curs_set(1)
        stdscr.nodelay(False)
        
        try:
            choice = stdscr.getstr().decode('utf-8').lower()
            
            if choice == 'q':
                break
            elif choice == 'n' and current_page < total_pages - 1:
                current_page += 1
                continue
            elif choice == 'p' and current_page > 0:
                current_page -= 1
                continue
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= total_entries:
                    # Get selected band
                    band_key = list(BAND_PRESETS.keys())[choice_num - 1]
                    start, end, _ = BAND_PRESETS[band_key]
                    # Use recommended bandwidth if available, otherwise calculate
                    if band_key in BAND_BANDWIDTHS:
                        bandwidth = BAND_BANDWIDTHS[band_key]
                    else:
                        bandwidth = min(end - start, 2e6)  # Limit bandwidth to 2MHz or band width
                    return start + (end - start)/2, bandwidth
            except ValueError:
                pass
                
        except curses.error:
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
    max_height, max_width = stdscr.getmaxyx()  # Get screen dimensions
    
    # Calculate total steps for progress bar
    total_steps = int((end_freq - start_freq) / step)
    current_step = 0
    
    while current_freq <= end_freq:
        try:
            # Update scanning status display
            draw_scanning_status(stdscr, current_freq, start_freq, end_freq, sdr)
            
            # Check for user interrupt ('q' to quit scanning)
            if stdscr.getch() == ord('q'):
                break
            
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
                    
                    # Show immediate detection
                    status_msg = f"Signal detected at {current_freq/1e6:.3f} MHz ({signal_type})"
                    stdscr.addstr(max_height-1, 0, " " * (max_width-1))  # Clear line
                    stdscr.addstr(max_height-1, 0, status_msg, curses.color_pair(4))
                    stdscr.refresh()
        
        except Exception as e:
            stdscr.addstr(max_height-1, 0, f"Error: {str(e)}", curses.color_pair(3))
            stdscr.refresh()
            time.sleep(0.5)
        
        current_freq += step
        current_step += 1
    
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
    """Display scanner configuration menu with band selection"""
    max_height, max_width = stdscr.getmaxyx()
    available_height = max_height - 6  # Reserve space for header and footer
    
    # Calculate total entries and pages
    total_entries = len(BAND_PRESETS)
    entries_per_page = available_height
    total_pages = (total_entries + entries_per_page - 1) // entries_per_page
    current_page = 0
    
    while True:
        stdscr.clear()
        
        # Draw header
        header = "Scanner Configuration - Select Band to Scan"
        stdscr.addstr(0, 2, header, curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(1, 2, "-" * len(header), curses.color_pair(2))
        
        # Calculate slice for current page
        start_idx = current_page * entries_per_page
        end_idx = min(start_idx + entries_per_page, total_entries)
        
        # Display current page of presets
        current_items = list(BAND_PRESETS.items())[start_idx:end_idx]
        for i, (key, (start, end, description)) in enumerate(current_items, 1):
            # Calculate absolute index for selection
            abs_index = start_idx + i
            line = f"{abs_index:2d}. {key:<8} : {description:<25} ({start/1e6:.3f}-{end/1e6:.3f} MHz)"
            try:
                stdscr.addstr(i + 2, 2, line, curses.color_pair(2))
            except curses.error:
                pass
        
        # Add custom range option
        custom_option = f"{total_entries + 1}. Custom frequency range"
        try:
            stdscr.addstr(end_idx - start_idx + 3, 2, custom_option, curses.color_pair(4))
        except curses.error:
            pass
        
        # Draw footer with navigation help
        footer = f"Page {current_page + 1}/{total_pages} | [n]ext/[p]rev page | [q]uit | Enter number to select"
        try:
            stdscr.addstr(max_height-3, 2, footer, curses.color_pair(5))
            stdscr.addstr(max_height-2, 2, "Choice: ", curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass
        
        # Handle input
        curses.echo()
        curses.curs_set(1)
        stdscr.nodelay(False)
        
        try:
            choice = stdscr.getstr().decode('utf-8').lower()
            
            if choice == 'q':
                return None, None, None
            elif choice == 'n' and current_page < total_pages - 1:
                current_page += 1
                continue
            elif choice == 'p' and current_page > 0:
                current_page -= 1
                continue
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= total_entries:
                    # Get selected band
                    band_key = list(BAND_PRESETS.keys())[choice_num - 1]
                    start, end, _ = BAND_PRESETS[band_key]
                    
                    # Get threshold
                    stdscr.clear()
                    stdscr.addstr(0, 2, "Enter signal strength threshold \n(dB, recommended -40 to -20): ", 
                                curses.color_pair(2))
                    threshold = float(stdscr.getstr().decode('utf-8'))
                    
                    return start, end, threshold
                    
                elif choice_num == total_entries + 1:
                    # Handle custom range
                    stdscr.clear()
                    stdscr.addstr(0, 2, "Enter start frequency (MHz): ", curses.color_pair(2))
                    start = float(stdscr.getstr().decode('utf-8')) * 1e6
                    stdscr.addstr(1, 2, "Enter end frequency (MHz): ", curses.color_pair(2))
                    end = float(stdscr.getstr().decode('utf-8')) * 1e6
                    stdscr.addstr(2, 2, "Enter signal strength threshold \n(dB, recommended -40 to -20): ", 
                                curses.color_pair(2))
                    threshold = float(stdscr.getstr().decode('utf-8'))
                    
                    return start, end, threshold
                    
            except ValueError:
                pass
                
        except curses.error:
            pass
        finally:
            stdscr.nodelay(True)
            curses.noecho()
            curses.curs_set(0)
    
    return None, None, None

def display_scan_results(stdscr, signals, threshold):
    """Display scanner results with pagination and allow selection"""
    # Ensure we're in the right mode for user input
    stdscr.nodelay(False)  # Make sure we wait for input
    curses.echo()          # Show user input
    curses.curs_set(1)     # Show cursor
    
    try:
        if not signals:
            stdscr.addstr(0, 0, "\nNo signals found above threshold.\n", curses.color_pair(3))
            stdscr.addstr(2, 0, "\nPress any key to continue...", curses.color_pair(2))
            stdscr.getch()  # Wait for keypress
            return None
        
        max_height, max_width = stdscr.getmaxyx()
        results_per_page = max_height - 7  # Reserve space for header and footer
        total_pages = (len(signals) + results_per_page - 1) // results_per_page
        current_page = 0
        
        while True:
            stdscr.clear()
            
            # Draw header
            header = f"Detected Signals ({len(signals)} found) - Page {current_page + 1}/{total_pages}"
            stdscr.addstr(0, 0, header, curses.color_pair(1) | curses.A_BOLD)
            stdscr.addstr(1, 0, "-" * len(header), curses.color_pair(2))
            
            # Calculate slice for current page
            start_idx = current_page * results_per_page
            end_idx = min(start_idx + results_per_page, len(signals))
            
            # Display signals for current page
            current_line = 2
            for i, signal in enumerate(signals[start_idx:end_idx], start_idx + 1):
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
                
                stdscr.addstr(current_line, 0, line[:max_width-1], color)
                current_line += 1
            
            # Draw navigation footer
            footer = "Navigation: [n]ext page, [p]revious page, [number] to select, [q]uit"
            stdscr.addstr(max_height-1, 0, footer, curses.color_pair(2))
            stdscr.addstr(max_height-2, 0, "Enter choice: ", curses.color_pair(1) | curses.A_BOLD)
            
            stdscr.refresh()
            
            # Get user input
            try:
                choice = stdscr.getstr().decode('utf-8').lower()
                
                if choice == 'q':
                    break
                elif choice == 'n' and current_page < total_pages - 1:
                    current_page += 1
                elif choice == 'p' and current_page > 0:
                    current_page -= 1
                else:
                    try:
                        choice_num = int(choice)
                        if 1 <= choice_num <= len(signals):
                            return signals[choice_num-1]['frequency']
                    except ValueError:
                        pass
            except curses.error:
                pass
            
    except Exception as e:
        # Debug output for unexpected errors
        stdscr.addstr(max_height-1, 0, f"Display error ({type(e).__name__}): {str(e)}", 
                     curses.color_pair(3))
        stdscr.refresh()
        stdscr.getch()  # Wait for key press to see error
    
    finally:
        # Restore original terminal settings
        stdscr.nodelay(True)
        curses.noecho()
        curses.curs_set(0)
        stdscr.clear()
    
    return None

def draw_scanning_status(stdscr, current_freq, start_freq, end_freq, sdr):
    """Draw scanning progress at the top of the screen"""
    try:
        max_height, max_width = stdscr.getmaxyx()
        
        # Calculate progress percentage
        total_range = end_freq - start_freq
        if total_range > 0:  # Prevent division by zero
            progress = (current_freq - start_freq) / total_range
        else:
            progress = 0
            
        # Calculate progress bar width (70% of screen width)
        bar_width = int(max_width * 0.7)
        filled = int(bar_width * progress)
        
        # Clear the status lines
        stdscr.addstr(0, 0, " " * max_width)
        stdscr.addstr(1, 0, " " * max_width)
        
        # Create the status text
        status_text = f"Scanning: {current_freq/1e6:8.3f} MHz "
        progress_bar = "[" + "=" * filled + " " * (bar_width - filled) + "]"
        percentage = f" {progress * 100:3.0f}%"
        
        # Calculate starting position to center the display
        total_length = len(status_text) + len(progress_bar) + len(percentage)
        start_pos = max(0, (max_width - total_length) // 2)
        
        # Draw the components with colors
        stdscr.addstr(0, start_pos, status_text, curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(1, start_pos, progress_bar, curses.color_pair(2))
        stdscr.addstr(1, start_pos + len(progress_bar), percentage, curses.color_pair(4))
        
        # Force screen update
        stdscr.refresh()
        
    except curses.error:
        pass  # Ignore curses errors

def draw_waterfall(stdscr, freq_data, frequencies, center_freq, bandwidth, gain, step, 
                  sdr, is_recording=False, recording_duration=None):
    """Draw the waterfall display using ASCII characters"""
    global WATERFALL_HISTORY
    max_height, max_width = stdscr.getmaxyx()
    display_width = max_width - 8
    display_height = max_height - 4
    
    # Add current data to history
    WATERFALL_HISTORY.append(freq_data)
    if len(WATERFALL_HISTORY) > WATERFALL_MAX_LINES:
        WATERFALL_HISTORY.pop(0)

    # Normalize all data for consistent coloring
    all_data = np.array(WATERFALL_HISTORY)
    min_val = np.min(all_data[np.isfinite(all_data)])
    max_val = np.max(all_data[np.isfinite(all_data)])
    
    # Draw dB scale on the left
    for i in range(display_height):
        db_value = max_val - (i * (max_val - min_val) / display_height)
        if i % 3 == 0:  # Show scale every 3 lines
            db_label = f"{db_value:4.0f}dB"
            try:
                stdscr.addstr(i + 2, 0, db_label, curses.color_pair(2))
                # Add scale markers
                stdscr.addstr(i + 2, 8, "|", curses.color_pair(2))
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

        # Draw each point in the line using ASCII characters
        for x, value in enumerate(resampled):
            if np.isfinite(value):
                # Normalize value and select ASCII character and color
                norm_value = (value - min_val) / (max_val - min_val)
                color_index = int(norm_value * 5)  # 0-5 for the 6 color pairs
                
                if norm_value > 0.75:
                    char = "#"
                elif norm_value > 0.5:
                    char = "="
                elif norm_value > 0.25:
                    char = "-"
                else:
                    char = "."
                
                try:
                    stdscr.addstr(y + 3, x + 9, char, curses.color_pair(10 + color_index))
                except curses.error:
                    pass

    # Use standardized frequency labels
    draw_frequency_labels(stdscr, center_freq, bandwidth, display_height, display_width)

def draw_frequency_labels(stdscr, center_freq, bandwidth, display_height, display_width, x_offset=9):
    """Standardized function to draw frequency labels and axis using ASCII only"""
    try:
        # Draw horizontal axis background to reflect center frequency
        half_bw = bandwidth / 2
        start_freq = center_freq - half_bw
        end_freq = center_freq + half_bw
        
        # Calculate center marker width proportional to bandwidth
        # For example: 2MHz -> 4 chars, 1MHz -> 2 chars, 0.5MHz -> 1 char
        center_marker_width = max(1, int(bandwidth / 250000))  # 1 char per 500kHz
        center_x = display_width // 2  # Center position in display units
        
        # Draw the axis background with different characters for different frequency ranges
        axis_line = ""
        for x in range(display_width):
            # Use different characters based on position relative to center
            if abs(x - center_x) < center_marker_width:  # Center marker
                axis_line += "="
            else:
                axis_line += "-"  # Same character for both sides
        
        # Draw the axis with background
        stdscr.addstr(display_height + 2, x_offset, axis_line, curses.color_pair(2))
        
        # Calculate frequency steps and format labels
        freq_step = bandwidth / 5
        
        # Draw frequency labels and tick marks
        for i in range(6):
            freq = start_freq + (i * freq_step)
            label = f"{freq/1e6:.2f}MHz"
            pos = int(x_offset + (i * (display_width-1)/5))
            
            try:
                # Draw tick mark
                stdscr.addstr(display_height + 2, pos, "|", curses.color_pair(2))
                
                # Center the label under the tick mark
                label_pos = max(pos - len(label)//2, x_offset)
                stdscr.addstr(display_height + 3, label_pos, label, curses.color_pair(2))
            except curses.error:
                pass

    except curses.error:
        pass

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

def draw_persistence(stdscr, freq_data, frequencies, center_freq, bandwidth, gain, step,
                    sdr, is_recording=False, recording_duration=None):
    """Draw spectrum with persistence effect"""
    global PERSISTENCE_HISTORY
    max_height, max_width = stdscr.getmaxyx()
    display_width = max_width - 8  # Reserve space for dB scale
    display_height = max_height - 4
    
    # Add current data to history
    PERSISTENCE_HISTORY.append(freq_data)
    if len(PERSISTENCE_HISTORY) > PERSISTENCE_LENGTH:
        PERSISTENCE_HISTORY.pop(0)

    # Draw dB scale on the left
    min_val = np.min(freq_data[np.isfinite(freq_data)])
    max_val = np.max(freq_data[np.isfinite(freq_data)])
    db_range = max_val - min_val
    for i in range(max_height - 3):
        db_value = max_val - (i * db_range / (max_height - 3))
        if i % 3 == 0:  # Show scale every 3 lines
            db_label = f"{db_value:4.0f}dB"
            try:
                stdscr.addstr(i + 2, 0, db_label, curses.color_pair(2))
            except curses.error:
                pass

    # Draw each trace with ASCII characters
    for i, historical_data in enumerate(PERSISTENCE_HISTORY):
        alpha = PERSISTENCE_ALPHA ** (PERSISTENCE_LENGTH - i)
        color_pair = int(1 + (5 * (1 - alpha)))
        
        for x in range(display_width):
            try:
                y = int(max_height - 2 - (historical_data[x] / 100 * (max_height - 3)))
                if 2 <= y < max_height - 1:
                    stdscr.addstr(y, x + 8, '*', curses.color_pair(color_pair))
            except curses.error:
                pass
    
    # Use standardized frequency labels
    draw_frequency_labels(stdscr, center_freq, bandwidth, display_height, display_width)

def draw_surface_plot(stdscr, freq_data, frequencies, center_freq, bandwidth, gain, step,
                     sdr, is_recording=False, recording_duration=None):
    """Draw spectrum as pseudo-3D surface with frequency labels"""
    max_height, max_width = stdscr.getmaxyx()
    display_width = max_width - 8
    display_height = max_height - 4
    
    # Calculate frequency range
    half_bw = bandwidth / 2
    start_freq = center_freq - half_bw
    end_freq = center_freq + half_bw
    
    # Draw surface with ASCII characters
    angle_rad = np.radians(SURFACE_ANGLE)
    for x in range(max_width - 10):  # Reserve space for labels
        magnitude = freq_data[x]
        for y in range(int(magnitude)):
            screen_x = int(x - y * np.cos(angle_rad)) + 8  # Offset for labels
            screen_y = int(max_height - 2 - y * np.sin(angle_rad))
            
            if 0 <= screen_x < max_width and 2 <= screen_y < max_height - 1:
                try:
                    stdscr.addstr(screen_y, screen_x, '#', 
                                curses.color_pair(1 + (y % 5)))
                except curses.error:
                    pass
    
    # Use standardized frequency labels
    draw_frequency_labels(stdscr, center_freq, bandwidth, display_height, display_width)
    
    # Draw amplitude scale on the left
    min_val = np.min(freq_data[np.isfinite(freq_data)])
    max_val = np.max(freq_data[np.isfinite(freq_data)])
    db_range = max_val - min_val
    for i in range(max_height - 3):
        db_value = max_val - (i * db_range / (max_height - 3))
        if i % 3 == 0:  # Show scale every 3 lines
            db_label = f"{db_value:4.0f}dB"
            try:
                stdscr.addstr(i + 2, 0, db_label, curses.color_pair(2))
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

def draw_gradient_waterfall(stdscr, freq_data, frequencies, center_freq, bandwidth, gain, step, 
                          sdr, is_recording=False, recording_duration=None):
    """Draw waterfall with ASCII characters for better compatibility"""
    global WATERFALL_HISTORY
    max_height, max_width = stdscr.getmaxyx()
    display_width = max_width - 10
    display_height = max_height - 4
    
    # Add current data to history
    WATERFALL_HISTORY.append(freq_data)
    if len(WATERFALL_HISTORY) > WATERFALL_MAX_LINES:
        WATERFALL_HISTORY.pop(0)

    # Normalize data
    all_data = np.array(WATERFALL_HISTORY)
    min_val = np.min(all_data[np.isfinite(all_data)])
    max_val = np.max(all_data[np.isfinite(all_data)])
    
    # Draw dB scale on the left
    for i in range(display_height):
        db_value = max_val - (i * (max_val - min_val) / display_height)
        if i % 3 == 0:  # Show scale every 3 lines
            db_label = f"{db_value:4.0f}dB"
            try:
                stdscr.addstr(i + 2, 0, db_label, curses.color_pair(2))
                # Add scale markers
                stdscr.addstr(i + 2, 8, "|", curses.color_pair(2))
            except curses.error:
                pass

    # Define ASCII intensity characters (from darkest to brightest)
    intensity_chars = ' ._-=+*#@'  # 9 levels of intensity
    
    # Draw each line with ASCII characters
    for y, line_data in enumerate(reversed(WATERFALL_HISTORY)):
        if y >= display_height:
            break
            
        # Resample data to fit display width
        resampled = np.interp(
            np.linspace(0, len(line_data) - 1, display_width),
            np.arange(len(line_data)),
            line_data
        )
        
        for x, value in enumerate(resampled):
            if np.isfinite(value):
                # Normalize value between 0 and 1
                normalized = (value - min_val) / (max_val - min_val)
                
                # Convert normalized value to character index
                char_index = int(normalized * (len(intensity_chars) - 1))
                char = intensity_chars[char_index]
                
                # Select color based on intensity
                color_index = int(normalized * 5)  # 6 color pairs (0-5)
                
                try:
                    stdscr.addstr(y + 2, x + 9, char, 
                                curses.color_pair(10 + color_index))
                except curses.error:
                    pass

    # Draw intensity scale on the right
    for i in range(display_height):
        normalized = 1 - (i / display_height)
        char_index = int(normalized * (len(intensity_chars) - 1))
        try:
            stdscr.addstr(i + 2, max_width - 2, 
                         intensity_chars[char_index] * 2, 
                         curses.color_pair(10 + int(normalized * 5)))
        except curses.error:
            pass

    # Use standardized frequency labels
    draw_frequency_labels(stdscr, center_freq, bandwidth, display_height, display_width)

def draw_vector_display(stdscr, samples, center_freq, bandwidth, gain, step, sdr, 
                       is_recording=False, recording_duration=None):
    """Draw I/Q samples as vector constellation"""
    max_height, max_width = stdscr.getmaxyx()
    display_width = max_width - 8
    display_height = max_height - 4
    
    # Create coordinate system
    center_x = max_width // 2
    center_y = max_height // 2
    scale = min(max_width, max_height) // 4
    
    # Draw axes with ASCII characters
    for i in range(max_width):
        try:
            stdscr.addstr(center_y, i, '-')
        except curses.error:
            pass
    for i in range(max_height):
        try:
            stdscr.addstr(i, center_x, '|')
        except curses.error:
            pass
    
    # Plot I/Q samples with ASCII dot
    for i, q in zip(np.real(samples), np.imag(samples)):
        x = int(center_x + i * scale)
        y = int(center_y - q * scale)
        
        if 0 <= x < max_width and 0 <= y < max_height:
            try:
                stdscr.addstr(y, x, '.', curses.color_pair(1))
            except curses.error:
                pass

    # Use standardized frequency labels
    draw_frequency_labels(stdscr, center_freq, bandwidth, display_height, display_width)

# Add new class to handle different SDR backends
class SDRDevice:
    def __init__(self, backend='SOAPY', stdscr=None):
        self.backend = backend
        self.device = None
        self.sample_rate = 2.048e6
        self.center_freq = 100e6
        self.gain = 20
        self.bandwidth = 2e6
        self.ppm = DEFAULT_PPM
        self.stdscr = stdscr
        self._valid_gains = None
    
    def enumerate_devices(self):
        """List all available SDR devices"""
        try:
            devices = SoapySDR.Device.enumerate()
            formatted_devices = []
            
            for i, device in enumerate(devices, 1):
                # Extract relevant device information using SoapySDRKwargs methods
                driver = device['driver'] if 'driver' in device else 'Unknown'
                label = device['label'] if 'label' in device else ''
                serial = device['serial'] if 'serial' in device else ''
                
                # Create formatted device string
                device_str = f"{driver}"
                if label:
                    device_str += f" ({label})"
                if serial:
                    device_str += f" [SN: {serial}]"
                
                formatted_devices.append((i, device_str, device))
            
            return formatted_devices
            
        except Exception as e:
            raise RuntimeError(f"Error enumerating devices: {e}")
    
    def select_device(self):
        """Display device selection menu and return chosen device args"""
        try:
            devices = self.enumerate_devices()
            if not devices:
                raise RuntimeError("No SDR devices found")
            
            if len(devices) == 1:
                # If only one device, use it automatically
                self.stdscr.addstr(0, 0, "Found single SDR device, using it automatically...", 
                                 curses.color_pair(4))
                self.stdscr.refresh()
                time.sleep(1)
                return devices[0][2]
            
            # Display device selection menu
            self.stdscr.clear()
            self.stdscr.addstr(0, 0, "Available SDR Devices:", curses.color_pair(1) | curses.A_BOLD)
            self.stdscr.addstr(1, 0, "-" * 50, curses.color_pair(2))
            
            for idx, name, _ in devices:
                self.stdscr.addstr(idx + 1, 0, f"{idx}. {name}", curses.color_pair(2))
            
            self.stdscr.addstr(len(devices) + 3, 0, "Select device (1-{}): ".format(len(devices)), curses.color_pair(1) | curses.A_BOLD)
            
            # Get user input
            curses.echo()
            curses.curs_set(1)
            self.stdscr.nodelay(False)
            
            while True:
                try:
                    choice = int(self.stdscr.getstr().decode('utf-8'))
                    if 1 <= choice <= len(devices):
                        return devices[choice-1][2]
                    else:
                        raise ValueError
                except ValueError:
                    self.stdscr.addstr(len(devices) + 4, 0, "Invalid choice. Try again: ", 
                                     curses.color_pair(3))
                    self.stdscr.refresh()
        
        finally:
            curses.noecho()
            curses.curs_set(0)
            self.stdscr.nodelay(True)
            self.stdscr.clear()
    
    def init_device(self):
        """Initialize SoapySDR device with device selection"""
        try:
            # Get device arguments from selection menu
            args = self.select_device()
            
            # Create device instance with selected device
            self.device = SoapySDR.Device(args)
            
            # Set initial parameters BEFORE creating the stream
            self.set_sample_rate(self.sample_rate)
            self.set_center_freq(self.center_freq)
            self.set_gain(self.gain)
            self.set_bandwidth(self.bandwidth)
            
            # Initialize gain range
            self._valid_gains = self._get_valid_gains()
            
            # Setup RX stream AFTER setting parameters
            self.stream = self.device.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
            self.device.activateStream(self.stream)
                
        except Exception as e:
            raise RuntimeError(f"Error initializing SoapySDR device: {e}")
    
    def _get_valid_gains(self):
        """Get list of valid gain values"""
        try:
            gain_range = self.device.getGainRange(SOAPY_SDR_RX, 0)
            step = gain_range.step() if gain_range.step() > 0 else 1
            return np.arange(gain_range.minimum(), gain_range.maximum() + step, step)
        except Exception:
            return np.arange(0, 50, 1)  # Fallback range
    
    def read_samples(self, num_samples):
        """Read samples from the SDR device"""
        buff = np.array([0]*num_samples, np.complex64)
        ret = self.device.readStream(self.stream, [buff], len(buff))
        if ret.ret < 0:
            raise RuntimeError(f"Stream error: {ret.ret}")
        return buff
    
    def close(self):
        if self.device:
            self.device.deactivateStream(self.stream)
            self.device.closeStream(self.stream)
            self.device = None
    
    @property
    def valid_gains_db(self):
        return self._valid_gains
    
    def set_gain(self, gain):
        """Set the gain value"""
        if gain == 'auto':
            self.device.setGainMode(SOAPY_SDR_RX, 0, True)
        else:
            self.device.setGainMode(SOAPY_SDR_RX, 0, False)
            self.device.setGain(SOAPY_SDR_RX, 0, float(gain))
        self.gain = gain
    
    def set_center_freq(self, freq):
        self.device.setFrequency(SOAPY_SDR_RX, 0, float(freq))
        self.center_freq = freq
    
    def set_sample_rate(self, rate):
        self.device.setSampleRate(SOAPY_SDR_RX, 0, float(rate))
        self.sample_rate = rate
    
    def set_bandwidth(self, bw):
        self.device.setBandwidth(SOAPY_SDR_RX, 0, float(bw))
        self.bandwidth = bw

    def set_ppm(self, ppm):
        """Set frequency correction if supported"""
        try:
            if 'freqCorrection' in self.device.getSettingInfo():
                self.device.writeSetting('freqCorrection', str(ppm))
                self.ppm = ppm
                return True
        except Exception as e:
            if self.stdscr:
                self.stdscr.addstr(0, 0, f"PPM correction not supported: {str(e)}", 
                             curses.color_pair(3) | curses.A_BOLD)
                self.stdscr.refresh()
                time.sleep(1)
        return False

def init_audio_device():
    """Initialize audio device with error handling and backend selection"""
    try:
        # Try to create output stream without specifying backend
        test_stream = sd.OutputStream(
            channels=1,
            samplerate=44100,
            blocksize=2048,
            dtype=np.float32
        )
        test_stream.close()
        return True
    except sd.PortAudioError as e:
        print(f"Audio initialization error: {e}")
        return False

def init_device(self):
    """Initialize SDR device with error handling for PPM correction"""
    try:
        if self.backend == 'RTL':
            self.device = RtlSdr()
            
            # Set basic parameters first, without PPM
            self.device.sample_rate = self.sample_rate
            self.device.center_freq = self.center_freq
            self.device.gain = self.gain
            
            # Don't try to set PPM during initialization
            self.ppm = 0  # Start with 0 PPM
            
    except Exception as e:
        raise RuntimeError(f"Error initializing SDR device: {e}")

def main(stdscr):
    global SCAN_ACTIVE, AGC_ENABLED, last_agc_update, SAMPLES, WATERFALL_MODE, CURRENT_DEMOD
    init_colors()
    gainindex = -1
    
    # Get initial screen dimensions
    max_height, max_width = stdscr.getmaxyx()
    
    # Initialize display mode
    current_display_mode = 'SPECTRUM'
    
    # Initialize audio
    audio_available = init_audio_device()
    if not audio_available:
        stdscr.addstr(0, 0, "Warning: Audio system initialization failed", 
                     curses.color_pair(3) | curses.A_BOLD)
        stdscr.refresh()
        time.sleep(2)
    
    # Add audio state variables
    audio_enabled = False
    stream = None

    # Add new variables for audio recording
    audio_recording = False
    wav_file = None
    recording_start_time = None

    # Initialize SDR device with selected backend
    try:
        sdr = SDRDevice(stdscr=stdscr)
        sdr.init_device()
        
        # Load saved settings if available
        settings = load_settings()
        sdr.set_sample_rate(settings['sample_rate'])
        sdr.set_center_freq(settings['frequency'])
        
        # Handle gain setting properly
        if settings['gain'] == 'auto':
            sdr.set_gain('auto')
            gainindex = -1
        else:
            try:
                gain_value = float(settings['gain'])
                valid_gains = sdr.valid_gains_db
                gainindex = min(range(len(valid_gains)), 
                              key=lambda i: abs(valid_gains[i] - gain_value))
                sdr.set_gain(valid_gains[gainindex])
            except (ValueError, TypeError):
                sdr.set_gain('auto')
                gainindex = -1
        
        # Try to set PPM after device is initialized
        try:
            if settings['ppm'] != 0:  # Only try to set non-zero PPM
                sdr.set_ppm(settings['ppm'])
        except Exception as e:
            stdscr.addstr(0, 0, f"Warning: PPM correction not supported: {str(e)}", 
                         curses.color_pair(3) | curses.A_BOLD)
            stdscr.refresh()
            time.sleep(1)
            sdr.ppm = 0  # Reset to 0 if setting fails
        
        bandwidth = settings['bandwidth']
        freq_step = settings['freq_step']
        SAMPLES = settings['samples']
        AGC_ENABLED = settings['agc_enabled']
        
        # Enable non-blocking input
        stdscr.nodelay(True)

        while True:
            try:
                current_time = time.time()
                
                # Update screen dimensions in case terminal was resized
                max_height, max_width = stdscr.getmaxyx()
                
                # Read samples and compute FFT
                try:
                    samples = sdr.read_samples((2**SAMPLES) * 256)
                    if len(samples) == 0 or np.all(samples == 0):
                        stdscr.addstr(max_height-1, 0, "Error reading samples, retrying...", 
                                     curses.color_pair(3))
                        stdscr.refresh()
                        time.sleep(0.1)
                        continue
                except Exception as e:
                    stdscr.addstr(max_height-1, 0, f"Error: {str(e)}", curses.color_pair(3))
                    stdscr.refresh()
                    time.sleep(0.1)
                    continue

                # Handle AGC if enabled
                if AGC_ENABLED and (current_time - last_agc_update) >= AGC_UPDATE_INTERVAL:
                    current_power = measure_signal_power(samples)
                    gainindex = adjust_gain(sdr, current_power, gainindex)
                    last_agc_update = current_time

                # Update audio processing logic
                if AUDIO_AVAILABLE and audio_enabled:
                    audio = demodulate_signal(samples, sdr.sample_rate, CURRENT_DEMOD)
                    audio_buffer.append(audio)

                # Calculate frequency bins
                num_bins = 1024  # Reduced from 2048
                freq_bins = np.fft.fftshift(np.fft.fftfreq(num_bins, d=1/sdr.sample_rate)) + sdr.center_freq

                # Compute FFT with improved processing
                fft = np.fft.fft(samples * np.hamming(len(samples)))
                fft = np.fft.fftshift(fft)
                
                # Compute power spectrum with better noise handling
                freq_data = 20 * np.log10(np.abs(fft) + 1e-10)
                
                # Apply moving average smoothing
                window_size = 5
                freq_data = np.convolve(freq_data, np.ones(window_size)/window_size, mode='valid')
                
                # Apply additional noise reduction
                noise_threshold = np.median(freq_data) - 10
                freq_data[freq_data < noise_threshold] = noise_threshold
                
                # Update the draw_spectrogram call to include recording status
                recording_duration = time.time() - recording_start_time if audio_recording else None
                
                draw_header(stdscr, freq_data, freq_bins, sdr.center_freq, bandwidth, sdr.gain, freq_step, sdr, audio_recording, recording_duration)
                
                if current_display_mode == 'SPECTRUM':
                    draw_spectrogram(stdscr, freq_data, freq_bins, sdr.center_freq, 
                                   bandwidth, sdr.gain, freq_step, sdr,  # Add sdr here
                                   audio_recording, recording_duration)
                elif current_display_mode == 'WATERFALL':
                    draw_waterfall(stdscr, freq_data, freq_bins, sdr.center_freq, 
                                 bandwidth, sdr.gain, freq_step, sdr,  # Add sdr here
                                 audio_recording, recording_duration)
                elif current_display_mode == 'PERSISTENCE':
                    draw_persistence(stdscr, freq_data, freq_bins, sdr.center_freq,
                                   bandwidth, sdr.gain, freq_step, sdr,  # Add sdr here
                                   audio_recording, recording_duration)
                elif current_display_mode == 'SURFACE':
                    draw_surface_plot(stdscr, freq_data, freq_bins, sdr.center_freq,
                                  bandwidth, sdr.gain, freq_step, sdr,  # Add sdr here
                                  audio_recording, recording_duration)
                elif current_display_mode == 'GRADIENT':
                    draw_gradient_waterfall(stdscr, freq_data, freq_bins, sdr.center_freq,
                                           bandwidth, sdr.gain, freq_step, sdr,
                                           audio_recording, recording_duration)
                elif current_display_mode == 'VECTOR':
                    draw_vector_display(stdscr, samples, sdr.center_freq,
                                   bandwidth, sdr.gain, freq_step, sdr)


                # Handle user input
                key = stdscr.getch()
                if key == ord('q'):  # Quit
                    break
                elif key == ord('a'):  # Toggle audio
                    if audio_available:
                        audio_enabled = not audio_enabled
                        if audio_enabled and stream is None:
                            try:
                                stream = sd.OutputStream(
                                    channels=1,
                                    samplerate=44100,
                                    callback=audio_callback,
                                    blocksize=2048,
                                    latency=0.1,
                                    dtype=np.float32
                                )
                                stream.start()
                            except sd.PortAudioError as e:
                                stdscr.addstr(0, 0, f"Audio error: {str(e)}", 
                                            curses.color_pair(3) | curses.A_BOLD)
                                stdscr.refresh()
                                time.sleep(2)
                                audio_enabled = False
                                stream = None
                        elif not audio_enabled and stream is not None:
                            try:
                                stream.stop()
                                stream.close()
                            except:
                                pass
                            stream = None
                            audio_buffer.clear()
                elif key == curses.KEY_UP:  # Increase frequency by 1 MHz
                    sdr.set_center_freq(sdr.center_freq + 1e6)
                elif key == curses.KEY_DOWN:  # Decrease frequency by 1 MHz
                    sdr.set_center_freq(max(0, sdr.center_freq - 1e6))
                elif key == curses.KEY_RIGHT:  # Increase frequency by 0.5 MHz
                    sdr.set_center_freq(sdr.center_freq + 0.5e6)
                elif key == curses.KEY_LEFT:  # Decrease frequency by 0.5 MHz
                    sdr.set_center_freq(max(0, sdr.center_freq - 0.5e6))
                elif key == ord('x'):  # Set Frequency
                    freq = setfreq(stdscr)
                    if freq[-1] in 'mM  ':
                        freq = float(freq[:-1]) * 1e6
                    elif freq[-1] in 'kK':
                        freq = float(freq[:-1]) * 1e3
                    sdr.set_center_freq(int(freq))
                elif key == ord('t'):  # Decrease step
                    freq_step = max(0.01e6, freq_step - 0.01e6)
                    draw_clearheader(stdscr)
                elif key == ord('T'):  # Increase step
                    freq_step = min(sdr.sample_rate / 2, freq_step + 0.01e6)
                    draw_clearheader(stdscr)
                elif key == ord('h'):  # Help
                    showhelp(stdscr)
                    stdscr.clear()
                    stdscr.refresh()
                elif key == ord('b'):  # Zoom in (reduce bandwidth)
                    bandwidth = max(0.1e6, bandwidth - zoom_step)
                    draw_clearheader(stdscr)
                elif key == ord('B'):  # Zoom out (increase bandwidth)
                    bandwidth = min(sdr.sample_rate, bandwidth + zoom_step)
                    draw_clearheader(stdscr)
                elif key == ord('f'):  # Shift center frequency down
                    sdr.set_center_freq(max(0, sdr.center_freq - freq_step))
                    draw_clearheader(stdscr)
                elif key == ord('F'):  # Shift center frequency up
                    sdr.set_center_freq(sdr.center_freq + freq_step)
                    draw_clearheader(stdscr)
                elif key == ord('s'):  # Decrease samples
                    SAMPLES -= 1
                    if SAMPLES < 5:
                        SAMPLES = 5
                    draw_clearheader(stdscr)
                elif key == ord('S'):  # Increase samples
                    SAMPLES += 1
                    if SAMPLES > 12:
                        SAMPLES = 12
                    draw_clearheader(stdscr)
                elif key == ord('G'):
                    gainindex +=1
                    if gainindex <= len(sdr.valid_gains_db)-1:
                        sdr.set_gain(sdr.valid_gains_db[gainindex])
                    else:
                        sdr.set_gain("auto")
                        gainindex = -1
                    draw_clearheader(stdscr)
                elif key == ord('g'):
                    gainindex -= 1
                    if gainindex < 0:
                        sdr.set_gain(sdr.valid_gains_db[0])
                        gainindex = 0
                    else:
                        sdr.set_gain(sdr.valid_gains_db[gainindex])
                    draw_clearheader(stdscr)
                elif key == ord('k'):  # Save bookmark
                    add_bookmark(stdscr, sdr.center_freq)
                elif key == ord('l'):  # Load bookmark
                    new_freq = show_bookmarks(stdscr)
                    if new_freq is not None:
                        sdr.set_center_freq(new_freq)
                elif key == ord('R'):  # Start/Stop recording
                    draw_clearheader(stdscr)
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
                    sdr.set_sample_rate(settings['sample_rate'])
                    sdr.set_center_freq(settings['frequency'])
                    sdr.set_gain(settings['gain'])
                    bandwidth = settings['bandwidth']
                    freq_step = settings['freq_step']
                    SAMPLES = settings['samples']
                    AGC_ENABLED = settings['agc_enabled']
                    stdscr.addstr(max_height-1, 0, "Settings loaded", curses.color_pair(4))
                    stdscr.refresh()
                    time.sleep(1)  # Show message briefly
                elif key == ord('A'):  # Toggle AGC
                    draw_clearheader(stdscr)
                    AGC_ENABLED = not AGC_ENABLED
                    if not AGC_ENABLED:
                        # Reset to manual gain mode
                        if gainindex >= 0 and gainindex < len(sdr.valid_gains_db):
                            sdr.set_gain(sdr.valid_gains_db[gainindex])
                        else:
                            sdr.set_gain('auto')
                            gainindex = -1
                elif key == ord('n'):  # Band presets
                    new_freq, new_bandwidth = show_band_presets(stdscr)
                    stdscr.clear()
                    if new_freq is not None:
                        sdr.set_center_freq(new_freq)
                        bandwidth = new_bandwidth
                        # Adjust gain for the new frequency range
                        if AGC_ENABLED:
                            # Force an immediate AGC update
                            last_agc_update = 0
                        show_popup_msg(stdscr,f"Switched to band: {new_freq/1e6:.3f} MHz")
                elif key == ord('c'):  # Start frequency scanner
                    # Get scanner configuration
                    start_freq, end_freq, threshold = show_scanner_menu(stdscr)
                    if start_freq is not None:
                        SCAN_ACTIVE = True
                        signals = []
                        current_freq = start_freq
                        
                        # Scanning loop
                        while current_freq <= end_freq and SCAN_ACTIVE:
                            # Update progress display
                            draw_scanning_status(stdscr, current_freq, start_freq, end_freq, sdr)
                            
                            # Check for cancel
                            if stdscr.getch() == ord('q'):
                                SCAN_ACTIVE = False
                                break
                            
                            # Perform scan for current chunk
                            try:
                                # Set frequency and allow settling time
                                sdr.set_center_freq(current_freq)
                                time.sleep(0.01)  # Short settling time
                                
                                # Read samples and compute FFT
                                samples = sdr.read_samples(2048)  # Reduced sample size for speed
                                if len(samples) > 0:
                                    # Compute power spectrum
                                    spectrum = np.fft.fftshift(np.fft.fft(samples))
                                    power_db = 10 * np.log10(np.abs(spectrum)**2 + 1e-10)
                                    
                                    # Find peak power
                                    peak_power = np.max(power_db)
                                    
                                    # If signal detected
                                    if peak_power > threshold:
                                        # Estimate bandwidth
                                        mask = power_db > (peak_power - 20)  # Points within 20dB of peak
                                        bandwidth = np.sum(mask) * (sdr.sample_rate / len(power_db))
                                        
                                        # Only add if bandwidth is reasonable
                                        if bandwidth > MIN_SIGNAL_BANDWIDTH:
                                            signals.append({
                                                'frequency': current_freq,
                                                'power': peak_power,
                                                'bandwidth': bandwidth,
                                                'type': classify_signal(samples, sdr.sample_rate, bandwidth)
                                            })
                                            
                                            # Debug output
                                            stdscr.addstr(max_height-1, 0, 
                                                        f"Signal found: {current_freq/1e6:.3f} MHz, "
                                                        f"Power: {peak_power:.1f} dB, "
                                                        f"BW: {bandwidth/1e3:.1f} kHz", 
                                                        curses.color_pair(4))
                                            stdscr.refresh()
                            
                            except Exception as e:
                                stdscr.addstr(max_height-1, 0, 
                                            f"Scan error ({type(e).__name__}): {str(e)}", 
                                            curses.color_pair(3))
                                stdscr.refresh()
                            
                            # Move to next frequency
                            current_freq += SCAN_STEP
                        
                        # After scanning, store results globally
                        if signals:
                            global LAST_SCAN_RESULTS
                            LAST_SCAN_RESULTS = signals.copy()  # Store a copy of the results
                            
                            # Display results and get selected frequency
                            new_freq = display_scan_results(stdscr, signals, threshold)
                            
                            # ... rest of existing scanning code ...
                        
                        # Reset scan state
                        SCAN_ACTIVE = False
                        stdscr.clear()
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
                elif key == ord('P'):  # Increase PPM
                    draw_clearheader(stdscr)
                    if sdr.ppm < 1000:  # Add reasonable limit
                        if sdr.set_ppm(sdr.ppm + 1):
                            show_popup_msg(stdscr, f"PPM set to {sdr.ppm}")
                        else:
                            show_popup_msg(stdscr, "Failed to set PPM", error=True)
                elif key == ord('p'):  # Decrease PPM
                    draw_clearheader(stdscr)
                    if sdr.ppm > -1000:  # Add reasonable limit
                        if sdr.set_ppm(sdr.ppm - 1):
                            show_popup_msg(stdscr, f"PPM set to {sdr.ppm}")
                        else:
                            show_popup_msg(stdscr, "Failed to set PPM", error=True)
                elif key == ord('O'):  # Set exact PPM value
                    draw_clearheader(stdscr)
                    stdscr.addstr(0, 0, "Enter PPM correction value: ", 
                                 curses.color_pair(1) | curses.A_BOLD)
                    curses.echo()
                    curses.curs_set(1)
                    stdscr.nodelay(False)
                    try:
                        ppm = int(stdscr.getstr().decode('utf-8'))
                        if sdr.set_ppm(ppm):
                            show_popup_msg(stdscr, f"PPM set to {sdr.ppm}")
                        else:
                            show_popup_msg(stdscr, "Failed to set PPM", error=True)
                    except ValueError:
                        show_popup_msg(stdscr, "Invalid PPM value!", error=True)
                    finally:
                        curses.noecho()
                        curses.curs_set(0)
                        stdscr.nodelay(True)

                # Remove the separate recording duration display since it's now handled in draw_spectrogram
                if audio_recording and AUDIO_AVAILABLE and audio_enabled:
                    if len(audio_buffer) > 0:
                        audio_data = np.concatenate(list(audio_buffer))
                        write_audio_samples(wav_file, audio_data)
                        audio_buffer.clear()

                # Add new key handler for showing last results
                elif key == ord('C'):  # Show last scan results
                    if LAST_SCAN_RESULTS:
                        stdscr.nodelay(False)
                        curses.flushinp()
                        
                        # Display the stored results
                        new_freq = display_scan_results(stdscr, LAST_SCAN_RESULTS, SIGNAL_THRESHOLD)
                        
                        # If frequency was selected, tune to it
                        if new_freq is not None:
                            sdr.set_center_freq(new_freq)
                        
                        stdscr.nodelay(True)
                        stdscr.clear()
                    else:
                        # Show message if no previous scan results exist
                        draw_clearheader(stdscr)
                        stdscr.addstr(0, 0, "No previous scan results available", curses.color_pair(3))
                        stdscr.refresh()
                        time.sleep(2)
                        draw_clearheader(stdscr)

            except curses.error:
                # Handle curses errors (like terminal resize)
                continue

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

if __name__ == "__main__":
    curses.wrapper(main)
