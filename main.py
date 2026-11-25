# -*- coding: utf-8 -*-
"""
TinyHand Windows - Main Entry Point.
Coordinates the click-through overlay, frosted-glass HUD capsule,
dark settings window, sound engine, keyboard hotkeys, and Windows system tray.
"""

import ctypes
import os
import sys
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from config import Config, get_data_dir, get_resource_dir
from hud_bar import TinyHandHUD
from icons import make_app_icon, make_svg_icon
from input_hook import InputHook
from overlay_window import OverlayWindow
from settings_window import SIZE_SCALES, SettingsWindow
from sound_engine import SoundEngine


def _apply_config(
    config: Config,
    overlay: OverlayWindow,
    sound_engine: SoundEngine,
    base_dir: str,
):
    """Apply saved config values to all engine components at startup."""
    # 1. Load any persisted custom hands first
    custom_hands_dir = os.path.join(base_dir, "custom_hands")
    for ch in config.get("custom_hands", []):
        key = ch.get("key", "")
        fname = ch.get("filename", "")
        if key and fname:
            overlay.add_custom_hand(key, os.path.join(custom_hands_dir, fname))

    # 2. Load any persisted custom sounds
    custom_sounds_dir = os.path.join(base_dir, "custom_sounds")
    for cs in config.get("custom_sounds", []):
        key = cs.get("key", "")
        fname = cs.get("filename", "")
        if key and fname:
            fpath = os.path.join(custom_sounds_dir, fname)
            if os.path.exists(fpath):
                sound_engine.add_custom_sound(key, fpath)

    # 3. Pointer style & scale
    style = config.get("pointer_style", "coral")
    if isinstance(style, str) and style.startswith("hand_"):
        style = style[5:]
        config.set("pointer_style", style)

    ink_choice = config.get("ink_choice", "match")
    overlay.ink_match_pointer = ink_choice == "match"
    overlay.set_pointer_style(style)

    scale_idx = max(0, min(len(SIZE_SCALES) - 1, int(config.get("pointer_scale", 2))))
    overlay.set_pointer_scale(SIZE_SCALES[scale_idx])
    overlay.show_shadow = bool(config.get("show_shadow", True))

    # 4. Ink engine settings
    ink = overlay.ink_engine
    INK_COLORS = {
        "coral": "#EE4F98",
        "cyan": "#22D3EE",
        "blue": "#3B82F6",
        "gold": "#F59E0B",
        "emerald": "#10B981",
        "violet": "#8B5CF6",
        "white": "#F1F5F9",
        "pink": "#EC4899",
    }
    if ink_choice == "rainbow":
        ink.rainbow_mode = True
    elif ink_choice in INK_COLORS:
        ink.rainbow_mode = False
        ink.current_color = QColor(INK_COLORS[ink_choice])
    else:
        ink.rainbow_mode = False

    ink.stroke_width = float(config.get("ink_width", 5))
    fade_secs = int(config.get("fade_seconds", 6))
    if fade_secs == 0:
        ink.auto_fade = False
    else:
        ink.auto_fade = True
        ink.fade_duration = float(fade_secs)

    ink.smooth_lines = bool(config.get("smooth_lines", False))
    ink.smooth_strength = int(config.get("smooth_strength", 5))

    # 5. Visual FX & Spotlight & Controls
    overlay.show_ripple = bool(config.get("click_ripple", True))
    overlay.show_comic_bubbles = bool(config.get("show_comic_bubbles", True))
    overlay.comic_word_pack = config.get("comic_word_pack", "funny")
    overlay.spotlight_radius = float(config.get("spotlight_radius", 160))
    overlay.spotlight_dim = float(config.get("spotlight_dim", 60)) / 100.0
    overlay.laser_sound = bool(config.get("laser_sound", False))
    hold_key = config.get("hold_to_draw_key", "shift")
    overlay.hold_draw_key = None if (not hold_key or hold_key == "off") else hold_key

    # 6. Sound settings
    snd_preset = config.get("sound_preset", "boop")
    sound_engine.enabled = snd_preset != "off"
    if sound_engine.enabled:
        sound_engine.set_sound(snd_preset)
    sound_engine.set_volume(float(config.get("sound_volume", 0.8)))


def _sync_hud_from_config(config: Config, overlay: OverlayWindow, hud: TinyHandHUD):
    """Ensure the floating HUD reflects persisted custom hands, scale, pointer, and audio."""
    for ch in config.get("custom_hands", []):
        key = ch.get("key", "")
        name = ch.get("name", "Custom")
        if key in overlay.hand_assets:
            hud.add_custom_hand(key, name, overlay.hand_assets[key].default_ink)

    hud.sync_pointer(overlay.current_style)
    hud.sync_scale(int(config.get("pointer_scale", 2)))
    hud.sync_comic_bubbles(overlay.show_comic_bubbles)
    hud.sync_sound(config.get("sound_preset", "boop"), overlay.sound_engine.enabled)


def main():
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "Wajahat.TinyHandWindows.App.1"
            )
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("TinyHand Windows")
    app_icon = make_app_icon()
    app.setWindowIcon(app_icon)
    app.setQuitOnLastWindowClosed(False)

    resource_dir = get_resource_dir()
    data_dir = get_data_dir()
    assets_dir = os.path.join(resource_dir, "assets")
    sounds_dir = os.path.join(assets_dir, "sounds")

    os.makedirs(os.path.join(data_dir, "custom_hands"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "custom_sounds"), exist_ok=True)

    # 1. Config & Sound Engine
    config = Config(data_dir)
    sound_engine = SoundEngine(sounds_dir)

    # 2. Permanently Click-Through Overlay Window
    overlay = OverlayWindow(assets_dir, sound_engine)
    _apply_config(config, overlay, sound_engine, data_dir)
    overlay.show()

    # 3. Frosted Obsidian Glass HUD Capsule
    hud = TinyHandHUD(overlay, sound_engine, config=config)
    _sync_hud_from_config(config, overlay, hud)
    overlay.hud_rect_provider = hud.geometry

    hud_x = config.get("hud_x", -1)
    hud_y = config.get("hud_y", -1)
    if hud_x >= 0 and hud_y >= 0:
        hud.move(hud_x, hud_y)
    hud.show()

    # 4. Global Keyboard Hotkeys
    hook = InputHook()
    hook.update_hotkeys(
        toggle=config.get("hotkey_toggle", "ctrl+alt+h"),
        clear=config.get("hotkey_clear", "ctrl+alt+x"),
        spotlight=config.get("hotkey_spotlight", "ctrl+alt+s"),
        drawing=config.get("hotkey_draw", "ctrl+alt+d"),
    )

    # 5. Obsidian Studio Settings Window
    settings_win = SettingsWindow(
        config, overlay, hud, sound_engine, overlay.ink_engine, input_hook=hook
    )
    hud.on_hud_changed = settings_win.sync_from_hud
    overlay.settings_rect_provider = (
        lambda: settings_win.geometry()
        if (settings_win.isVisible() and not settings_win.isMinimized())
        else None
    )

    def open_settings():
        settings_win.sync_from_hud()
        settings_win.showNormal()
        settings_win.raise_()
        settings_win.activateWindow()

    if hasattr(hud, "btn_settings"):
        hud.btn_settings.clicked.connect(open_settings)

    def toggle_pointer():
        overlay.pointer_visible = not overlay.pointer_visible
        hud.set_pointer_active(overlay.pointer_visible)
        overlay.sync_cursor_visibility()
        overlay.update()

    def on_esc():
        if overlay.spotlight_mode:
            hud.btn_spotlight.setChecked(False)
        else:
            toggle_pointer()

    hook.signals.hotkey_toggle.connect(toggle_pointer)
    hook.signals.hotkey_clear.connect(overlay.ink_engine.clear)
    hook.signals.hotkey_spotlight.connect(hud.btn_spotlight.click)
    hook.signals.hotkey_drawing.connect(hud.btn_draw.click)
    hook.signals.hotkey_esc.connect(on_esc)
    hook.start()

    app.aboutToQuit.connect(hook.stop)
    app.aboutToQuit.connect(overlay.restore_system_cursor)

    def _save_state():
        pos = hud.pos()
        config.set("hud_x", pos.x())
        config.set("hud_y", pos.y())
        config.save()

    app.aboutToQuit.connect(_save_state)

    # 6. Windows System Tray Integration
    tray = QSystemTrayIcon(app_icon, app)
    tray.setToolTip("TinyHand Windows")

    tray_menu = QMenu()
    tray_menu.setStyleSheet("""
        QMenu {
            background-color: #1A1C23;
            color: #F3F4F6;
            border: 1px solid rgba(255, 255, 255, 28);
            border-radius: 10px;
            padding: 6px;
            font-family: 'Segoe UI', sans-serif;
            font-size: 12px;
        }
        QMenu::item {
            padding: 6px 14px;
            border-radius: 6px;
        }
        QMenu::item:selected {
            background-color: #3B82F6;
            color: #FFFFFF;
        }
    """)

    act_settings = QAction(make_svg_icon("settings", "#60A5FA", 14), "Settings...", app)
    act_settings.triggered.connect(open_settings)
    tray_menu.addAction(act_settings)

    tray_menu.addSeparator()

    act_toggle = QAction(make_svg_icon("hand", "#E2E8F0", 14), "Toggle Pointer (Ctrl+Alt+H)", app)
    act_toggle.triggered.connect(toggle_pointer)
    tray_menu.addAction(act_toggle)

    act_draw = QAction(make_svg_icon("pen", "#E2E8F0", 14), "Toggle Drawing (Ctrl+Alt+D)", app)
    act_draw.triggered.connect(hud.btn_draw.click)
    tray_menu.addAction(act_draw)

    act_clear = QAction(make_svg_icon("clear", "#FDA4AF", 14), "Clear Screen Ink (Ctrl+Alt+X)", app)
    act_clear.triggered.connect(overlay.ink_engine.clear)
    tray_menu.addAction(act_clear)

    act_spotlight = QAction(make_svg_icon("spotlight", "#E2E8F0", 14), "Cinema Spotlight (Ctrl+Alt+S)", app)
    act_spotlight.triggered.connect(hud.btn_spotlight.click)
    tray_menu.addAction(act_spotlight)

    tray_menu.addSeparator()

    act_sound = QAction(make_svg_icon("sound_on", "#E2E8F0", 14), "Mute / Unmute Sound", app)
    act_sound.triggered.connect(hud._toggle_sound)
    tray_menu.addAction(act_sound)

    tray_menu.addSeparator()

    act_exit = QAction(make_svg_icon("close", "#F87171", 14), "Exit TinyHand Windows", app)
    act_exit.triggered.connect(app.quit)
    tray_menu.addAction(act_exit)

    tray.setContextMenu(tray_menu)
    tray.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
