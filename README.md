# PySpecSDR
```
   ____        ____                  ____  ____  ____  
  |  _ \ _   _/ ___| _ __   ___  ___/ ___||  _ \|  _ \ 
  | |_) | | | \___ \| '_ \ / _ \/ __\___ \| | | | |_) |
  |  __/| |_| |___) | |_) |  __/ (__ ___) | |_| |  _ < 
  |_|    \__, |____/| .__/ \___|\___|____/|____/|_| \_\
         |___/      |_|                                
```

## PySpecSDR - Python SDR Spectrum Analyzer and Signal Processor

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

## Key Shortcuts
* f/F : Dec/Increase Center Frequency
* b/B : Dec/Increase Bandwidth
* s/S : Dec/Increase Samples
* t/T : Dec/Increase Step
* x   : Type in center frequency. Ex. 144800000, 144.8M, 144800K.
* k   : Save currenct frequncy as Bookmark
* l   : Load a bookmark
* a   : Toggle Audio On/Off
* R   : Start/Stop audio recording
* A   : Toggle AGC
* p   : Select Band Preset
* c   : Frequncy Scanner
* w   : Save Current Settings. Will be loaded next time as default.
* d   : Select demodulation mode
* m   : Cycle through visualization modes
* 1   : Spectrum Visualization
* 2   : Waterfall Visualization
* 3   : Persistence Spectrum Visualization
* 4   : Surface Visualization
* 5   : Gradient Visualization
* 6   : Vector Visualization
* Up  : Increase Freq. by 1MHz
* Down: Decrease Freq. by 1MHz
* Left: Decrease Freq. by 0.5MHz
* Rigt: Increase Freq. by 0.5MHz

## PySpecSDR Changelog

### Version 1.0.1 (2024/11/22)

Features Added:
+ Added PPM (Parts Per Million) frequency correction functionality
  - New 'P'/'p' keys to increase/decrease PPM correction
  - New 'O' key to set exact PPM correction value
  - PPM value displayed in header
  - PPM settings saved/loaded with other configurations

+ Added more band presets for various radio services
  - Amateur radio bands (160m through 23cm)
  - Shortwave radio
  - Citizens Band (CB)
  - PMR446
  - Marine VHF
  - GSM bands
  - DECT
  - LTE bands
  - WiFi 2.4/5 GHz
  - Digital radio services

+ Added scrolling capability in Help screen
  - Up/Down arrow keys for line-by-line scrolling
  - PgUp/PgDn for page scrolling
  - Visual scrollbar indicator

+ Added pagination to scan results and bookmarks
  - Next/Previous page navigation
  - Page number indicators
  - Improved readability for long lists

+ Added ability to delete bookmarks
  - 'd' key in bookmarks menu to delete entries
  - Confirmation prompt for deletion

+ Added feature to recall last scan results
  - 'C' key shows results from most recent frequency scan
  - Maintains scan history between sessions

Improvements:
! All characters now use lower ASCII for better compatibility
! All visual modes now have consistent frequency labels
! Improved signal detection algorithm
! Fixed/standardized look across all display modes

Bug Fixes:
! Fixed inconsistent character display in some terminals
! Fixed frequency label alignment issues
! Fixed bookmark sorting and display
! Improved error handling for PPM settings
! Fixed memory leak in waterfall display

Note: This version maintains backward compatibility with existing configuration files and bookmarks.

## ToDo:
* Fix bugs
* Add recording status to all visual modes
* Better management for bookmarks (DONE)

## Showcase
![spectrum-vis](https://cp737.net/files/pyspecsdr/spectrum.png)

![band-presets](https://cp737.net/files/pyspecsdr/bands.png)

Select Band to adjust frequncy and bandwidth

![demodulation-modes](https://cp737.net/files/pyspecsdr/demodulation.png)

Select demodulation mode

![gradient-vis](https://cp737.net/files/pyspecsdr/gradient.png)

Gradient Visualization mode

![persistent-vis](https://cp737.net/files/pyspecsdr/persistent.png)

Persistent Visualization mode

![scanner1](https://cp737.net/files/pyspecsdr/scanner1.png)

Select signal strength to scan for...

![scanner2](https://cp737.net/files/pyspecsdr/scanner2.png)

Select band...

![scanner3](https://cp737.net/files/pyspecsdr/scanner3.png)

Scanning...

![scanner4](https://cp737.net/files/pyspecsdr/scanner4.png)

Results. Select to listen.

![surface-vis](https://cp737.net/files/pyspecsdr/surface.png)
![vector-vis](https://cp737.net/files/pyspecsdr/vector.png)
![waterfall-vis](https://cp737.net/files/pyspecsdr/waterfall.png)


## Troubleshooting
```
1. If you get "ImportError: No module named 'rtlsdr'":
   - Check that pyrtlsdr is installed: pip3 install pyrtlsdr
2. If you get "usb.core.NoBackendError":
   - Install libusb: pip3 install libusb1
3. If you get "RTLSDRError: No device found":
   - Check device connection
   - Check udev rules (Linux)
   - Check driver installation (Windows)
4. If you get "OSError: PortAudio library not found":
   - Install PortAudio:
     Ubuntu/Debian: sudo apt-get install libportaudio2
     Fedora: sudo dnf install portaudio-devel
     Arch: sudo pacman -S portaudio
     macOS: brew install portaudio
```
Copyright (c) 2024 [XQTR]
