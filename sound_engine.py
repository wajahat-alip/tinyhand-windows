# -*- coding: utf-8 -*-
"""
Sound Engine for TinyHand Pro (Windows Edition).
Plays authentic click and tap sounds asynchronously using Windows native audio.
Supports custom user sounds (MP3/WAV) via QMediaPlayer + QAudioOutput and
per-instance volume control for both built-in and custom sounds.
"""

import os
import threading
import winsound
from typing import Dict, Optional

from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtCore import QUrl


class SoundEngine:
    """Manages tap sound presets and zero-blocking Windows WAV playback.

    Built-in sounds are played via winsound (async, zero-latency).
    Custom user sounds (MP3/WAV) are played via QMediaPlayer + QAudioOutput.
    Volume is applied to both channels.
    """

    SOUNDS: Dict[str, str] = {
        "boop": "tap_boop.wav",
        "click": "tap_click.wav",
        "pop": "tap_pop.wav",
        "thock": "tap_thock.wav",
        "wood": "tap_wood.wav",
        "squeak": "tap_squeak.wav",
    }

    def __init__(self, sounds_dir: str):
        self.sounds_dir = sounds_dir
        self.enabled = True
        self.current_sound = "boop"
        self._sound_paths: Dict[str, str] = {}
        self._custom_sounds: Dict[str, str] = {}  # key -> absolute file path
        self._volume: float = 0.8

        # QMediaPlayer for custom sounds (reused for previews)
        self._audio_output = QAudioOutput()
        self._audio_output.setVolume(self._volume)
        self._media_player = QMediaPlayer()
        self._media_player.setAudioOutput(self._audio_output)

        self._load_sounds()

    # ------------------------------------------------------------------
    # Internal sound discovery
    # ------------------------------------------------------------------

    def _load_sounds(self):
        for key, filename in self.SOUNDS.items():
            path = os.path.join(self.sounds_dir, filename)
            if os.path.exists(path):
                self._sound_paths[key] = path
            else:
                alt_path = os.path.join(self.sounds_dir, "sounds", filename)
                if os.path.exists(alt_path):
                    self._sound_paths[key] = alt_path

    # ------------------------------------------------------------------
    # Volume
    # ------------------------------------------------------------------

    @property
    def volume(self) -> float:
        """Current playback volume (0.0-1.0)."""
        return self._volume

    def set_volume(self, vol: float):
        """Set playback volume for both built-in and custom sounds (0.0-1.0)."""
        self._volume = max(0.0, min(1.0, vol))
        self._audio_output.setVolume(self._volume)

    # ------------------------------------------------------------------
    # Custom sounds management
    # ------------------------------------------------------------------

    @property
    def custom_sounds(self) -> Dict[str, str]:
        """Read-only view of registered custom sounds (key -> path)."""
        return dict(self._custom_sounds)

    def add_custom_sound(self, key: str, path: str):
        """Register a custom sound file under the given key.

        Args:
            key:  Unique identifier (e.g. "my_clap").
            path: Absolute path to an MP3 or WAV file.
        """
        self._custom_sounds[key] = path

    def remove_custom_sound(self, key: str):
        """Unregister a custom sound by key."""
        self._custom_sounds.pop(key, None)
        # Fall back to default preset if the removed key was active
        if self.current_sound == key:
            self.current_sound = "boop"

    # ------------------------------------------------------------------
    # Playback control
    # ------------------------------------------------------------------

    def set_sound(self, sound_name: str):
        """Select the active sound preset or custom key."""
        if sound_name in self.SOUNDS or sound_name in self._custom_sounds:
            self.current_sound = sound_name

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        return self.enabled

    def play(self, sound_override: Optional[str] = None):
        """Play the current (or overridden) sound asynchronously."""
        if not self.enabled:
            return

        sound_key = sound_override or self.current_sound
        self._play_key(sound_key)

    def play_preview(self, sound_key: str):
        """Preview a sound from the settings panel (always plays, ignoring enabled flag)."""
        self._play_key(sound_key)

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    def _play_key(self, sound_key: str):
        """Dispatch playback to the correct backend for the given key."""
        # Custom sound: use QMediaPlayer
        if sound_key in self._custom_sounds:
            path = self._custom_sounds[sound_key]
            if os.path.exists(path):
                self._media_player.setSource(QUrl.fromLocalFile(path))
                self._media_player.play()
            return

        # Built-in WAV: use winsound (async, low-latency)
        path = self._sound_paths.get(sound_key)

        def _play_async():
            try:
                if path and os.path.exists(path):
                    winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                else:
                    winsound.Beep(980, 20)
            except Exception:
                pass

        threading.Thread(target=_play_async, daemon=True).start()
