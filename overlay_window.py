# -*- coding: utf-8 -*-
"""
Overlay Window for TinyHand Pro (Windows Edition).
Borderless, always-on-top, permanently click-through translucent layered window.
Uses 60fps QCursor.pos() + GetAsyncKeyState polling with delta-time kinematics
and zero low-level mouse hooks.
"""

import ctypes
import glob
import math
import os
import random
import time
from typing import Callable, Dict, List, Optional
from PyQt6.QtCore import QElapsedTimer, QPointF, QRect, QRectF, Qt, QTimer
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QGuiApplication,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import QWidget

from hand_engine import CustomFunnyPointers, HandAsset
from ink_engine import InkEngine

# Windows API constants for permanently click-through layered overlay
user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008
WS_EX_NOACTIVATE = 0x08000000
VK_LBUTTON = 0x01


class ClickRipple:
    """Expanding concentric ring that pulses on each click tap."""
    DURATION = 0.45  # seconds

    def __init__(self, x: float, y: float, color: QColor):
        self.x = x
        self.y = y
        self.color = color
        self.born = time.time()

    def alive(self, now: float) -> bool:
        return now - self.born < self.DURATION

    def draw(self, painter: QPainter, now: float):
        progress = (now - self.born) / self.DURATION  # 0.0 → 1.0
        radius = 8 + progress * 52  # 8px → 60px
        alpha = int(220 * (1.0 - progress))
        ring_color = QColor(self.color)
        ring_color.setAlpha(alpha)
        pen = QPen(ring_color, max(1.0, 3.0 * (1.0 - progress)))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(self.x, self.y), radius, radius)


class ComicBubble:
    """Playful tap pop badge displayed briefly above click points."""

    WORDS_FUNNY = ("BOOP!", "TAP!", "POW!", "CLICK!", "BAM!", "PING!")
    WORDS_CLEAN = ("CLICK", "POINT", "HERE", "TAP", "FOCUS")

    def __init__(self, x: float, y: float, color: QColor, pack: str = "funny"):
        self.x = x
        self.y = y - 14.0
        pool = self.WORDS_CLEAN if pack == "clean" else self.WORDS_FUNNY
        self.word = random.choice(pool)
        self.color = color
        self.created_at = time.time()
        self.duration = 0.60
        self.vy = -38.0

    def draw(self, painter: QPainter, now: float) -> bool:
        elapsed = now - self.created_at
        if elapsed > self.duration:
            return False

        progress = elapsed / self.duration
        alpha = max(0.0, 1.0 - progress)
        curr_y = self.y + (self.vy * elapsed)
        scale = 0.92 + 0.28 * min(1.0, progress * 1.4)

        painter.save()
        painter.translate(self.x + 22.0, curr_y)
        painter.scale(scale, scale)

        bg_col = QColor(self.color.red(), self.color.green(), self.color.blue(), int(225 * alpha))
        border_col = QColor(255, 255, 255, int(235 * alpha))

        bubble_rect = QRectF(-28, -12, 56, 22)
        bubble_path = QPainterPath()
        bubble_path.addRoundedRect(bubble_rect, 9, 9)
        painter.fillPath(bubble_path, QBrush(bg_col))
        painter.setPen(QPen(border_col, 1.4))
        painter.drawPath(bubble_path)

        font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, int(255 * alpha)))
        painter.drawText(bubble_rect, Qt.AlignmentFlag.AlignCenter, self.word)

        painter.restore()
        return True


class OverlayWindow(QWidget):
    """Fullscreen transparent click-through overlay for hands, spotlight, and ink."""

    def __init__(self, assets_dir: str, sound_engine):
        super().__init__()
        self.assets_dir = assets_dir
        self.sound_engine = sound_engine
        self.ink_engine = InkEngine()

        # State flags
        self.pointer_visible = True
        self.drawing_mode = False
        self.spotlight_mode = False
        self.spotlight_radius: float = 160.0
        self.spotlight_dim: float = 0.60
        self.show_comic_bubbles: bool = True
        self.comic_word_pack: str = "funny"
        self.show_shadow = True
        self.show_ripple: bool = True
        self.laser_sound: bool = False
        self.ink_match_pointer: bool = True
        self.ripples: List[ClickRipple] = []
        self.hold_draw_key: Optional[str] = "shift"
        self._hold_draw_active: bool = False
        self._hold_activated_draw: bool = False
        self.pointer_scale = 1.0
        self.hud_rect_provider: Optional[Callable[[], QRect]] = None

        # Cursor & kinematics state
        self.hand_assets: Dict[str, HandAsset] = {}
        self.current_style = "coral"
        self.comic_bubbles: List[ComicBubble] = []

        self._init_window()
        self._load_all_hands()

        initial_local = self.mapFromGlobal(QCursor.pos())
        self.cursor_pos = QPointF(float(initial_local.x()), float(initial_local.y()))
        self.grip_x = self._compute_target_grip_x(self.cursor_pos.x())
        self.press_amount = 0.0
        self.is_mouse_down = False
        self._last_painted_state = None

        self._frame_timer = QElapsedTimer()
        self._frame_timer.start()

        # 60fps decoupled render/polling timer
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _init_window(self):
        screen_rect = QRectF()
        for s in QGuiApplication.screens():
            screen_rect = screen_rect.united(QRectF(s.geometry()))

        self.setGeometry(
            int(screen_rect.x()),
            int(screen_rect.y()),
            int(screen_rect.width()),
            int(screen_rect.height()),
        )

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._enforce_click_through()

    def showEvent(self, event):
        super().showEvent(event)
        self._enforce_click_through()

    def _enforce_click_through(self):
        hwnd = int(self.winId())
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        desired = (
            style
            | WS_EX_TRANSPARENT
            | WS_EX_LAYERED
            | WS_EX_TOOLWINDOW
            | WS_EX_TOPMOST
            | WS_EX_NOACTIVATE
        )
        if style != desired:
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, desired)

    def _compute_target_grip_x(self, cursor_x: float) -> float:
        w = max(1.0, float(self.width()))
        return min(max(cursor_x + 0.28 * w, w * 0.15), w * 1.05)

    def toggle_spotlight(self):
        self.spotlight_mode = not self.spotlight_mode
        self.update()

    def toggle_drawing(self):
        self.drawing_mode = not self.drawing_mode
        if not self.drawing_mode:
            self.ink_engine.end_stroke()
        self.update()

    def set_pointer_scale(self, scale: float):
        self.pointer_scale = max(0.6, min(1.5, scale))
        self.update()

    def _load_all_hands(self):
        pattern = os.path.join(self.assets_dir, "hand_*.png")
        for fpath in sorted(glob.glob(pattern)):
            fname = os.path.basename(fpath)
            style_name = fname[5:-4]  # strip 'hand_' and '.png'
            self.hand_assets[style_name] = HandAsset(style_name, fpath)

        if "coral" in self.hand_assets:
            self.ink_engine.current_color = self.hand_assets["coral"].default_ink

    def add_custom_hand(self, key: str, filepath: str) -> Optional[HandAsset]:
        """Load and register a user-uploaded custom hand PNG."""
        if not os.path.exists(filepath):
            return None
        asset = HandAsset(key, filepath)
        self.hand_assets[key] = asset
        return asset

    def remove_custom_hand(self, key: str):
        """Unregister a custom hand asset."""
        self.hand_assets.pop(key, None)
        if self.current_style == key:
            self.set_pointer_style("coral")

    def get_pointer_default_color(self, style: str) -> QColor:
        """Return the matching ink color for any pointer style."""
        if style in self.hand_assets:
            return QColor(self.hand_assets[style].default_ink)
        if style == "laser":
            return QColor("#EF4444")
        if style == "cat_paw":
            return QColor("#FB7185")
        if style == "magic_wand":
            return QColor("#38BDF8")
        if style == "boxing_glove":
            return QColor("#DC2626")
        return QColor("#EE4F98")

    def set_pointer_style(self, style: str):
        self.current_style = style
        if self.ink_match_pointer:
            self.ink_engine.current_color = self.get_pointer_default_color(style)
        self.update()

    def _ink_color(self) -> QColor:
        return self.ink_engine.current_color

    def _is_over_hud(self, global_pos) -> bool:
        if self.hud_rect_provider is None:
            return False
        try:
            return self.hud_rect_provider().contains(global_pos)
        except Exception:
            return False

    def _on_mouse_down_event(self, global_pos, local_pt: QPointF):
        self.is_mouse_down = True
        if self._is_over_hud(global_pos):
            return

        self.press_amount = 1.0
        if self.current_style != "laser" or self.laser_sound:
            self.sound_engine.play()

        if self.show_comic_bubbles and self.current_style != "laser":
            self.comic_bubbles.append(
                ComicBubble(local_pt.x(), local_pt.y(), self.ink_engine.current_color, self.comic_word_pack)
            )

        if self.show_ripple:
            self.ripples.append(ClickRipple(local_pt.x(), local_pt.y(), self._ink_color()))

        if self.drawing_mode:
            self.ink_engine.begin_stroke(local_pt)

    def _on_mouse_up_event(self):
        self.is_mouse_down = False
        if self.ink_engine.is_drawing:
            self.ink_engine.end_stroke()

    def _tick(self):
        dt = max(0.001, min(0.05, self._frame_timer.restart() / 1000.0))

        # 1. Exact 1:1 cursor tracking mapped to overlay coordinates
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)
        new_cursor = QPointF(float(local_pos.x()), float(local_pos.y()))
        cursor_moved = (
            abs(new_cursor.x() - self.cursor_pos.x()) > 0.2
            or abs(new_cursor.y() - self.cursor_pos.y()) > 0.2
        )
        self.cursor_pos = new_cursor

        # 2. Smooth frame-rate-independent grip inertia
        target_gx = self._compute_target_grip_x(self.cursor_pos.x())
        grip_alpha = 1.0 - math.exp(-9.0 * dt)
        grip_moving = abs(target_gx - self.grip_x) > 0.25
        if grip_moving:
            self.grip_x += (target_gx - self.grip_x) * grip_alpha
        else:
            self.grip_x = target_gx

        # 3. Non-blocking click polling via Win32 GetAsyncKeyState
        is_lbutton_down = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)

        # Hold-to-Draw key (Shift / Alt / Ctrl)
        VK_MAP = {"shift": 0x10, "ctrl": 0x11, "alt": 0x12}
        if self.hold_draw_key and self.hold_draw_key in VK_MAP:
            held = bool(user32.GetAsyncKeyState(VK_MAP[self.hold_draw_key]) & 0x8000)
            if held != self._hold_draw_active:
                self._hold_draw_active = held
                if held and not self.drawing_mode:
                    self.drawing_mode = True
                    self._hold_activated_draw = True
                elif not held and self._hold_activated_draw:
                    self._hold_activated_draw = False
                    self.drawing_mode = False
                    if self.ink_engine.is_drawing:
                        self.ink_engine.end_stroke()
        elif self._hold_activated_draw:
            self._hold_activated_draw = False
            self._hold_draw_active = False
            self.drawing_mode = False

        btn_changed = False
        if is_lbutton_down and not self.is_mouse_down:
            self._on_mouse_down_event(global_pos, self.cursor_pos)
            btn_changed = True
        elif not is_lbutton_down and self.is_mouse_down:
            self._on_mouse_up_event()
            btn_changed = True
        elif is_lbutton_down and self.is_mouse_down and self.drawing_mode and self.ink_engine.is_drawing:
            self.ink_engine.extend_stroke(self.cursor_pos)

        # 4. Frame-rate-independent tap spring rebound
        spring_moving = False
        if not self.is_mouse_down and self.press_amount > 0.002:
            self.press_amount *= math.exp(-15.0 * dt)
            if self.press_amount < 0.002:
                self.press_amount = 0.0
            spring_moving = True

        # 5. Comic bubbles & click ripple lifecycle
        now = time.time()
        had_bubbles = len(self.comic_bubbles) > 0
        self.comic_bubbles = [b for b in self.comic_bubbles if now - b.created_at < b.duration]
        has_bubbles = len(self.comic_bubbles) > 0 or had_bubbles

        had_ripples = len(self.ripples) > 0
        self.ripples = [r for r in self.ripples if r.alive(now)]
        has_ripples = len(self.ripples) > 0 or had_ripples

        # 6. Conditional repaint: full 60fps when animating, zero idle churn
        if (
            cursor_moved
            or grip_moving
            or btn_changed
            or spring_moving
            or has_bubbles
            or has_ripples
            or self.ink_engine.has_active_strokes()
        ):
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        screen_w = float(self.width())
        screen_h = float(self.height())
        cursor = self.cursor_pos
        now = time.time()

        # 1. Spotlight vignette
        if self.spotlight_mode:
            self._draw_spotlight(painter, cursor, screen_w, screen_h)

        # 2. Vector ink strokes
        self.ink_engine.draw(painter)

        # 3. Click ripples
        if self.ripples:
            for ripple in self.ripples:
                if ripple.alive(now):
                    ripple.draw(painter, now)

        # 4. Comic tap bubbles
        if self.comic_bubbles:
            for bubble in self.comic_bubbles:
                bubble.draw(painter, now)

        # 5. Active pointer
        if self.pointer_visible:
            grip = QPointF(self.grip_x, screen_h + screen_h * 0.08)

            if self.current_style == "laser":
                CustomFunnyPointers.draw_laser_dot(
                    painter, cursor, self.press_amount, self.ink_engine.current_color, self.pointer_scale
                )
            elif self.current_style == "cat_paw":
                CustomFunnyPointers.draw_cat_paw(
                    painter, cursor, grip, self.press_amount, self.pointer_scale
                )
            elif self.current_style == "magic_wand":
                CustomFunnyPointers.draw_magic_wand(
                    painter, cursor, grip, self.press_amount, self.ink_engine.current_color, self.pointer_scale
                )
            elif self.current_style == "boxing_glove":
                CustomFunnyPointers.draw_boxing_glove(
                    painter, cursor, grip, self.press_amount, self.pointer_scale
                )
            elif self.current_style in self.hand_assets:
                self._draw_realistic_hand(
                    painter, self.hand_assets[self.current_style], cursor, grip, screen_h
                )

        painter.end()

    def _draw_spotlight(self, painter: QPainter, cursor: QPointF, screen_w: float, screen_h: float):
        spot_r = max(60.0, float(self.spotlight_radius)) * max(0.75, min(1.3, self.pointer_scale))
        dim_alpha = int(max(40, min(235, float(self.spotlight_dim) * 255.0)))
        edge_alpha = int(dim_alpha * 0.82)
        soft_alpha = int(dim_alpha * 0.18)

        spot_grad = QRadialGradient(cursor, spot_r * 1.45)
        spot_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        spot_grad.setColorAt(0.68, QColor(0, 0, 0, soft_alpha))
        spot_grad.setColorAt(0.88, QColor(0, 0, 0, edge_alpha))
        spot_grad.setColorAt(1.0, QColor(0, 0, 0, dim_alpha))

        painter.fillRect(QRectF(0, 0, screen_w, screen_h), QBrush(spot_grad))

        painter.setPen(QPen(QColor(255, 255, 255, 55), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(cursor, spot_r, spot_r)

    def _draw_realistic_hand(
        self,
        painter: QPainter,
        asset: HandAsset,
        cursor: QPointF,
        grip: QPointF,
        screen_h: float,
    ):
        if not asset.pixmap or asset.pixmap.isNull():
            return

        dx = cursor.x() - grip.x()
        dy = cursor.y() - grip.y()
        reach = math.hypot(dx, dy)
        aim_angle = math.atan2(dy, dx)

        hand_len_frac = 0.14 * self.pointer_scale
        hand_pts = hand_len_frac * screen_h * (1.0 - 0.06 * self.press_amount)

        span = max(0.01, asset.wrist - asset.hand_top)
        s = hand_pts / span
        width_pts = s * asset.aspect
        hand_tip_pts = (asset.wrist - asset.tip) * s
        tip_off_x = (asset.tip_x - asset.rod_x) * width_pts

        along = math.sqrt(max(0.0, reach * reach - tip_off_x * tip_off_x))
        rod_len = max(screen_h * 0.05, along - hand_tip_pts)

        # Align fingertip vector (tip_off_x, -(rod_len + hand_tip_pts)) directly onto aim_angle
        local_tip_angle = math.atan2(-(rod_len + hand_tip_pts), tip_off_x)
        rot_deg = math.degrees(aim_angle - local_tip_angle)

        rod_w = max(9.0, width_pts * 0.16)
        rod_rect = QRectF(-rod_w * 0.5, -rod_len, rod_w, rod_len)
        dest_rect = QRectF(-asset.rod_x * width_pts, -rod_len - hand_pts, width_pts, hand_pts)

        img_w = asset.pixmap.width()
        img_h = asset.pixmap.height()
        src_top = int(asset.hand_top * img_h)
        src_bot = int(asset.wrist * img_h)
        src_rect = QRectF(0, src_top, img_w, max(1, src_bot - src_top))

        painter.save()
        painter.translate(grip.x(), grip.y())
        painter.rotate(rot_deg)

        # 1. True silhouette drop shadow (never a crude rectangle)
        if self.show_shadow:
            shadow_dist = 14.0 - 8.0 * self.press_amount
            painter.save()
            painter.translate(shadow_dist * 0.65, shadow_dist)

            rod_shadow_path = QPainterPath()
            rod_shadow_path.addRoundedRect(rod_rect, rod_w * 0.5, rod_w * 0.5)
            painter.fillPath(rod_shadow_path, QColor(0, 0, 0, int(42 + 18 * self.press_amount)))

            if asset.shadow_pixmap and not asset.shadow_pixmap.isNull():
                painter.setOpacity(0.24 + 0.10 * self.press_amount)
                painter.drawPixmap(dest_rect, asset.shadow_pixmap, src_rect)
                painter.setOpacity(1.0)
            painter.restore()

        # 2. Telescopic metallic gradient rod
        rod_grad = QLinearGradient(-rod_w * 0.5, 0, rod_w * 0.5, 0)
        rod_grad.setColorAt(0.0, QColor("#18191D"))
        rod_grad.setColorAt(0.3, QColor("#565863"))
        rod_grad.setColorAt(0.65, QColor("#2B2C33"))
        rod_grad.setColorAt(1.0, QColor("#111215"))

        rod_path = QPainterPath()
        rod_path.addRoundedRect(rod_rect, rod_w * 0.5, rod_w * 0.5)
        painter.fillPath(rod_path, QBrush(rod_grad))
        painter.setPen(QPen(QColor("#3E404B"), 1.0))
        painter.drawPath(rod_path)

        # 3. High-DPI sliced hand artwork
        painter.drawPixmap(dest_rect, asset.pixmap, src_rect)

        painter.restore()
