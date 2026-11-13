# -*- coding: utf-8 -*-
"""
Global Keyboard Hotkey Hook for TinyHand Pro (Windows Edition).
Uses pynput keyboard listener only (zero low-level mouse hooks),
ensuring 100% native Windows mouse responsiveness.
Supports dynamic hotkey rebinding via Settings.
"""

from typing import Dict, Set, Tuple
from pynput import keyboard
from PyQt6.QtCore import QObject, pyqtSignal


class InputHookSignals(QObject):
    hotkey_toggle = pyqtSignal()
    hotkey_clear = pyqtSignal()
    hotkey_spotlight = pyqtSignal()
    hotkey_drawing = pyqtSignal()
    hotkey_esc = pyqtSignal()


class InputHook:
    """Listens for configurable global modifier+key shortcuts and Esc."""

    def __init__(self):
        self.signals = InputHookSignals()
        self.keyboard_listener = None
        self._current_keys: set = set()
        self._bindings: Dict[str, Tuple[Set[str], str]] = {}
        self.update_hotkeys(
            toggle="ctrl+alt+h",
            clear="ctrl+alt+x",
            spotlight="ctrl+alt+s",
            drawing="ctrl+alt+d",
        )

    @staticmethod
    def _parse_hotkey(spec: str) -> Tuple[Set[str], str]:
        parts = [p.strip().lower() for p in (spec or "").split("+") if p.strip()]
        mods = set()
        trigger = ""
        for p in parts:
            if p in ("ctrl", "control"):
                mods.add("ctrl")
            elif p == "alt":
                mods.add("alt")
            elif p == "shift":
                mods.add("shift")
            else:
                trigger = p
        return mods, trigger

    def update_hotkeys(
        self,
        toggle: str = "ctrl+alt+h",
        clear: str = "ctrl+alt+x",
        spotlight: str = "ctrl+alt+s",
        drawing: str = "ctrl+alt+d",
    ):
        """Update active hotkey bindings dynamically."""
        self._bindings = {
            "toggle": self._parse_hotkey(toggle),
            "clear": self._parse_hotkey(clear),
            "spotlight": self._parse_hotkey(spotlight),
            "drawing": self._parse_hotkey(drawing),
        }

    def start(self):
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self.keyboard_listener.daemon = True
        self.keyboard_listener.start()

    def stop(self):
        if self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
            except Exception:
                pass
            self.keyboard_listener = None

    def _active_modifiers(self) -> Set[str]:
        mods = set()
        if any(k in self._current_keys for k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)):
            mods.add("ctrl")
        if any(k in self._current_keys for k in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr)):
            mods.add("alt")
        if any(k in self._current_keys for k in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r)):
            mods.add("shift")
        return mods

    @staticmethod
    def _match_key(key, target: str) -> bool:
        if not target:
            return False
        vk = getattr(key, "vk", None)
        if len(target) == 1:
            if vk == ord(target.upper()):
                return True
            char = getattr(key, "char", None)
            if char and char.lower() == target:
                return True
        name = getattr(key, "name", None)
        if name and name.lower() == target:
            return True
        return False

    def _on_key_press(self, key):
        self._current_keys.add(key)

        if key == keyboard.Key.esc:
            self.signals.hotkey_esc.emit()
            return

        active_mods = self._active_modifiers()
        for action, (req_mods, trigger) in self._bindings.items():
            if not trigger:
                continue
            if active_mods == req_mods and self._match_key(key, trigger):
                if action == "toggle":
                    self.signals.hotkey_toggle.emit()
                elif action == "clear":
                    self.signals.hotkey_clear.emit()
                elif action == "spotlight":
                    self.signals.hotkey_spotlight.emit()
                elif action == "drawing":
                    self.signals.hotkey_drawing.emit()
                break

    def _on_key_release(self, key):
        self._current_keys.discard(key)
