# -*- coding: utf-8 -*-
"""
Persistent Configuration Manager for TinyHand Windows.
JSON-based settings with Windows startup integration.
"""

import json
import os
import sys
import winreg
from typing import Any, Dict, List, Optional


APP_NAME = "TinyHand Windows"
APP_VERSION = "1.0.0"


def get_resource_dir() -> str:
    """Return read-only resource directory (sys._MEIPASS when frozen, else source dir)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def get_data_dir() -> str:
    """Return writable data directory for config.json and custom assets."""
    if getattr(sys, "frozen", False):
        local_app = os.environ.get("LOCALAPPDATA") or os.path.dirname(sys.executable)
        data_dir = os.path.join(local_app, "TinyHandWindows")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
    return os.path.dirname(os.path.abspath(__file__))

DEFAULTS: Dict[str, Any] = {
    "app_name": APP_NAME,
    "version": APP_VERSION,
    # Pointer
    "pointer_style": "coral",
    "pointer_scale": 2,  # 0=XS, 1=S, 2=M, 3=L, 4=XL
    "show_shadow": True,
    # Visual FX
    "show_comic_bubbles": True,
    "comic_word_pack": "funny",  # "funny" / "clean" / "off"
    "click_ripple": True,
    # Spotlight
    "spotlight_radius": 160,
    "spotlight_dim": 60,
    # Ink
    "ink_choice": "match",  # "match"/"rainbow"/"cyan"/"coral"/"gold"/"emerald"/"violet"/"white"/"pink"
    "ink_width": 5,
    "fade_seconds": 6,  # 3 / 6 / 10 / 0 (keep)
    "smooth_lines": False,
    "smooth_strength": 5,  # 1-10
    # Sound
    "sound_preset": "boop",  # "off"/"boop"/"click"/"pop"/"thock"/"wood"/"squeak" or custom key
    "sound_volume": 0.8,
    "laser_sound": False,
    "custom_sounds": [],  # list of {"key": str, "label": str, "filename": str}
    # Controls
    "hold_to_draw_key": "shift",  # None/"shift"/"alt"/"ctrl"
    "hotkey_toggle": "ctrl+alt+h",
    "hotkey_clear": "ctrl+alt+x",
    "hotkey_spotlight": "ctrl+alt+s",
    "hotkey_draw": "ctrl+alt+d",
    # App
    "hud_x": -1,
    "hud_y": -1,
    "theme_mode": "dark",  # "dark" / "light"
    "launch_at_startup": False,
    "custom_hands": [],  # list of {"key": str, "name": str, "filename": str}
}


class Config:
    """Persistent JSON config manager for TinyHand Windows."""

    def __init__(self, app_dir: str):
        self.app_dir = app_dir
        self.config_path = os.path.join(app_dir, "config.json")
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Load config from disk, filling in missing keys with defaults."""
        self._data = dict(DEFAULTS)
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self._data.update(saved)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        """Persist config to disk."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any):
        self._data[key] = value

    def reset_defaults(self):
        self._data = dict(DEFAULTS)
        self.save()

    # Windows Startup via registry
    def set_launch_at_startup(self, enabled: bool):
        self.set("launch_at_startup", enabled)
        self.save()
        reg_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_key, 0, winreg.KEY_SET_VALUE)
            if enabled:
                if getattr(sys, "frozen", False):
                    launch_cmd = f'"{sys.executable}"'
                else:
                    launch_cmd = f'"{os.path.join(self.app_dir, "run.bat")}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, launch_cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except OSError:
            pass

    def get_launch_at_startup_state(self) -> bool:
        """Check actual registry state."""
        reg_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_key, 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, APP_NAME)
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except OSError:
            return False

    # Custom sounds helpers
    def add_custom_sound(self, key: str, label: str, filename: str):
        sounds = self.get("custom_sounds", [])
        # Remove old entry with same key
        sounds = [s for s in sounds if s.get("key") != key]
        sounds.append({"key": key, "label": label, "filename": filename})
        self.set("custom_sounds", sounds)
        self.save()

    def remove_custom_sound(self, key: str):
        sounds = [s for s in self.get("custom_sounds", []) if s.get("key") != key]
        self.set("custom_sounds", sounds)
        self.save()

    # Custom hands helpers
    def add_custom_hand(self, key: str, name: str, filename: str):
        hands = self.get("custom_hands", [])
        hands = [h for h in hands if h.get("key") != key]
        hands.append({"key": key, "name": name, "filename": filename})
        self.set("custom_hands", hands)
        self.save()

    def remove_custom_hand(self, key: str):
        hands = [h for h in self.get("custom_hands", []) if h.get("key") != key]
        self.set("custom_hands", hands)
        self.save()
