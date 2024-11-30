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

This is part of the PySpecSDR program.

It converts a GQRX CSV/Bookmark file to JSON/PySpecSDR format. Make
sure to save the file as sdr_bookmarks.json to load it to PySpecSDR, 
as it is. You can also open the file to an editor and add entries from
it.


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
Last Updated: 2024/11/30

'''
import csv
import json
import argparse

def gqrx_to_json(csv):
    results = {}
    with open(csv) as file:
        for line in file:
            line = line.strip()
            if line.startswith('#'):
                pass
            elif line.startswith('Untagged'):
                pass
            elif not line:
                pass
            else:
                #print(line.rstrip())
                flds = line.split(';')
                freq = float(flds[0])
                name = flds[1].strip()
                mode = flds[2].strip()
                band = float(flds[3].strip())
                
                if mode.startswith('Narrow'):
                    mode = "FM"
                elif mode.startswith('AM'):
                    mode = "AM"
                elif mode.startswith('WFM'):
                    mode = "WFM"
                elif mode.startswith('CW'):
                    mode = "CW"
                results[name]=[freq,mode,band]
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Load GQRX bookmarks from a file and convert to JSON/PySpecSDR format.')
    parser.add_argument('readfile', type=str, help='Path to the GQRX bookmarks file')
    parser.add_argument('savefile', type=str, help='Filename to JSON file')
    args = parser.parse_args()
    with open(args.savefile, 'w') as f:
        json.dump(gqrx_to_json(args.readfile), f, indent=2)
