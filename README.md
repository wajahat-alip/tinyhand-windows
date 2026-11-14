# Wajji TinyHand PRO (Windows Edition)

[![Windows 10/11](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white)](https://github.com/wajahat-alip/wajji-tinyhand-pro)
[![Release](https://img.shields.io/github/v/release/wajahat-alip/wajji-tinyhand-pro?color=3B82F6&label=Download%20v1.0.0)](https://github.com/wajahat-alip/wajji-tinyhand-pro/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Web Showcase](https://img.shields.io/badge/Web%20Showcase-Live%20Demo-blue)](https://wajahat-alip.github.io/wajji-tinyhand-pro/)

> **Website & Interactive Demo**: [https://wajahat-alip.github.io/wajji-tinyhand-pro/](https://wajahat-alip.github.io/wajji-tinyhand-pro/)

A polished, zero-lag, permanently click-through Windows native presentation pointer inspired by `nilbuild/tinyhand`, featuring telescopic rod kinematics, all 36 original 3D hand styles, custom animated pointers, smooth vector ink trails with Chaikin line stabilization, auditorium spotlight mode, a frosted-glass HUD capsule, and the custom **Obsidian Studio** settings suite.

---

## Features

- **Custom Dark Settings Window**:
  - Clean frameless dark-graphite interface with live interactive preview canvas.
  - **Live Interactive Preview Canvas**: Test hand styles, pointer scaling (`XS`–`XL`), silhouette drop shadows, ink colors, rainbow spectrum trails, Chaikin smooth lines, expanding click ripple rings, comic pop bubbles, and cinema spotlight live inside the preview box.
  - **Searchable Pointer Gallery & Custom Hands**: Browse all 36 3D PNG hands + 4 animated vector pointers (`Cat Paw`, `Magic Wand`, `Boxing Glove`, `Cyber Laser`), or upload your own transparent PNG pointer.
  - **Custom Audio & Hotkeys**: Built-in WAV tap presets (`Boop`, `Click`, `Pop`, `Thock`, `Wood`, `Squeak`), custom WAV/MP3 sound uploads, volume slider, configurable **Hold-to-Draw** modifier (`Shift`/`Alt`/`Ctrl`), rebindable global hotkeys, and optional Windows startup.
- **60fps Sub-Pixel Kinematics & Zero Click Blocking**:
  - 1:1 locked fingertip tracking via `QCursor.pos()` and `GetAsyncKeyState` polling with zero low-level mouse hooks.
  - Permanent `WS_EX_TRANSPARENT` click-through overlay so background apps never lose clicks.
- **Auditorium Spotlight Mode & Frosted Floating HUD**:
  - Smooth radial vignette (`Ctrl + Alt + S`), DPI-aware floating capsule with SVG icons, and collapse-to-orb mode.

---

## Keyboard Shortcuts (Default)

| Shortcut | Action |
|---|---|
| `Ctrl + Alt + H` | Toggle pointer visibility ON / OFF |
| `Ctrl + Alt + D` | Toggle live screen drawing mode |
| `Ctrl + Alt + S` | Toggle Cinema Spotlight mode |
| `Ctrl + Alt + X` | Clear all screen ink drawings |
| `Hold Shift` (configurable) | Temporary Hold-to-Draw modifier |
| `Esc` | Exit Spotlight mode or toggle pointer |

*(All shortcuts can be customized inside **Settings → General**.)*

---

## How to Run

### Standalone Executable (Recommended for End Users)
Double-click **`dist\WajjiTinyHandPRO.exe`** — zero Python installation required. Settings and custom uploads are stored in `%LOCALAPPDATA%\WajjiTinyHandPRO\`.

### From Source (Development)
Double-click **`run.bat`** in `C:\Users\PC\.gemini\antigravity\scratch\tinyhand-windows` or run:
```powershell
cd C:\Users\PC\.gemini\antigravity\scratch\tinyhand-windows
python main.py
```

### Build Standalone `.exe`
Run **`build_exe.bat`** (requires `pyinstaller`):
```powershell
pyinstaller --clean --noconfirm WajjiTinyHandPRO.spec
```
Output executable: `dist\WajjiTinyHandPRO.exe`.

---

## Project Structure

```text
tinyhand-windows/
├── assets/                   # 36 original 3D hand PNGs, app_icon.ico & WAV sound presets
│   └── sounds/               # tap_boop, tap_click, tap_pop, tap_thock, tap_squeak, tap_wood
├── custom_hands/             # User-uploaded custom transparent PNG pointers (source mode)
├── custom_sounds/            # User-uploaded custom WAV/MP3 tap sounds (source mode)
├── config.py                 # Persistent JSON config, frozen-path resolver & Windows startup
├── icons.py                  # DPI-aware inline SVG vector icon renderer & tray icon generator
├── hand_engine.py            # Fast asset analyzer, silhouette shadow cache & custom pointers
├── ink_engine.py             # Quadratic-spline glow ink, Rainbow mode & Chaikin stabilizer
├── sound_engine.py           # Async WAV playback + QMediaPlayer custom audio & volume control
├── overlay_window.py         # Multi-monitor click-through overlay, ripples, spotlight & kinematics
├── hud_bar.py                # DPI-aware frosted glass HUD capsule
├── settings_window.py        # Custom dark Settings UI & Live Interactive Preview Canvas
├── input_hook.py             # Rebindable global keyboard hotkey listener (zero mouse hooks)
├── main.py                   # Application coordinator & Windows system tray
├── WajjiTinyHandPRO.spec     # PyInstaller single-file build specification
├── build_exe.bat             # One-click standalone .exe builder
├── run.bat                   # Development Windows launcher
├── THIRD_PARTY_LICENSES.txt  # MIT license attribution for bundled assets
└── README.md                 # Documentation
```
