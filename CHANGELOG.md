## PySpecSDR Changelog

### Version 1.0.1 (2024/11/22)

#### Features Added:
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

#### Improvements:
* ! All characters now use lower ASCII for better compatibility
* ! All visual modes now have consistent frequency labels
* ! Improved signal detection algorithm
* ! Fixed/standardized look across all display modes

#### Bug Fixes:
* ! Fixed inconsistent character display in some terminals
* ! Fixed frequency label alignment issues
* ! Fixed bookmark sorting and display
* ! Improved error handling for PPM settings
* ! Fixed memory leak in waterfall display

### Version 1.0.2 (2024/11/24)

#### Features Added:
+ The x axis has a center marker, with adjustable width, proportional to Bandwidth

#### Improvements:
* Adjusted calculation for better spectrogram/waterfall visualization
  
#### Bug Fixes:
* Fixed Initialization process for LimeSDR
* Revert spectrogram drawing to first release

### Version 1.0.3 (2024/11/30)

#### Features Added:
* The program now displays the Band name if the center frequency is inside a known one
* The '/' key opens the RTLSDR Commands menu (read below)
* Added an utility to convert CSV/GQRX bookmark files to JSON/PySpecSDR format

#### Bug Fixes:
* Fixed AGC string in header
* Fixed bugs in user inputs

#### Features Removed:
* RTLSDR version removed. SoapySDR is more capable and supports more devices.

### Version 1.0.4 (2024/12/07)

#### Features Added:
* Named PIPE to /tmp/sdrpipe of audio, to use with any program that decodes signals, like multimon-ng.

#### Bug Fixes:
* Improved sound quality to NFM and WFM modes, thanks to ChrisDev8 (https://github.com/xqtr/PySpecSDR/issues/3)

### Version 1.0.5 (2024/12/15)

#### Fixes:
* Change string for Narrow FM, to NFM, from FM, to avoid confusion (https://github.com/xqtr/PySpecSDR/issues/3)
* IQ correction added to all demodulation modes (https://github.com/xqtr/PySpecSDR/issues/3)
* Added filter between 300 and 3000 hz to remove low frequency harmonics and high pitched, out of band noise (between 300 and 3000 hz to remove low frequency harmonics and high pitched, out of band noise)
* Converted all audio to Stereo, even in Mono sound the program outputs stereo/two channel sound.

