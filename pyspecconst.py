
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

BAND_PRESETS = {
    # Amateur Radio Bands
    'HAM160': (1.8e6, 2.0e6, "160m Amateur Band"),
    'HAM80': (3.5e6, 4.0e6, "80m Amateur Band"),
    'HAM60': (5.3515e6, 5.3665e6, "60m Amateur Band"),
    'HAM40': (7.0e6, 7.3e6, "40m Amateur Band"),
    'HAM30': (10.1e6, 10.15e6, "30m Amateur Band"),
    'HAM20': (14.0e6, 14.35e6, "20m Amateur Band"),
    'HAM17': (18.068e6, 18.168e6, "17m Amateur Band"),
    'HAM15': (21.0e6, 21.45e6, "15m Amateur Band"),
    'HAM12': (24.89e6, 24.99e6, "12m Amateur Band"),
    'HAM10': (28.0e6, 29.7e6, "10m Amateur Band"),
    'HAM6': (50.0e6, 54.0e6, "6m Amateur Band"),
    'HAM2': (144.0e6, 148.0e6, "2m Amateur Band"),
    'HAM70CM': (420.0e6, 450.0e6, "70cm Amateur Band"),
    
    # CB Radio
    'CB': (26.965e6, 27.405e6, "Citizens Band Radio"),
    
    # Marine Bands
    'MARINE': (156.0e6, 162.025e6, "Marine VHF"),
    'MARINE_MF': (1.605e6, 4.0e6, "Marine MF Band"),
    
    # Aviation
    'AIR_VOICE': (118.0e6, 137.0e6, "Aircraft Voice Comms"),
    'AIR_NAV': (108.0e6, 117.975e6, "Aircraft Navigation"),
    
    # Emergency Services
    'NOAA': (162.4e6, 162.55e6, "NOAA Weather Radio"),
    'PUBLIC': (152.0e6, 162.0e6, "Public Safety VHF"),
    'PUBLIC_UHF': (450.0e6, 470.0e6, "Public Safety UHF"),
    
    # Broadcast
    'AM': (535e3, 1.705e6, "AM Broadcast"),
    'FM': (87.5e6, 108.0e6, "FM Broadcast"),
    'SW1': (2.3e6, 2.495e6, "Shortwave Band 1"),
    'SW2': (3.2e6, 3.4e6, "Shortwave Band 2"),
    'SW3': (4.75e6, 4.995e6, "Shortwave Band 3"),
    'SW4': (5.9e6, 6.2e6, "Shortwave Band 4"),
    'SW5': (7.3e6, 7.35e6, "Shortwave Band 5"),
    'SW6': (9.4e6, 9.9e6, "Shortwave Band 6"),
    'SW7': (11.6e6, 12.1e6, "Shortwave Band 7"),
    'SW8': (13.57e6, 13.87e6, "Shortwave Band 8"),
    'SW9': (15.1e6, 15.8e6, "Shortwave Band 9"),
    'SW10': (17.48e6, 17.9e6, "Shortwave Band 10"),
    'SW11': (21.45e6, 21.85e6, "Shortwave Band 11"),
    'SW12': (25.67e6, 26.1e6, "Shortwave Band 12"),
    
    # Digital Modes Common Frequencies
    'FT8_40': (7.074e6, 7.076e6, "40m FT8"),
    'FT8_20': (14.074e6, 14.076e6, "20m FT8"),
    'PSK31_40': (7.070e6, 7.071e6, "40m PSK31"),
    'PSK31_20': (14.070e6, 14.071e6, "20m PSK31"),
    'RTTY_40': (7.080e6, 7.125e6, "40m RTTY"),
    'RTTY_20': (14.080e6, 14.099e6, "20m RTTY"),
    
    # CW (Morse) Common Frequencies
    'CW_80': (3.5e6, 3.6e6, "80m CW"),
    'CW_40': (7.0e6, 7.125e6, "40m CW"),
    'CW_30': (10.1e6, 10.13e6, "30m CW"),
    'CW_20': (14.0e6, 14.15e6, "20m CW"),
    
    # Satellite
    'SAT_VHF': (145.8e6, 146.0e6, "Amateur Satellite VHF"),
    'SAT_UHF': (435.0e6, 438.0e6, "Amateur Satellite UHF"),
    'NOAA_SAT': (137.0e6, 138.0e6, "NOAA Weather Satellites"),
    
    # Time Signals
    'WWV': (2.5e6, 20.0e6, "WWV Time Signals"),
    'WWVH': (2.5e6, 15.0e6, "WWVH Time Signals"),
}

BAND_BANDWIDTHS = {
    'AM': 10e3,
    'NFM': 200e3,
    'WFM': 100e6,
    'HAM160': 2.7e3,
    'HAM80': 2.7e3,
    'HAM40': 2.7e3,
    'HAM20': 2.7e3,
    'CB': 10e3,
    'MARINE': 16e3,
    'AIR_VOICE': 8.33e3,
    'NOAA': 25e3,
    'FT8_40': 3e3,
    'FT8_20': 3e3,
    'PSK31_40': 500,
    'PSK31_20': 500,
    'RTTY_40': 3e3,
    'RTTY_20': 3e3,
    'CW_80': 500,
    'CW_40': 500,
    'CW_30': 500,
    'CW_20': 500,
    'SAT_VHF': 50e3,
    'SAT_UHF': 50e3,
    'NOAA_SAT': 40e3,
}

MORSE_CODE = {
    '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E',
    '..-.': 'F', '--.': 'G', '....': 'H', '..': 'I', '.---': 'J',
    '-.-': 'K', '.-..': 'L', '--': 'M', '-.': 'N', '---': 'O',
    '.--.': 'P', '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T',
    '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y',
    '--..': 'Z', '.----': '1', '..---': '2', '...--': '3', '....-': '4',
    '.....': '5', '-....': '6', '--...': '7', '---..': '8', '----.': '9',
    '-----': '0', '--..--': ',', '.-.-.-': '.', '..--..': '?',
    '-..-.': '/', '-....-': '-', '-.--.': '(', '-.--.-': ')',
    '.-...': '&', '---...': ':', '-.-.-.': ';', '-...-': '=',
    '.-.-.': '+', '.-..-.': '"', '...-..-': '$', '.--.-.': '@',
    '..--.-': '_', '...---...': 'SOS'
}

# Define help content with categories
help_content = [
    ("General Controls", [
        ("q", "Quit program"),
        ("h", "Show this help screen"),
        ("w", "Save current settings"),
        ("m", "Cycle through display modes"),
        ("1-6", "Quick switch display modes"),
        ("/", "RTL Commands Selector"),
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
        ("I", "Start/Stop named PIPE at /tmp/sdrpipe"),
    ]),
    ("Decoders", [
        ("M", "Morse Code Decoder (experimental)"),
        (".", "APRS Decoder (experimental)"),
    ]),
    ("Frequency Management", [
        ("k/l", "Save/Load frequency bookmark"),
        ("n", "Access band presets"),
        ("c", "Start frequency scanner"),
        ("C", "Show scan results"),
        ("", ""),
    ]),
]