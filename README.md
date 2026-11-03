# Phone Audio Bridge

Stream your Android phone's audio to your Windows PC over Wi-Fi. A small dark-themed app on top of [scrcpy](https://github.com/Genymobile/scrcpy) (audio only, no screen mirroring).

## Features
- One big Start/Stop button, live status
- Auto-detects the phone's IP (plug in USB once)
- Adjustable delay buffer
- Optional **launch with Windows** and **auto-stream with auto-reconnect**

## Requirements
- Windows, Python 3.9+ (tkinter included)
- `adb` and `scrcpy` 2.0+ on PATH (`winget install Genymobile.scrcpy`)
- Android 11+ with USB debugging enabled; phone and PC on the same Wi-Fi

## Run
```
pythonw phone_audio_bridge.pyw
```
First time: plug the phone in by USB so the app can enable Wi-Fi debugging, then press Start. After that USB is not needed until the phone reboots.

## License
MIT
