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

## ToDo:
* Fix bugs
* Add recording status to all visual modes
* Better management for bookmarks

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
