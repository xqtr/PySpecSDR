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
- Dependencies listed in requirements.txt

License: GPL-3.0-or-later

## Installing Dependencies

You can install the required dependencies using the requirements.txt file.

* Install via pip:

    `pip install -r requirements.txt`

## Changelog

Moved to CHANGELOG.md, as it was getting big... :)

## RTLSDR Commands Menu
Pressing the '/' key, will show a menu with various RTLSDR commands. These are examples of what you can do with the RTLSDR suite of programs like rtl_433, rtl_power etc. Selecting one, from the menu, will store it in memory, passing the current frequency as a paramater to that command. When you exit the program, this command will be printed on the terminal.

It's a simple way, to have ready to use RTLSDR commands and use the current frequency. Select one and exit, at the current frequency, to immediately, do something else (like decoding messages).

The command is not executed, it's just printed on the terminal. Copy/Paste it to use it.

## Named PIPE Function

As from version 1.0.4, PySpecSDR, has the ability to export audio to a named PIPE file, at location /tmp/sdrpipe. This means that you can launch as many programs you want and decode the same source, at the same time ;)

To start the process press the 'I' (capital I) key. The program will freeze and wait until another program attaches to the PIPE file (/tmp/sdrpipe). When it does, the program will work as before. To finish/end the process, just kill all the processes/programs that are attached to the PIPE file and it will close automatically.

The data exported to this file, is audio, with sample rate at 44100Hz, 16bit, mono. Below are some examples of commands that you can use:

`sox -t raw -r 44100 -b 16 -e signed-integer /tmp/sdrpipe -t raw - | multimon-ng -t raw -a POCSAG1200 -

ffmpeg -f s16le -ar 44100 -ac 1 -i /tmp/sdrpipe output.wav`

Multimon-ng, even if it has the ability to attach to a PIPE file, it seems it doesn't work. So using SOX is a trick to make it work. More examples on how to use multimon-ng with SOX, on the [multimon-ng](https://github.com/EliasOenal/multimon-ng)  git repo.


## Showcase
![spectrum-vis](https://cp737.net/files/pyspecsdr/1spectrum.png)

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

![surface](https://cp737.net/files/pyspecsdr/1surface.png)
![vector](https://cp737.net/files/pyspecsdr/1vector.png)

ASCII Waterfall

![waterfall](https://cp737.net/files/pyspecsdr/1waterfall.png)

RTLSDR Commands
![commands](https://cp737.net/files/pyspecsdr/rtlcmd.png)

Running flawlessly in a Hackberry Pi Q20...
![hackberry-vis](https://cp737.net/files/pyspecsdr/hbwfall.jpg)


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
