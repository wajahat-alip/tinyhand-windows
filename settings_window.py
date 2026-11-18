# -*- coding: utf-8 -*-
"""
Settings Window for TinyHand Windows.
Clean, restrained dark-graphite utility interface inspired by native studio tools:
  - Minimal frameless window with crisp titlebar and single-line sidebar navigation
  - Elevated graphite surface groups (#1B1D23) with hairline dividers
  - Searchable 40+ Pointer Gallery (all 36 3D PNG hands + 4 vector FX + custom PNGs)
  - Live interactive preview canvas (hand kinematics, scaling, shadow, ink drawing,
    click ripples, comic pop bubbles, and cinema spotlight)
"""

import math
import os
import shutil
import time
from typing import Callable, Dict, List, Optional, Tuple

from PyQt6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QGuiApplication,
    QKeyEvent,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from hand_engine import HAND_CATALOG, CustomFunnyPointers, HandAsset
from icons import make_svg_icon
from ink_engine import InkEngine
from overlay_window import ClickRipple, ComicBubble

# ---------------------------------------------------------------------------
# Palette — Clean Warm-Neutral Graphite
# ---------------------------------------------------------------------------
C_WIN_BG = "#131418"       # outer window surface
C_SIDEBAR = "#101115"      # navigation rail background
C_CONTENT = "#16171C"      # main canvas background
C_SURFACE = "#1D1F26"      # grouped card surface
C_SURFACE_HOVER = "#242730"
C_CONTROL_BG = "#121318"   # recessed wells / segmented backings
C_ACCENT = "#3B82F6"       # single restrained Cobalt accent
C_ACCENT_LIGHT = "#60A5FA"
C_TEXT = "#F3F4F6"
C_TEXT_SEC = "#9CA3AF"
C_TEXT_MUTED = "#6B7280"
C_TRACK_OFF = "#2C2F3A"
C_DANGER = "#F87171"

SIZE_LABELS = ["XS", "S", "M", "L", "XL"]
SIZE_SCALES = [0.62, 0.80, 1.00, 1.22, 1.44]

FUNNY_POINTERS: List[Tuple[str, str, str]] = [
    ("cat_paw", "Cat Paw", "#FB7185"),
    ("magic_wand", "Magic Wand", "#38BDF8"),
    ("boxing_glove", "Boxing Glove", "#DC2626"),
    ("laser", "Laser Dot", "#EF4444"),
]

INK_SWATCHES: List[Tuple[str, str, str]] = [
    ("match", "Match Pointer", "#3B82F6"),
    ("rainbow", "Rainbow Cycle", "#FF6B6B"),
    ("coral", "Coral", "#EE4F98"),
    ("cyan", "Cyan", "#22D3EE"),
    ("blue", "Blue", "#3B82F6"),
    ("gold", "Gold", "#F59E0B"),
    ("emerald", "Green", "#10B981"),
    ("violet", "Violet", "#8B5CF6"),
    ("white", "White", "#F3F4F6"),
]

FADE_OPTIONS: List[Tuple[str, int]] = [("3s", 3), ("6s", 6), ("10s", 10), ("Keep", 0)]

SOUND_PRESETS: List[Tuple[str, str]] = [
    ("off", "Off"),
    ("boop", "Boop"),
    ("click", "Click"),
    ("pop", "Pop"),
    ("thock", "Thock"),
    ("wood", "Wood"),
    ("squeak", "Squeak"),
]

HOLD_KEY_OPTIONS: List[Tuple[str, str]] = [
    ("off", "Disabled"),
    ("shift", "Shift"),
    ("alt", "Alt"),
    ("ctrl", "Ctrl"),
]

HOTKEY_ROWS: List[Tuple[str, str]] = [
    ("hotkey_toggle", "Show / Hide Pointer"),
    ("hotkey_clear", "Clear Drawings"),
    ("hotkey_spotlight", "Toggle Spotlight"),
    ("hotkey_draw", "Toggle Draw Mode"),
]


# ---------------------------------------------------------------------------
# Artwork helpers: slice sharp hand thumbnails & render vector thumbs
# ---------------------------------------------------------------------------
def build_hand_thumb_pixmap(
    key: str,
    assets_dir: str,
    hand_assets: Optional[Dict[str, HandAsset]] = None,
    width: int = 76,
    height: int = 62,
) -> Optional[QPixmap]:
    """Build a crisp preview pixmap for any built-in, custom, or vector pointer."""
    dpr = 2
    pw, ph = width * dpr, height * dpr

    if key in ("cat_paw", "magic_wand", "boxing_glove", "laser"):
        pm = QPixmap(pw, ph)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.scale(dpr, dpr)
        cx, cy = width * 0.50, height * 0.25
        grip = QPointF(width * 0.64, height + 18.0)
        cursor = QPointF(cx, cy)
        if key == "cat_paw":
            CustomFunnyPointers.draw_cat_paw(p, cursor, grip, 0.12, 0.54)
        elif key == "magic_wand":
            CustomFunnyPointers.draw_magic_wand(p, cursor, grip, 0.30, QColor("#38BDF8"), 0.65)
        elif key == "boxing_glove":
            CustomFunnyPointers.draw_boxing_glove(p, cursor, grip, 0.12, 0.50)
        elif key == "laser":
            CustomFunnyPointers.draw_laser_dot(p, QPointF(width * 0.5, height * 0.5), 0.20, QColor("#EF4444"), 1.0)
        p.end()
        pm.setDevicePixelRatio(dpr)
        return pm

    asset = hand_assets.get(key) if hand_assets else None
    src_px = asset.pixmap if (asset and asset.pixmap and not asset.pixmap.isNull()) else None
    crop_bottom_frac = min(1.0, asset.wrist + 0.10) if asset else 0.62

    if src_px is None:
        stem = key[7:] if key.startswith("custom_") else key
        for fname in (f"hand_{key}.png", f"{key}.png", f"{stem}.png"):
            candidate = os.path.join(assets_dir, fname)
            if os.path.exists(candidate):
                loaded = QPixmap(candidate)
                if not loaded.isNull():
                    src_px = loaded
                    break

    if src_px is None or src_px.isNull():
        return None

    crop_h = max(1, int(src_px.height() * crop_bottom_frac))
    cropped = src_px.copy(0, 0, src_px.width(), crop_h)
    scaled = cropped.scaled(
        pw,
        ph,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    scaled.setDevicePixelRatio(dpr)
    return scaled


# ---------------------------------------------------------------------------
# Scroll & Typography Helpers
# ---------------------------------------------------------------------------
def _scroll_qss() -> str:
    return (
        f"QScrollArea {{ background: {C_CONTENT}; border: none; }}"
        "QScrollBar:vertical { background: transparent; width: 6px; margin: 4px 2px 4px 0; }"
        "QScrollBar::handle:vertical { background: rgba(255, 255, 255, 0.14); "
        "border-radius: 3px; min-height: 28px; }"
        "QScrollBar::handle:vertical:hover { background: rgba(255, 255, 255, 0.28); }"
        "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }"
    )


def _page_scroll() -> Tuple[QScrollArea, QWidget, QVBoxLayout]:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setStyleSheet(_scroll_qss())
    inner = QWidget()
    inner.setStyleSheet(f"background: {C_CONTENT};")
    vbox = QVBoxLayout(inner)
    vbox.setContentsMargins(24, 20, 22, 28)
    vbox.setSpacing(14)
    scroll.setWidget(inner)
    return scroll, inner, vbox


def _label(
    text: str,
    size: int = 12,
    color: str = C_TEXT,
    bold: bool = False,
    muted: bool = False,
) -> QLabel:
    lbl = QLabel(text)
    col = C_TEXT_MUTED if muted else color
    weight = "600" if bold else "400"
    lbl.setStyleSheet(
        f"color: {col}; font-size: {size}px; font-weight: {weight}; "
        "background: transparent; border: none; font-family: 'Segoe UI', sans-serif;"
    )
    return lbl


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {C_TEXT_SEC}; font-size: 12px; font-weight: 600; "
        "background: transparent; border: none; padding-top: 2px; "
        "font-family: 'Segoe UI', sans-serif;"
    )
    return lbl


def _add_hsep(layout: QVBoxLayout):
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setFixedHeight(1)
    sep.setStyleSheet("background: rgba(255, 255, 255, 0.05); border: none; margin: 2px 0;")
    layout.addWidget(sep)


# ===========================================================================
# Clean Custom Controls
# ===========================================================================
class NavRailButton(QWidget):
    """Quiet single-line sidebar navigation pill (clean linear/macOS style)."""

    clicked = pyqtSignal()

    def __init__(self, icon_key: str, label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.icon_key = icon_key
        self.label = label
        self._checked = False
        self._hovered = False
        self.setFixedHeight(36)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self._icon_active = make_svg_icon(icon_key, C_ACCENT_LIGHT, 15)
        self._icon_hover = make_svg_icon(icon_key, C_TEXT, 15)
        self._icon_idle = make_svg_icon(icon_key, C_TEXT_MUTED, 15)

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self.update()

    def isChecked(self) -> bool:
        return self._checked

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(10, 1, self.width() - 20, self.height() - 2)
        pill = QPainterPath()
        pill.addRoundedRect(rect, 8.0, 8.0)

        if self._checked:
            p.fillPath(pill, QColor("#21242D"))
            p.setPen(QPen(QColor(255, 255, 255, 14), 1.0))
            p.drawPath(pill)
        elif self._hovered:
            p.fillPath(pill, QColor(255, 255, 255, 9))

        icon = (
            self._icon_active
            if self._checked
            else (self._icon_hover if self._hovered else self._icon_idle)
        )
        icon.paint(p, QRect(21, int((self.height() - 15) * 0.5), 15, 15))

        txt_col = QColor("#FFFFFF") if self._checked else (QColor(C_TEXT) if self._hovered else QColor(C_TEXT_SEC))
        weight = QFont.Weight.DemiBold if self._checked else QFont.Weight.Medium
        p.setFont(QFont("Segoe UI", 9, weight))
        p.setPen(txt_col)
        p.drawText(
            QRectF(45, 0, self.width() - 56, self.height()),
            Qt.AlignmentFlag.AlignVCenter,
            self.label,
        )
        p.end()


class SettingsGroup(QWidget):
    """Elevated dark-graphite settings group card with clean hairline rim."""

    def __init__(self, body_layout, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_layout.setContentsMargins(16, 12, 16, 12)
        body.setLayout(body_layout)
        outer.addWidget(body)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 10.0, 10.0)
        p.fillPath(path, QColor(C_SURFACE))
        p.setPen(QPen(QColor(255, 255, 255, 16), 1.0))
        p.drawPath(path)
        p.end()


class CleanToggle(QWidget):
    """Crisp 38 x 22 px sliding switch (flat solid accent, zero neon halo)."""

    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._checked = bool(checked)
        self._knob_x = 27.0 if self._checked else 11.0
        self.setFixedSize(38, 22)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self._anim = QPropertyAnimation(self, b"knob_x", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _get_knob_x(self) -> float:
        return self._knob_x

    def _set_knob_x(self, v: float):
        self._knob_x = v
        self.update()

    knob_x = pyqtProperty(float, _get_knob_x, _set_knob_x)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, state: bool, silent: bool = False):
        state = bool(state)
        if state == self._checked:
            return
        self._checked = state
        self._anim.stop()
        self._anim.setStartValue(self._knob_x)
        self._anim.setEndValue(27.0 if state else 11.0)
        self._anim.start()
        if not silent:
            self.toggled.emit(state)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        track_r = QRectF(1.0, 1.5, 36.0, 19.0)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(C_ACCENT) if self._checked else QColor(C_TRACK_OFF))
        p.drawRoundedRect(track_r, 9.5, 9.5)

        p.setBrush(QColor("#FFFFFF") if self._checked else QColor("#D1D5DB"))
        p.drawEllipse(QPointF(self._knob_x, 11.0), 7.0, 7.0)
        p.end()


class CleanSlider(QWidget):
    """Refined 4 px track slider with solid Cobalt fill and crisp handle."""

    valueChanged = pyqtSignal(int)

    def __init__(
        self,
        minimum: int = 0,
        maximum: int = 100,
        value: int = 50,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._min = minimum
        self._max = maximum
        self._val = max(minimum, min(maximum, value))
        self._dragging = False
        self._hovered = False
        self.setFixedHeight(24)
        self.setMinimumWidth(120)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    @property
    def value(self) -> int:
        return self._val

    def setValue(self, v: int, silent: bool = False):
        v = max(self._min, min(self._max, v))
        if v != self._val:
            self._val = v
            self.update()
            if not silent:
                self.valueChanged.emit(self._val)

    def _ratio(self) -> float:
        rng = self._max - self._min
        return (self._val - self._min) / rng if rng else 0.0

    def _track_rect(self) -> QRectF:
        m = 8.0
        return QRectF(m, (self.height() - 4.0) * 0.5, self.width() - 2.0 * m, 4.0)

    def _thumb_x(self) -> float:
        t = self._track_rect()
        return t.left() + self._ratio() * t.width()

    def _x_to_val(self, x: float) -> int:
        t = self._track_rect()
        ratio = max(0.0, min(1.0, (x - t.left()) / max(1.0, t.width())))
        return self._min + round(ratio * (self._max - self._min))

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self.setValue(self._x_to_val(event.position().x()))

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.setValue(self._x_to_val(event.position().x()))

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = self._track_rect()
        tx = self._thumb_x()
        cy = self.height() * 0.5

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(C_TRACK_OFF))
        p.drawRoundedRect(t, 2.0, 2.0)

        if tx > t.left():
            p.setBrush(QColor(C_ACCENT))
            p.drawRoundedRect(QRectF(t.left(), t.top(), tx - t.left(), t.height()), 2.0, 2.0)

        # Subtle soft drop shadow under thumb
        p.setBrush(QColor(0, 0, 0, 80))
        p.drawEllipse(QPointF(tx, cy + 1.0), 7.5, 7.5)

        r = 7.0 if (self._dragging or self._hovered) else 6.2
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QPen(QColor(0, 0, 0, 50), 1.0))
        p.drawEllipse(QPointF(tx, cy), r, r)
        p.end()


class SegmentedControl(QWidget):
    """Understated segmented pill selector."""

    changed = pyqtSignal(object)

    def __init__(
        self,
        items: List[Tuple[str, object]],
        current_val: object = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._current = current_val if current_val is not None else items[0][1]
        self._buttons: List[Tuple[QPushButton, object]] = []
        self.setFixedHeight(32)

        hl = QHBoxLayout(self)
        hl.setContentsMargins(3, 3, 3, 3)
        hl.setSpacing(2)

        for label, val in items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(val == self._current)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(
                "QPushButton { background: transparent; color: #9CA3AF; border: none; "
                "border-radius: 6px; padding: 3px 11px; font-size: 11px; font-weight: 500; "
                "font-family: 'Segoe UI', sans-serif; }"
                "QPushButton:hover { color: #F3F4F6; }"
                "QPushButton:checked { background: #282B35; color: #FFFFFF; font-weight: 600; }"
            )
            btn.clicked.connect(lambda _c, v=val: self._select(v))
            self._buttons.append((btn, val))
            hl.addWidget(btn)

    def _select(self, val: object):
        self.setValue(val)
        self.changed.emit(val)

    def setValue(self, val: object):
        self._current = val
        for btn, bval in self._buttons:
            btn.setChecked(bval == val)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 8.0, 8.0)
        p.fillPath(path, QColor(C_CONTROL_BG))
        p.setPen(QPen(QColor(255, 255, 255, 14), 1.0))
        p.drawPath(path)
        p.end()


class InkSwatchButton(QWidget):
    """Circular ink color swatch with clean selection ring."""

    selected = pyqtSignal(str, str)

    def __init__(self, key: str, name: str, hex_color: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.name = name
        self.hex_color = hex_color
        self._checked = False
        self._hovered = False
        self.setFixedSize(32, 32)
        self.setToolTip(name)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def setChecked(self, state: bool):
        if self._checked != state:
            self._checked = state
            self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.key, self.hex_color)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        c = QPointF(self.width() * 0.5, self.height() * 0.5)

        if self._checked:
            p.setPen(QPen(QColor("#FFFFFF"), 1.8))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(c, 14.0, 14.0)
        elif self._hovered:
            p.setPen(QPen(QColor(255, 255, 255, 90), 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(c, 13.5, 13.5)

        p.setPen(QPen(QColor(255, 255, 255, 35), 1.0))
        if self.key == "rainbow":
            cg = QConicalGradient(c, 0)
            for pos, col in [
                (0.0, "#EF4444"), (0.17, "#F59E0B"), (0.33, "#22C55E"),
                (0.50, "#06B6D4"), (0.67, "#3B82F6"), (0.83, "#A855F7"), (1.0, "#EF4444")
            ]:
                cg.setColorAt(pos, QColor(col))
            p.setBrush(QBrush(cg))
        elif self.key == "match":
            lg = QLinearGradient(6, 6, 26, 26)
            lg.setColorAt(0.0, QColor("#EE4F98"))
            lg.setColorAt(0.5, QColor("#3B82F6"))
            lg.setColorAt(1.0, QColor("#10B981"))
            p.setBrush(QBrush(lg))
        else:
            p.setBrush(QColor(self.hex_color))
        p.drawEllipse(c, 10.5, 10.5)

        if self.key == "match":
            p.setPen(QColor("#FFFFFF"))
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "A")
        p.end()


class PointerThumb(QWidget):
    """Clean 88 x 102 pointer tile displaying cropped 3D hand or vector art."""

    selected_signal = pyqtSignal(str)

    def __init__(
        self,
        key: str,
        name: str,
        category: str,
        assets_dir: str,
        hand_assets: Optional[Dict[str, HandAsset]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.key = key
        self.name = name
        self.category = category
        self._selected = False
        self._hovered = False
        self.setFixedSize(88, 102)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 7, 6, 6)
        layout.setSpacing(4)

        self._img_label = QLabel()
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setFixedSize(76, 62)
        self._img_label.setStyleSheet("background: transparent;")
        layout.addWidget(self._img_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self._pixmap = build_hand_thumb_pixmap(key, assets_dir, hand_assets, 76, 62)
        if self._pixmap and not self._pixmap.isNull():
            self._img_label.setPixmap(self._pixmap)
        else:
            self._img_label.setPixmap(make_svg_icon("hand", C_ACCENT_LIGHT, 28).pixmap(QSize(28, 28)))

        self._name_lbl = QLabel(name)
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_lbl.setWordWrap(True)
        self._name_lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 500; color: {C_TEXT_SEC}; "
            "background: transparent; font-family: 'Segoe UI', sans-serif;"
        )
        layout.addWidget(self._name_lbl)

    def setSelected(self, state: bool):
        self._selected = state
        self._name_lbl.setStyleSheet(
            f"font-size: 10px; font-weight: {'600' if state else '500'}; "
            f"color: {'#FFFFFF' if state else C_TEXT_SEC}; "
            "background: transparent; font-family: 'Segoe UI', sans-serif;"
        )
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected_signal.emit(self.key)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 10.0, 10.0)

        if self._selected:
            p.fillPath(path, QColor(59, 130, 246, 36))
            p.setPen(QPen(QColor(C_ACCENT), 1.6))
            p.drawPath(path)
        elif self._hovered:
            p.fillPath(path, QColor(C_SURFACE_HOVER))
            p.setPen(QPen(QColor(255, 255, 255, 34), 1.0))
            p.drawPath(path)
        else:
            p.fillPath(path, QColor(C_SURFACE))
            p.setPen(QPen(QColor(255, 255, 255, 14), 1.0))
            p.drawPath(path)
        p.end()


class SoundTile(QWidget):
    """88 x 68 sound preset tile with clean selected state."""

    clicked_signal = pyqtSignal(str)

    def __init__(self, key: str, label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.key = key
        self._selected = False
        self._hovered = False
        self.setFixedSize(88, 68)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 10, 4, 8)
        layout.setSpacing(5)

        self._icon_name = "sound_off" if key == "off" else "sound_on"
        self._icon_lbl = QLabel()
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setStyleSheet("background: transparent;")
        layout.addWidget(self._icon_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        self._name_lbl = QLabel(label)
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._name_lbl)
        self._refresh_visuals()

    def _refresh_visuals(self):
        icon_col = C_ACCENT_LIGHT if self._selected else (C_TEXT if self._hovered else C_TEXT_MUTED)
        self._icon_lbl.setPixmap(make_svg_icon(self._icon_name, icon_col, 19).pixmap(QSize(19, 19)))
        txt_col = "#FFFFFF" if self._selected else (C_TEXT if self._hovered else C_TEXT_SEC)
        weight = "600" if self._selected else "500"
        self._name_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: {weight}; color: {txt_col}; "
            "background: transparent; font-family: 'Segoe UI', sans-serif;"
        )

    def setSelected(self, state: bool):
        if self._selected != state:
            self._selected = state
            self._refresh_visuals()
            self.update()

    def enterEvent(self, event):
        self._hovered = True
        self._refresh_visuals()
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self._refresh_visuals()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked_signal.emit(self.key)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 9.0, 9.0)

        if self._selected:
            p.fillPath(path, QColor(59, 130, 246, 36))
            p.setPen(QPen(QColor(C_ACCENT), 1.5))
        elif self._hovered:
            p.fillPath(path, QColor(C_SURFACE_HOVER))
            p.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
        else:
            p.fillPath(path, QColor(C_CONTROL_BG))
            p.setPen(QPen(QColor(255, 255, 255, 14), 1.0))
        p.drawPath(path)
        p.end()


class HotkeyButton(QPushButton):
    """Click-to-record hotkey pill button."""

    hotkeyChanged = pyqtSignal(str)

    def __init__(self, current: str = "", parent=None):
        super().__init__(parent)
        self._current = current
        self._recording = False
        self._update_text()
        self.clicked.connect(self._start_recording)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet(self._base_qss())
        self.setFixedHeight(28)
        self.setMinimumWidth(124)

    @staticmethod
    def _base_qss() -> str:
        return (
            f"QPushButton {{ background: {C_CONTROL_BG}; color: {C_TEXT}; "
            "  border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 6px; "
            "  font-size: 11px; font-weight: 500; padding: 3px 10px; font-family: 'Segoe UI'; }}"
            "QPushButton:hover { border-color: rgba(255, 255, 255, 0.25); background: #232630; }"
        )

    @staticmethod
    def _record_qss() -> str:
        return (
            f"QPushButton {{ background: rgba(59, 130, 246, 0.20); color: #FFFFFF; "
            f"  border: 1.5px solid {C_ACCENT}; border-radius: 6px; "
            "  font-size: 11px; font-weight: 600; padding: 3px 10px; font-family: 'Segoe UI'; }}"
        )

    def _update_text(self):
        self.setText(self._current.upper() if self._current else "None")

    def _start_recording(self):
        self._recording = True
        self.setText("Press keys...")
        self.setStyleSheet(self._record_qss())
        self.grabKeyboard()

    def keyPressEvent(self, event: QKeyEvent):
        if not self._recording:
            return super().keyPressEvent(event)
        if event.key() == Qt.Key.Key_Escape:
            self._recording = False
            self._update_text()
            self.setStyleSheet(self._base_qss())
            self.releaseKeyboard()
            return
        if event.key() in (
            Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift, Qt.Key.Key_Meta
        ):
            return

        mods = []
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            mods.append("ctrl")
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            mods.append("alt")
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            mods.append("shift")

        key_name = QKeySequence(event.key()).toString().lower().strip()
        if not key_name:
            return
        self._current = "+".join(mods + [key_name]) if mods else key_name
        self._recording = False
        self._update_text()
        self.setStyleSheet(self._base_qss())
        self.releaseKeyboard()
        self.hotkeyChanged.emit(self._current)


# ===========================================================================
# Live Interactive Preview Stage (Refined Graphite Studio Canvas)
# ===========================================================================
class LivePreviewStage(QWidget):
    """Interactive dot-grid stage showing live hand kinematics, ink, bubbles & spotlight."""

    def __init__(
        self,
        assets_dir: str,
        hand_assets: Optional[Dict[str, HandAsset]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.assets_dir = assets_dir
        self.hand_assets: Dict[str, HandAsset] = hand_assets if hand_assets is not None else {}
        self.setFixedSize(280, 316)
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        self.pointer_key: str = "coral"
        self.scale: float = 1.0
        self.show_shadow: bool = True
        self.show_bubbles: bool = True
        self.comic_word_pack: str = "funny"
        self.show_ripple: bool = True
        self.draw_enabled: bool = True
        self.spotlight_preview: bool = False
        self.spotlight_radius: float = 160.0
        self.spotlight_dim: float = 0.60

        self.ink_engine = InkEngine()
        self.ink_engine.stroke_width = 4.5
        self.ink_engine.fade_duration = 5.0

        self._mouse_inside = False
        self._cx: float = 140.0
        self._cy: float = 135.0
        self._grip_x: float = 200.0
        self._angle: float = 0.0
        self._press_amount: float = 0.0
        self._is_dragging: bool = False
        self._ripples: List[ClickRipple] = []
        self._bubbles: List[ComicBubble] = []

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def trigger_tap(self, x: Optional[float] = None, y: Optional[float] = None):
        px = self._cx if x is None else x
        py = self._cy if y is None else y
        self._press_amount = 1.0
        if self.show_ripple:
            self._ripples.append(ClickRipple(px, py, self.ink_engine.current_color))
        if self.show_bubbles and self.pointer_key != "laser":
            self._bubbles.append(
                ComicBubble(px, py, self.ink_engine.current_color, self.comic_word_pack)
            )
        self.update()

    def clear_ink(self):
        self.ink_engine.clear()
        self.update()

    def set_pointer(self, key: str, color: Optional[QColor] = None):
        self.pointer_key = key
        if color is not None:
            self.ink_engine.current_color = color
        self.update()

    def set_scale_index(self, idx: int):
        self.scale = SIZE_SCALES[max(0, min(len(SIZE_SCALES) - 1, idx))]
        self.update()

    def enterEvent(self, event):
        self._mouse_inside = True

    def leaveEvent(self, event):
        self._mouse_inside = False
        if self._is_dragging:
            self._is_dragging = False
            self.ink_engine.end_stroke()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            self._cx = max(24.0, min(self.width() - 24.0, pos.x()))
            self._cy = max(20.0, min(self.height() - 20.0, pos.y()))
            self.trigger_tap(self._cx, self._cy)
            if self.draw_enabled:
                self._is_dragging = True
                self.ink_engine.begin_stroke(QPointF(self._cx, self._cy))

    def mouseMoveEvent(self, event):
        pos = event.position()
        self._cx = max(14.0, min(self.width() - 14.0, pos.x()))
        self._cy = max(14.0, min(self.height() - 14.0, pos.y()))
        if self._is_dragging and self.draw_enabled and self.ink_engine.is_drawing:
            self.ink_engine.extend_stroke(QPointF(self._cx, self._cy))
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False
            self.ink_engine.end_stroke()

    def _tick(self):
        if not self._mouse_inside:
            self._angle += 0.030
            tx = self.width() * 0.5 + 54.0 * math.sin(self._angle)
            ty = self.height() * 0.42 + 30.0 * math.sin(self._angle * 2.0)
            self._cx += (tx - self._cx) * 0.14
            self._cy += (ty - self._cy) * 0.14

        target_gx = min(max(self._cx + 68.0, self.width() * 0.25), self.width() * 0.96)
        self._grip_x += (target_gx - self._grip_x) * 0.16

        if not self._is_dragging and self._press_amount > 0.002:
            self._press_amount *= 0.80
            if self._press_amount < 0.002:
                self._press_amount = 0.0

        now = time.time()
        self._ripples = [r for r in self._ripples if r.alive(now)]
        self._bubbles = [b for b in self._bubbles if now - b.created_at < b.duration]
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        w, h = float(self.width()), float(self.height())
        outer_rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        clip_path = QPainterPath()
        clip_path.addRoundedRect(outer_rect, 11.0, 11.0)
        p.setClipPath(clip_path)

        # Neutral studio canvas + fine dot grid
        p.fillRect(self.rect(), QColor("#0E0F13"))
        p.setPen(QPen(QColor(255, 255, 255, 16), 1.5))
        for gx in range(14, int(w), 18):
            for gy in range(14, int(h), 18):
                p.drawPoint(gx, gy)

        self.ink_engine.draw(p)

        cursor = QPointF(self._cx, self._cy)
        if self.spotlight_preview:
            spot_r = max(32.0, (self.spotlight_radius / 3.4) * max(0.75, min(1.3, self.scale)))
            dim_a = int(max(45, min(230, self.spotlight_dim * 255.0)))
            sg = QRadialGradient(cursor, spot_r * 1.45)
            sg.setColorAt(0.0, QColor(0, 0, 0, 0))
            sg.setColorAt(0.68, QColor(0, 0, 0, int(dim_a * 0.2)))
            sg.setColorAt(0.90, QColor(0, 0, 0, int(dim_a * 0.85)))
            sg.setColorAt(1.0, QColor(0, 0, 0, dim_a))
            p.fillRect(self.rect(), QBrush(sg))
            p.setPen(QPen(QColor(255, 255, 255, 65), 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(cursor, spot_r, spot_r)

        now = time.time()
        for rp in self._ripples:
            rp.draw(p, now)
        for bub in self._bubbles:
            bub.draw(p, now)

        grip = QPointF(self._grip_x, h + 24.0)
        if self.pointer_key == "laser":
            CustomFunnyPointers.draw_laser_dot(
                p, cursor, self._press_amount, self.ink_engine.current_color, self.scale * 0.9
            )
        elif self.pointer_key == "cat_paw":
            CustomFunnyPointers.draw_cat_paw(p, cursor, grip, self._press_amount, self.scale * 0.72)
        elif self.pointer_key == "magic_wand":
            CustomFunnyPointers.draw_magic_wand(
                p, cursor, grip, self._press_amount, self.ink_engine.current_color, self.scale * 0.78
            )
        elif self.pointer_key == "boxing_glove":
            CustomFunnyPointers.draw_boxing_glove(p, cursor, grip, self._press_amount, self.scale * 0.68)
        else:
            asset = self._resolve_asset(self.pointer_key)
            if asset:
                self._draw_stage_hand(p, asset, cursor, grip, h)

        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(clip_path)
        p.end()

    def _resolve_asset(self, key: str) -> Optional[HandAsset]:
        if key in self.hand_assets:
            return self.hand_assets[key]
        path = os.path.join(self.assets_dir, f"hand_{key}.png")
        if os.path.exists(path):
            asset = HandAsset(key, path)
            self.hand_assets[key] = asset
            return asset
        return None

    def _draw_stage_hand(
        self,
        painter: QPainter,
        asset: HandAsset,
        cursor: QPointF,
        grip: QPointF,
        stage_h: float,
    ):
        if not asset.pixmap or asset.pixmap.isNull():
            return

        dx = cursor.x() - grip.x()
        dy = cursor.y() - grip.y()
        reach = math.hypot(dx, dy)
        aim_angle = math.atan2(dy, dx)

        ref_h = max(stage_h, 390.0)
        hand_pts = 0.145 * ref_h * self.scale * (1.0 - 0.06 * self._press_amount)
        span = max(0.01, asset.wrist - asset.hand_top)
        s = hand_pts / span
        width_pts = s * asset.aspect
        hand_tip_pts = (asset.wrist - asset.tip) * s
        tip_off_x = (asset.tip_x - asset.rod_x) * width_pts

        along = math.sqrt(max(0.0, reach * reach - tip_off_x * tip_off_x))
        rod_len = max(24.0, along - hand_tip_pts)
        local_tip_angle = math.atan2(-(rod_len + hand_tip_pts), tip_off_x)
        rot_deg = math.degrees(aim_angle - local_tip_angle)

        rod_w = max(5.5, width_pts * 0.16)
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

        if self.show_shadow:
            sdist = 9.0 - 5.0 * self._press_amount
            painter.save()
            painter.translate(sdist * 0.65, sdist)
            rp = QPainterPath()
            rp.addRoundedRect(rod_rect, rod_w * 0.5, rod_w * 0.5)
            painter.fillPath(rp, QColor(0, 0, 0, 55))
            if asset.shadow_pixmap and not asset.shadow_pixmap.isNull():
                painter.setOpacity(0.32 + 0.10 * self._press_amount)
                painter.drawPixmap(dest_rect, asset.shadow_pixmap, src_rect)
                painter.setOpacity(1.0)
            painter.restore()

        rod_grad = QLinearGradient(-rod_w * 0.5, 0, rod_w * 0.5, 0)
        rod_grad.setColorAt(0.0, QColor("#18191D"))
        rod_grad.setColorAt(0.3, QColor("#5A5D68"))
        rod_grad.setColorAt(0.65, QColor("#2B2C33"))
        rod_grad.setColorAt(1.0, QColor("#111215"))
        rod_path = QPainterPath()
        rod_path.addRoundedRect(rod_rect, rod_w * 0.5, rod_w * 0.5)
        painter.fillPath(rod_path, QBrush(rod_grad))
        painter.setPen(QPen(QColor("#3E404B"), 0.8))
        painter.drawPath(rod_path)

        painter.drawPixmap(dest_rect, asset.pixmap, src_rect)
        painter.restore()

    def cleanup(self):
        self._timer.stop()


# ===========================================================================
# Helper row builders
# ===========================================================================
def _toggle_row(
    label: str,
    sublabel: str = "",
    checked: bool = False,
) -> Tuple[QWidget, CleanToggle]:
    row = QWidget()
    row.setStyleSheet("background: transparent;")
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 4, 0, 4)
    hl.setSpacing(12)

    col = QVBoxLayout()
    col.setSpacing(2)
    col.addWidget(_label(label, 12, C_TEXT, bold=True))
    if sublabel:
        sub = _label(sublabel, 11, C_TEXT_MUTED)
        sub.setWordWrap(True)
        col.addWidget(sub)
    hl.addLayout(col, 1)

    toggle = CleanToggle(checked)
    hl.addWidget(toggle, 0, Qt.AlignmentFlag.AlignVCenter)
    return row, toggle


def _slider_row(
    label: str,
    sublabel: str = "",
    lo: int = 0,
    hi: int = 100,
    val: int = 50,
) -> Tuple[QWidget, CleanSlider, QLabel]:
    row = QWidget()
    row.setStyleSheet("background: transparent;")
    vl = QVBoxLayout(row)
    vl.setContentsMargins(0, 2, 0, 2)
    vl.setSpacing(5)

    top = QHBoxLayout()
    top.setContentsMargins(0, 0, 0, 0)
    top.setSpacing(8)
    top.addWidget(_label(label, 12, C_TEXT, bold=True))
    if sublabel:
        top.addWidget(_label(sublabel, 11, C_TEXT_MUTED))
    top.addStretch()
    val_lbl = _label(str(val), 12, color=C_TEXT_SEC, bold=True)
    top.addWidget(val_lbl)
    vl.addLayout(top)

    slider = CleanSlider(lo, hi, val)
    vl.addWidget(slider)
    return row, slider, val_lbl


def _button(text: str, primary: bool = False, danger: bool = False) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    if danger:
        btn.setStyleSheet(
            "QPushButton { background: rgba(248, 113, 113, 0.12); color: #FCA5A5; "
            "  border: 1px solid rgba(248, 113, 113, 0.28); border-radius: 7px; "
            "  padding: 7px 14px; font-weight: 600; font-size: 12px; font-family: 'Segoe UI'; }"
            "QPushButton:hover { background: rgba(248, 113, 113, 0.22); color: #FFFFFF; }"
        )
    elif primary:
        btn.setStyleSheet(
            f"QPushButton {{ background: {C_ACCENT}; color: #FFFFFF; border: none; "
            "  border-radius: 7px; padding: 7px 14px; font-weight: 600; "
            "  font-size: 12px; font-family: 'Segoe UI'; }}"
            f"QPushButton:hover {{ background: #2563EB; }}"
        )
    else:
        btn.setStyleSheet(
            "QPushButton { background: #252832; color: #E5E7EB; "
            "  border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 7px; "
            "  padding: 7px 14px; font-weight: 500; font-size: 12px; font-family: 'Segoe UI'; }}"
            "QPushButton:hover { background: #2E323F; color: #FFFFFF; }"
        )
    return btn


# ===========================================================================
# Main Window: SettingsWindow
# ===========================================================================
class SettingsWindow(QWidget):
    """Clean dark-graphite Settings Window for TinyHand Windows."""

    WIN_W, WIN_H = 1000, 640
    SIDEBAR_W = 192
    PREVIEW_DOCK_W = 308

    def __init__(
        self,
        config,
        overlay,
        hud,
        sound_engine,
        ink_engine,
        input_hook=None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.config = config
        self.overlay = overlay
        self.hud = hud
        self.sound_engine = sound_engine
        self.ink_engine = ink_engine
        self.input_hook = input_hook

        fallback_dir = os.path.dirname(os.path.abspath(__file__))
        self.app_dir = config.app_dir if config else fallback_dir
        self.assets_dir = overlay.assets_dir if overlay else os.path.join(fallback_dir, "assets")
        self.custom_hands_dir = os.path.join(self.app_dir, "custom_hands")
        self.custom_sounds_dir = os.path.join(self.app_dir, "custom_sounds")

        self._drag_pos: Optional[QPoint] = None
        self._nav_items: List[NavRailButton] = []
        self._pointer_thumbs: List[PointerThumb] = []
        self._sound_tiles: List[SoundTile] = []
        self._swatch_btns: Dict[str, InkSwatchButton] = {}
        self._pointer_grid_layout: Optional[QGridLayout] = None
        self._pointer_category = "all"
        self._pointer_search = ""

        self.setFixedSize(self.WIN_W, self.WIN_H)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(44)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 195))
        self.setGraphicsEffect(shadow)

        self._build_ui()
        self._sync_preview_from_state()
        self._center_on_screen()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        outer = QRectF(1.0, 1.0, self.WIN_W - 2.0, self.WIN_H - 2.0)
        path = QPainterPath()
        path.addRoundedRect(outer, 13.0, 13.0)
        p.fillPath(path, QColor(C_WIN_BG))
        p.setPen(QPen(QColor(255, 255, 255, 24), 1.0))
        p.drawPath(path)
        p.end()

    def _center_on_screen(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.center().x() - self.WIN_W // 2,
                geo.center().y() - self.WIN_H // 2,
            )

    # ------------------------------------------------------------------
    # Shell Layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        shell = QVBoxLayout(self)
        shell.setContentsMargins(1, 1, 1, 1)
        shell.setSpacing(0)

        shell.addWidget(self._build_title_bar())

        hdiv = QWidget()
        hdiv.setFixedHeight(1)
        hdiv.setStyleSheet("background: rgba(255, 255, 255, 0.06);")
        shell.addWidget(hdiv)

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_hl = QHBoxLayout(body)
        body_hl.setContentsMargins(0, 0, 0, 0)
        body_hl.setSpacing(0)

        body_hl.addWidget(self._build_sidebar())

        vdiv1 = QWidget()
        vdiv1.setFixedWidth(1)
        vdiv1.setStyleSheet("background: rgba(255, 255, 255, 0.06);")
        body_hl.addWidget(vdiv1)

        self._stack = self._build_pages()
        body_hl.addWidget(self._stack, 1)

        self._preview_divider = QWidget()
        self._preview_divider.setFixedWidth(1)
        self._preview_divider.setStyleSheet("background: rgba(255, 255, 255, 0.06);")
        body_hl.addWidget(self._preview_divider)

        self._preview_dock = self._build_preview_dock()
        body_hl.addWidget(self._preview_dock)

        shell.addWidget(body, 1)

    # ------------------------------------------------------------------
    # Clean Minimal Titlebar (No gimmicks or extra badges)
    # ------------------------------------------------------------------
    def _build_title_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(16, 0, 12, 0)
        hl.setSpacing(10)

        badge = QLabel()
        badge.setFixedSize(24, 24)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setPixmap(make_svg_icon("hand", "#FFFFFF", 13).pixmap(QSize(13, 13)))
        badge.setStyleSheet(f"background: {C_ACCENT}; border-radius: 6px;")
        hl.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)

        hl.addWidget(_label("TinyHand Windows", 13, C_TEXT, bold=True), 0, Qt.AlignmentFlag.AlignVCenter)
        hl.addStretch()

        btn_min = QPushButton()
        btn_min.setFixedSize(30, 26)
        btn_min.setIcon(make_svg_icon("minimize", "#9CA3AF", 12))
        btn_min.setIconSize(QSize(12, 12))
        btn_min.setToolTip("Minimize")
        btn_min.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_min.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 6px; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.08); }"
        )
        btn_min.clicked.connect(self.showMinimized)
        hl.addWidget(btn_min, 0, Qt.AlignmentFlag.AlignVCenter)

        btn_close = QPushButton()
        btn_close.setFixedSize(30, 26)
        btn_close.setIcon(make_svg_icon("close", "#9CA3AF", 12))
        btn_close.setIconSize(QSize(12, 12))
        btn_close.setToolTip("Close")
        btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 6px; }"
            "QPushButton:hover { background: rgba(239, 68, 68, 0.72); }"
        )
        btn_close.clicked.connect(self.hide)
        hl.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignVCenter)

        return bar

    # ------------------------------------------------------------------
    # Left Navigation Rail
    # ------------------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        sb = QWidget()
        sb.setFixedWidth(self.SIDEBAR_W)
        sb.setStyleSheet(f"background: {C_SIDEBAR}; border-bottom-left-radius: 13px;")

        vl = QVBoxLayout(sb)
        vl.setContentsMargins(0, 14, 0, 14)
        vl.setSpacing(3)

        nav_defs = [
            ("settings", "General"),
            ("hand", "Pointers"),
            ("spotlight", "Style & FX"),
            ("pen", "Ink & Draw"),
            ("sound_on", "Sound"),
            ("info", "About"),
        ]
        for idx, (icon_key, title) in enumerate(nav_defs):
            item = NavRailButton(icon_key, title)
            item.setChecked(idx == 0)
            item.clicked.connect(lambda i=idx: self._switch_page(i))
            self._nav_items.append(item)
            vl.addWidget(item)

        vl.addStretch()

        ver_wrap = QHBoxLayout()
        ver_wrap.setContentsMargins(20, 0, 16, 0)
        ver_wrap.addWidget(_label("Version 1.0.0", 11, muted=True))
        vl.addLayout(ver_wrap)

        return sb

    # ------------------------------------------------------------------
    # Right Dock: Calm Live Preview
    # ------------------------------------------------------------------
    def _build_preview_dock(self) -> QWidget:
        dock = QWidget()
        dock.setFixedWidth(self.PREVIEW_DOCK_W)
        dock.setStyleSheet(f"background: {C_SIDEBAR}; border-bottom-right-radius: 13px;")

        vl = QVBoxLayout(dock)
        vl.setContentsMargins(14, 18, 14, 16)
        vl.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(2, 0, 2, 0)
        hdr.addWidget(_label("Preview", 12, C_TEXT_SEC, bold=True))
        hdr.addStretch()
        hdr.addWidget(_label("Click or drag", 11, muted=True))
        vl.addLayout(hdr)

        self._preview = LivePreviewStage(self.assets_dir, self.overlay.hand_assets)
        vl.addWidget(self._preview, 0, Qt.AlignmentFlag.AlignHCenter)

        # Clean 4-button action strip
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(6)

        self._pg_btn_draw = self._mini_ctrl_btn("Draw", "pen", checkable=True, checked=True)
        self._pg_btn_draw.toggled.connect(lambda on: setattr(self._preview, "draw_enabled", on))
        ctrl_row.addWidget(self._pg_btn_draw)

        self._pg_btn_spot = self._mini_ctrl_btn("Spot", "spotlight", checkable=True, checked=False)
        self._pg_btn_spot.toggled.connect(lambda on: setattr(self._preview, "spotlight_preview", on))
        ctrl_row.addWidget(self._pg_btn_spot)

        btn_tap = self._mini_ctrl_btn("Tap", "pops", checkable=False)
        btn_tap.clicked.connect(lambda: self._preview.trigger_tap())
        ctrl_row.addWidget(btn_tap)

        btn_clr = self._mini_ctrl_btn("Clear", "clear", checkable=False)
        btn_clr.clicked.connect(self._preview.clear_ink)
        ctrl_row.addWidget(btn_clr)

        vl.addLayout(ctrl_row)

        # Compact understated active pointer note
        summary_wrap = QWidget()
        summary_wrap.setObjectName("PreviewSummaryPill")
        summary_wrap.setStyleSheet(
            f"#PreviewSummaryPill {{ background: {C_SURFACE}; "
            "border: 1px solid rgba(255,255,255,0.06); border-radius: 9px; }"
        )
        sum_vl = QVBoxLayout(summary_wrap)
        sum_vl.setContentsMargins(12, 9, 12, 9)
        sum_vl.setSpacing(3)
        self._spec_pointer_lbl = _label("Coral Vinyl  ·  Size M", 12, C_TEXT, bold=True)
        self._spec_meta_lbl = _label("Match ink  ·  Shadow on", 11, C_TEXT_MUTED)
        sum_vl.addWidget(self._spec_pointer_lbl)
        sum_vl.addWidget(self._spec_meta_lbl)
        vl.addWidget(summary_wrap)

        vl.addStretch()
        return dock

    @staticmethod
    def _mini_ctrl_btn(
        text: str,
        icon_name: str,
        checkable: bool = False,
        checked: bool = False,
    ) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(checkable)
        if checkable:
            btn.setChecked(checked)
        btn.setIcon(make_svg_icon(icon_name, "#D1D5DB", 12))
        btn.setIconSize(QSize(12, 12))
        btn.setFixedHeight(29)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(
            f"QPushButton {{ background: {C_SURFACE}; color: #D1D5DB; "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 7px; "
            "padding: 3px 8px; font-size: 11px; font-weight: 500; font-family: 'Segoe UI'; }"
            "QPushButton:hover { background: #262933; color: #FFFFFF; }"
            f"QPushButton:checked {{ background: rgba(59,130,246,0.22); color: {C_ACCENT_LIGHT}; "
            f"border-color: rgba(59,130,246,0.55); font-weight: 600; }}"
        )
        return btn

    # ------------------------------------------------------------------
    # Pages Stack
    # ------------------------------------------------------------------
    def _build_pages(self) -> QStackedWidget:
        stack = QStackedWidget()
        stack.setStyleSheet(f"background: {C_CONTENT};")
        stack.addWidget(self._page_general())
        stack.addWidget(self._page_pointers())
        stack.addWidget(self._page_style_fx())
        stack.addWidget(self._page_ink())
        stack.addWidget(self._page_sound())
        stack.addWidget(self._page_about())
        return stack

    def _switch_page(self, idx: int):
        self._stack.setCurrentIndex(idx)
        for i, item in enumerate(self._nav_items):
            item.setChecked(i == idx)
        show_preview = idx != 5
        self._preview_dock.setVisible(show_preview)
        self._preview_divider.setVisible(show_preview)

    # ==================================================================
    # Page 0: General (Shortcuts, Modifier Key & Startup)
    # ==================================================================
    def _page_general(self) -> QScrollArea:
        scroll, _inner, vbox = _page_scroll()
        vbox.addWidget(_label("General", 18, C_TEXT, bold=True))

        # Shortcuts
        vbox.addWidget(_section_label("Shortcuts"))
        hk_body = QVBoxLayout()
        hk_body.setSpacing(6)
        for i, (cfg_key, lbl_txt) in enumerate(HOTKEY_ROWS):
            hk_row = QHBoxLayout()
            hk_row.setContentsMargins(0, 3, 0, 3)
            hk_row.addWidget(_label(lbl_txt, 12, C_TEXT))
            hk_row.addStretch()
            hk_btn = HotkeyButton(self.config.get(cfg_key, ""))
            hk_btn.hotkeyChanged.connect(lambda v, k=cfg_key: self._on_hotkey_changed(k, v))
            hk_row.addWidget(hk_btn)
            hk_body.addLayout(hk_row)
            if i < len(HOTKEY_ROWS) - 1:
                _add_hsep(hk_body)
        vbox.addWidget(SettingsGroup(hk_body))

        # Hold-to-Draw Key
        vbox.addWidget(_section_label("Quick Draw"))
        draw_body = QVBoxLayout()
        draw_body.setSpacing(6)

        hd_hl = QHBoxLayout()
        hd_hl.setContentsMargins(0, 2, 0, 2)
        hd_col = QVBoxLayout()
        hd_col.setSpacing(2)
        hd_col.addWidget(_label("Hold-to-Draw Key", 12, C_TEXT, bold=True))
        hd_sub = _label("Hold while dragging to draw without Draw mode", 11, C_TEXT_MUTED)
        hd_sub.setWordWrap(True)
        hd_col.addWidget(hd_sub)
        hd_hl.addLayout(hd_col, 1)

        hd_combo = QComboBox()
        hd_combo.setFixedWidth(124)
        hd_combo.setStyleSheet(self._combo_qss())
        cur_hd = self.config.get("hold_to_draw_key", "shift") or "off"
        for k, disp in HOLD_KEY_OPTIONS:
            hd_combo.addItem(disp, k)
        idx = hd_combo.findData(cur_hd)
        if idx >= 0:
            hd_combo.setCurrentIndex(idx)
        hd_combo.currentIndexChanged.connect(lambda _i: self._on_hold_key_changed(hd_combo.currentData()))
        hd_hl.addWidget(hd_combo, 0, Qt.AlignmentFlag.AlignVCenter)
        draw_body.addLayout(hd_hl)
        vbox.addWidget(SettingsGroup(draw_body))

        # Startup
        vbox.addWidget(_section_label("Startup"))
        st_body = QVBoxLayout()
        st_body.setSpacing(6)
        startup_on = (
            self.config.get_launch_at_startup_state()
            if hasattr(self.config, "get_launch_at_startup_state")
            else False
        )
        st_row, st_toggle = _toggle_row(
            "Open TinyHand PRO when you sign in",
            "Start silently in the system tray on Windows boot",
            startup_on,
        )
        st_toggle.toggled.connect(
            lambda v: self.config.set_launch_at_startup(v)
            if hasattr(self.config, "set_launch_at_startup")
            else None
        )
        st_body.addWidget(st_row)
        vbox.addWidget(SettingsGroup(st_body))

        vbox.addStretch()
        return scroll

    # ==================================================================
    # Page 1: Pointers
    # ==================================================================
    def _page_pointers(self) -> QScrollArea:
        scroll, _inner, vbox = _page_scroll()

        vbox.addWidget(_label("Pointers", 18, C_TEXT, bold=True))

        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search pointers...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setFixedHeight(32)
        self._search_input.setStyleSheet(
            f"QLineEdit {{ background: {C_CONTROL_BG}; color: {C_TEXT}; "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; "
            "padding: 3px 10px; font-size: 12px; font-family: 'Segoe UI'; }}"
            f"QLineEdit:focus {{ border-color: {C_ACCENT}; }}"
        )
        self._search_input.textChanged.connect(self._on_search_changed)
        filter_bar.addWidget(self._search_input, 1)

        cat_seg = SegmentedControl(
            [("All", "all"), ("Hands", "hands"), ("Special", "funny"), ("Custom", "custom")],
            current_val="all",
        )
        cat_seg.changed.connect(self._on_category_changed)
        filter_bar.addWidget(cat_seg)
        vbox.addLayout(filter_bar)

        grid_container = QWidget()
        grid_container.setStyleSheet("background: transparent;")
        self._pointer_grid_layout = QGridLayout(grid_container)
        self._pointer_grid_layout.setContentsMargins(0, 0, 0, 0)
        self._pointer_grid_layout.setSpacing(8)
        vbox.addWidget(grid_container)

        self._rebuild_pointer_grid()

        vbox.addSpacing(4)
        vbox.addWidget(_section_label("Custom Hands"))

        custom_body = QVBoxLayout()
        custom_body.setSpacing(8)
        custom_body.addWidget(
            _label("Add any transparent PNG image to use as your custom hand pointer.", 11, muted=True)
        )
        self._custom_hands_vbox = QVBoxLayout()
        self._custom_hands_vbox.setSpacing(6)
        custom_body.addLayout(self._custom_hands_vbox)
        self._refresh_custom_hands()

        add_hand_btn = _button("+ Upload Hand PNG", primary=True)
        add_hand_btn.clicked.connect(self._add_custom_hand)
        custom_body.addWidget(add_hand_btn, 0, Qt.AlignmentFlag.AlignLeft)
        vbox.addWidget(SettingsGroup(custom_body))

        vbox.addStretch()
        return scroll

    def _on_search_changed(self, text: str):
        self._pointer_search = text.strip().lower()
        self._rebuild_pointer_grid()

    def _on_category_changed(self, category: object):
        self._pointer_category = str(category)
        self._rebuild_pointer_grid()

    def _rebuild_pointer_grid(self):
        if self._pointer_grid_layout is None:
            return
        while self._pointer_grid_layout.count():
            item = self._pointer_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._pointer_thumbs.clear()

        current_key = self.config.get("pointer_style", "coral")
        entries: List[Tuple[str, str, str, str]] = []
        for key, name in HAND_CATALOG:
            entries.append((key, name, "hands", self.assets_dir))
        for key, name, _col in FUNNY_POINTERS:
            entries.append((key, name, "funny", self.assets_dir))
        for ch in self.config.get("custom_hands", []):
            entries.append((ch.get("key", ""), ch.get("name", "Custom"), "custom", self.custom_hands_dir))

        filtered = []
        for key, name, cat, adir in entries:
            if self._pointer_category != "all" and cat != self._pointer_category:
                continue
            if self._pointer_search and self._pointer_search not in name.lower() and self._pointer_search not in key.lower():
                continue
            filtered.append((key, name, cat, adir))

        cols = 4
        for idx, (key, name, cat, adir) in enumerate(filtered):
            thumb = PointerThumb(key, name, cat, adir, self.overlay.hand_assets)
            thumb.setSelected(key == current_key)
            thumb.selected_signal.connect(self._select_pointer)
            self._pointer_thumbs.append(thumb)
            self._pointer_grid_layout.addWidget(thumb, idx // cols, idx % cols)

    # ==================================================================
    # Page 2: Style & FX
    # ==================================================================
    def _page_style_fx(self) -> QScrollArea:
        scroll, _inner, vbox = _page_scroll()
        vbox.addWidget(_label("Style & FX", 18, C_TEXT, bold=True))

        # Pointer appearance
        vbox.addWidget(_section_label("Pointer"))
        ptr_body = QVBoxLayout()
        ptr_body.setSpacing(6)

        size_idx = max(0, min(4, int(self.config.get("pointer_scale", 2))))
        size_row, self._size_slider, self._size_val_lbl = _slider_row(
            "Pointer Size", "", lo=0, hi=4, val=size_idx
        )
        self._size_val_lbl.setText(SIZE_LABELS[size_idx])
        self._size_slider.valueChanged.connect(self._on_size_changed)
        ptr_body.addWidget(size_row)

        ticks_hl = QHBoxLayout()
        ticks_hl.setContentsMargins(2, 0, 2, 4)
        for lbl_txt in SIZE_LABELS:
            t_lbl = _label(lbl_txt, 10, muted=True)
            t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ticks_hl.addWidget(t_lbl, 1)
        ptr_body.addLayout(ticks_hl)

        _add_hsep(ptr_body)
        sh_row, self._shadow_toggle = _toggle_row(
            "Drop Shadow", "Render a soft silhouette shadow beneath the pointer",
            bool(self.config.get("show_shadow", True)),
        )
        self._shadow_toggle.toggled.connect(self._on_shadow_toggled)
        ptr_body.addWidget(sh_row)
        _add_hsep(ptr_body)

        rip_row, self._ripple_toggle = _toggle_row(
            "Click Ripple Ring", "Show an expanding pulse ring when clicking",
            bool(self.config.get("click_ripple", True)),
        )
        self._ripple_toggle.toggled.connect(self._on_ripple_toggled)
        ptr_body.addWidget(rip_row)
        vbox.addWidget(SettingsGroup(ptr_body))

        # Tap Bubbles
        vbox.addWidget(_section_label("Tap Bubbles"))
        bub_body = QVBoxLayout()
        bub_body.setSpacing(6)
        bub_row, self._bubble_toggle = _toggle_row(
            "Comic Tap Bubbles", "Display short callout words above clicks",
            bool(self.config.get("show_comic_bubbles", True)),
        )
        self._bubble_toggle.toggled.connect(self._on_bubbles_toggled)
        bub_body.addWidget(bub_row)
        _add_hsep(bub_body)

        pack_row = QHBoxLayout()
        pack_row.setContentsMargins(0, 4, 0, 2)
        pack_row.addWidget(_label("Word Style", 12, C_TEXT, bold=True))
        pack_row.addStretch()
        pack_seg = SegmentedControl(
            [("Playful", "funny"), ("Minimal", "clean")],
            current_val=self.config.get("comic_word_pack", "funny"),
        )
        pack_seg.changed.connect(self._on_word_pack_changed)
        pack_row.addWidget(pack_seg)
        bub_body.addLayout(pack_row)
        vbox.addWidget(SettingsGroup(bub_body))

        # Spotlight
        vbox.addWidget(_section_label("Spotlight"))
        spot_body = QVBoxLayout()
        spot_body.setSpacing(10)

        spot_r = int(self.config.get("spotlight_radius", 160))
        sr_row, sr_sl, sr_lbl = _slider_row("Spotlight Radius", "", lo=80, hi=300, val=spot_r)
        sr_lbl.setText(f"{spot_r} px")
        sr_sl.valueChanged.connect(lambda v: self._on_spot_radius_changed(v, sr_lbl))
        spot_body.addWidget(sr_row)

        spot_d = int(self.config.get("spotlight_dim", 60))
        sd_row, sd_sl, sd_lbl = _slider_row("Backdrop Dimness", "", lo=20, hi=90, val=spot_d)
        sd_lbl.setText(f"{spot_d}%")
        sd_sl.valueChanged.connect(lambda v: self._on_spot_dim_changed(v, sd_lbl))
        spot_body.addWidget(sd_row)
        vbox.addWidget(SettingsGroup(spot_body))

        vbox.addStretch()
        return scroll

    # ==================================================================
    # Page 3: Ink & Draw
    # ==================================================================
    def _page_ink(self) -> QScrollArea:
        scroll, _inner, vbox = _page_scroll()
        vbox.addWidget(_label("Ink & Draw", 18, C_TEXT, bold=True))

        vbox.addWidget(_section_label("Color"))
        color_body = QVBoxLayout()
        color_body.setSpacing(10)

        sw_row = QHBoxLayout()
        sw_row.setSpacing(8)
        cur_ink = self.config.get("ink_choice", "match")
        for key, name, hex_color in INK_SWATCHES:
            sw = InkSwatchButton(key, name, hex_color)
            sw.setChecked(key == cur_ink)
            sw.selected.connect(self._set_ink)
            self._swatch_btns[key] = sw
            sw_row.addWidget(sw)
        sw_row.addStretch()
        color_body.addLayout(sw_row)

        _add_hsep(color_body)
        rb_row, self._rainbow_toggle = _toggle_row(
            "Rainbow Ink", "Cycle colors smoothly while drawing strokes",
            cur_ink == "rainbow",
        )
        self._rainbow_toggle.toggled.connect(self._on_rainbow_toggled)
        color_body.addWidget(rb_row)
        vbox.addWidget(SettingsGroup(color_body))

        vbox.addWidget(_section_label("Stroke"))
        stroke_body = QVBoxLayout()
        stroke_body.setSpacing(8)

        ink_w = int(self.config.get("ink_width", 5))
        th_row, th_sl, th_lbl = _slider_row("Line Thickness", "", lo=2, hi=14, val=ink_w)
        th_lbl.setText(f"{ink_w} px")
        th_sl.valueChanged.connect(lambda v: self._on_ink_width_changed(v, th_lbl))
        stroke_body.addWidget(th_row)
        _add_hsep(stroke_body)

        smooth_on = bool(self.config.get("smooth_lines", False))
        sm_row, sm_toggle = _toggle_row(
            "Smooth Lines", "Stabilize mouse shake for cleaner curves",
            smooth_on,
        )
        stroke_body.addWidget(sm_row)

        sm_str = int(self.config.get("smooth_strength", 5))
        ss_row, ss_sl, ss_lbl = _slider_row("Smoothing Amount", "", lo=1, hi=10, val=sm_str)
        ss_row.setVisible(smooth_on)
        ss_sl.valueChanged.connect(lambda v: self._on_smooth_strength_changed(v, ss_lbl))
        stroke_body.addWidget(ss_row)
        sm_toggle.toggled.connect(lambda on: self._on_smooth_toggled(on, ss_row))

        _add_hsep(stroke_body)
        fade_hl = QHBoxLayout()
        fade_hl.setContentsMargins(0, 4, 0, 2)
        fade_hl.addWidget(_label("Fade Out After", 12, C_TEXT, bold=True))
        fade_hl.addStretch()
        fade_seg = SegmentedControl(
            [(lbl, sec) for lbl, sec in FADE_OPTIONS],
            current_val=int(self.config.get("fade_seconds", 6)),
        )
        fade_seg.changed.connect(self._set_fade)
        fade_hl.addWidget(fade_seg)
        stroke_body.addLayout(fade_hl)
        vbox.addWidget(SettingsGroup(stroke_body))

        vbox.addStretch()
        return scroll

    # ==================================================================
    # Page 4: Sound (Purely Audio)
    # ==================================================================
    def _page_sound(self) -> QScrollArea:
        scroll, _inner, vbox = _page_scroll()
        vbox.addWidget(_label("Sound", 18, C_TEXT, bold=True))

        vbox.addWidget(_section_label("Tap Sound"))
        tile_body = QVBoxLayout()
        tile_body.setSpacing(10)

        grid_w = QWidget()
        grid_w.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)

        cur_snd = self.config.get("sound_preset", "boop")
        for idx, (key, label) in enumerate(SOUND_PRESETS):
            tile = SoundTile(key, label)
            tile.setSelected(key == cur_snd)
            tile.clicked_signal.connect(self._on_sound_tile)
            self._sound_tiles.append(tile)
            grid.addWidget(tile, idx // 4, idx % 4)
        tile_body.addWidget(grid_w)

        _add_hsep(tile_body)
        vol_pct = int(float(self.config.get("sound_volume", 0.8)) * 100)
        vol_row, vol_sl, vol_lbl = _slider_row("Volume", "", lo=0, hi=100, val=vol_pct)
        vol_lbl.setText(f"{vol_pct}%")
        vol_sl.valueChanged.connect(lambda v: self._on_volume_changed(v, vol_lbl))
        tile_body.addWidget(vol_row)

        _add_hsep(tile_body)
        ls_row, ls_toggle = _toggle_row(
            "Sound in Laser Mode", "Play tap audio when using the laser dot",
            bool(self.config.get("laser_sound", False)),
        )
        ls_toggle.toggled.connect(self._on_laser_sound_toggled)
        tile_body.addWidget(ls_row)
        vbox.addWidget(SettingsGroup(tile_body))

        vbox.addWidget(_section_label("Custom Sounds"))
        cs_body = QVBoxLayout()
        cs_body.setSpacing(8)
        self._custom_sounds_vbox = QVBoxLayout()
        self._custom_sounds_vbox.setSpacing(6)
        cs_body.addLayout(self._custom_sounds_vbox)
        self._refresh_custom_sounds()

        add_snd_btn = _button("+ Upload Sound (WAV / MP3)")
        add_snd_btn.clicked.connect(self._add_custom_sound)
        cs_body.addWidget(add_snd_btn, 0, Qt.AlignmentFlag.AlignLeft)
        vbox.addWidget(SettingsGroup(cs_body))

        vbox.addStretch()
        return scroll

    # ==================================================================
    # Page 5: About
    # ==================================================================
    def _page_about(self) -> QScrollArea:
        scroll, _inner, vbox = _page_scroll()
        vbox.addStretch(1)

        hero_body = QVBoxLayout()
        hero_body.setSpacing(8)

        icon_badge = QLabel()
        icon_badge.setFixedSize(68, 68)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setPixmap(make_svg_icon("hand", "#FFFFFF", 36).pixmap(QSize(36, 36)))
        icon_badge.setStyleSheet(f"background: {C_ACCENT}; border-radius: 17px;")
        hero_body.addWidget(icon_badge, 0, Qt.AlignmentFlag.AlignHCenter)
        hero_body.addSpacing(4)

        title = _label("TinyHand Windows", 22, C_TEXT, bold=True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_body.addWidget(title)

        ver = _label("Version 1.0.0", 12, C_TEXT_SEC)
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_body.addWidget(ver)

        tag = _label("Floating presentation pointer, screen ink & spotlight for Windows.", 12, muted=True)
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_body.addWidget(tag)
        vbox.addWidget(SettingsGroup(hero_body))

        info_body = QVBoxLayout()
        info_body.setSpacing(6)
        for k, v in [
            ("Platform", "Windows Desktop (PyQt6)"),
            ("Pointers", "36 3D Hands, 4 Vector FX & Custom PNGs"),
            ("Licenses", "MIT License · THIRD_PARTY_LICENSES.txt"),
        ]:
            r = QHBoxLayout()
            r.addWidget(_label(k, 12, C_TEXT_SEC))
            r.addStretch()
            r.addWidget(_label(v, 12, C_TEXT, bold=True))
            info_body.addLayout(r)
            if k != "Licenses":
                _add_hsep(info_body)
        vbox.addWidget(SettingsGroup(info_body))

        credit = _label("Inspired by TinyHand (macOS)", 11, muted=True)
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(credit)

        reset_btn = _button("Reset All Settings", danger=True)
        reset_btn.setFixedWidth(180)
        reset_btn.clicked.connect(self._reset_all_settings)
        vbox.addWidget(reset_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        vbox.addStretch(1)
        return scroll

    # ==================================================================
    # Synchronization & Signal Handlers
    # ==================================================================
    def _sync_preview_from_state(self):
        if not self._preview:
            return
        style = self.config.get("pointer_style", "coral")
        if style.startswith("hand_"):
            style = style[5:]
        scale_idx = max(0, min(4, int(self.config.get("pointer_scale", 2))))
        self._preview.set_pointer(style, self.overlay.ink_engine.current_color)
        self._preview.set_scale_index(scale_idx)
        self._preview.show_shadow = bool(self.config.get("show_shadow", True))
        self._preview.show_bubbles = bool(self.config.get("show_comic_bubbles", True))
        self._preview.comic_word_pack = self.config.get("comic_word_pack", "funny")
        self._preview.show_ripple = bool(self.config.get("click_ripple", True))
        self._preview.spotlight_radius = float(self.config.get("spotlight_radius", 160))
        self._preview.spotlight_dim = float(self.config.get("spotlight_dim", 60)) / 100.0
        self._preview.ink_engine.rainbow_mode = self.overlay.ink_engine.rainbow_mode
        self._preview.ink_engine.stroke_width = self.overlay.ink_engine.stroke_width
        self._preview.ink_engine.smooth_lines = self.overlay.ink_engine.smooth_lines
        self._preview.ink_engine.smooth_strength = self.overlay.ink_engine.smooth_strength
        self._preview.ink_engine.auto_fade = self.overlay.ink_engine.auto_fade
        self._preview.ink_engine.fade_duration = self.overlay.ink_engine.fade_duration
        self._refresh_summary()

    def _refresh_summary(self):
        style = self.config.get("pointer_style", "coral")
        display = next((n for k, n in HAND_CATALOG if k == style), None)
        if not display:
            display = next((n for k, n, _ in FUNNY_POINTERS if k == style), None)
        if not display:
            display = next((c.get("name", style) for c in self.config.get("custom_hands", []) if c.get("key") == style), style)

        scale_idx = max(0, min(4, int(self.config.get("pointer_scale", 2))))
        scale_lbl = SIZE_LABELS[scale_idx]

        ink = self.config.get("ink_choice", "match").capitalize()
        sh = "Shadow on" if self.config.get("show_shadow", True) else "Shadow off"
        self._spec_pointer_lbl.setText(f"{display}  ·  Size {scale_lbl}")
        self._spec_meta_lbl.setText(f"{ink} ink  ·  {sh}")

    def sync_from_hud(self):
        """Called when HUD or open_settings triggers a refresh."""
        style = self.overlay.current_style
        self.config.set("pointer_style", style)
        for thumb in self._pointer_thumbs:
            thumb.setSelected(thumb.key == style)

        scale_idx = getattr(self.hud, "_scale_idx", 2)
        self.config.set("pointer_scale", scale_idx)
        if hasattr(self, "_size_slider"):
            self._size_slider.setValue(scale_idx, silent=True)
            self._size_val_lbl.setText(SIZE_LABELS[scale_idx])
        if hasattr(self, "_bubble_toggle"):
            self._bubble_toggle.setChecked(self.overlay.show_comic_bubbles, silent=True)

        self._sync_preview_from_state()

    def _select_pointer(self, key: str):
        self.config.set("pointer_style", key)
        self.config.save()
        for thumb in self._pointer_thumbs:
            thumb.setSelected(thumb.key == key)
        if self.overlay:
            self.overlay.set_pointer_style(key)
        if self._preview:
            col = self.overlay.ink_engine.current_color if self.overlay else None
            self._preview.set_pointer(key, col)
        if self.hud and hasattr(self.hud, "sync_pointer"):
            self.hud.sync_pointer(key)
        self._refresh_summary()

    def _on_size_changed(self, v: int):
        self._size_val_lbl.setText(SIZE_LABELS[v])
        self.config.set("pointer_scale", v)
        if self.overlay:
            self.overlay.set_pointer_scale(SIZE_SCALES[v])
        if self.hud and hasattr(self.hud, "sync_scale"):
            self.hud.sync_scale(v)
        if self._preview:
            self._preview.set_scale_index(v)
        self._refresh_summary()

    def _on_shadow_toggled(self, on: bool):
        self.config.set("show_shadow", on)
        if self.overlay:
            self.overlay.show_shadow = on
            self.overlay.update()
        if self._preview:
            self._preview.show_shadow = on
        self._refresh_summary()

    def _on_ripple_toggled(self, on: bool):
        self.config.set("click_ripple", on)
        if self.overlay:
            self.overlay.show_ripple = on
        if self._preview:
            self._preview.show_ripple = on
            if on:
                self._preview.trigger_tap()

    def _on_bubbles_toggled(self, on: bool):
        self.config.set("show_comic_bubbles", on)
        if self.overlay:
            self.overlay.show_comic_bubbles = on
        if self.hud and hasattr(self.hud, "sync_comic_bubbles"):
            self.hud.sync_comic_bubbles(on)
        if self._preview:
            self._preview.show_bubbles = on
            if on:
                self._preview.trigger_tap()

    def _on_word_pack_changed(self, pack: object):
        pack_str = str(pack)
        self.config.set("comic_word_pack", pack_str)
        if self.overlay:
            self.overlay.comic_word_pack = pack_str
        if self._preview:
            self._preview.comic_word_pack = pack_str
            self._preview.trigger_tap()

    def _on_spot_radius_changed(self, v: int, lbl: QLabel):
        lbl.setText(f"{v} px")
        self.config.set("spotlight_radius", v)
        if self.overlay:
            self.overlay.spotlight_radius = float(v)
            self.overlay.update()
        if self._preview:
            self._preview.spotlight_radius = float(v)
            self._pg_btn_spot.setChecked(True)

    def _on_spot_dim_changed(self, v: int, lbl: QLabel):
        lbl.setText(f"{v}%")
        self.config.set("spotlight_dim", v)
        if self.overlay:
            self.overlay.spotlight_dim = v / 100.0
            self.overlay.update()
        if self._preview:
            self._preview.spotlight_dim = v / 100.0
            self._pg_btn_spot.setChecked(True)

    def _set_ink(self, key: str, hex_color: str):
        self.config.set("ink_choice", key)
        for k, sw in self._swatch_btns.items():
            sw.setChecked(k == key)

        if hasattr(self, "_rainbow_toggle"):
            self._rainbow_toggle.setChecked(key == "rainbow", silent=True)

        if key == "match":
            col = self.overlay.get_pointer_default_color(self.overlay.current_style)
            if self.overlay:
                self.overlay.ink_match_pointer = True
            self.ink_engine.rainbow_mode = False
            self.ink_engine.current_color = col
        elif key == "rainbow":
            if self.overlay:
                self.overlay.ink_match_pointer = False
            self.ink_engine.rainbow_mode = True
        else:
            if self.overlay:
                self.overlay.ink_match_pointer = False
            self.ink_engine.rainbow_mode = False
            self.ink_engine.current_color = QColor(hex_color)

        if self._preview:
            self._preview.ink_engine.rainbow_mode = self.ink_engine.rainbow_mode
            self._preview.ink_engine.current_color = self.ink_engine.current_color
            self._preview.trigger_tap()
        self._refresh_summary()

    def _on_rainbow_toggled(self, on: bool):
        if on:
            self._set_ink("rainbow", "#FF6B6B")
        else:
            self._set_ink("match", "#3B82F6")

    def _on_ink_width_changed(self, v: int, lbl: QLabel):
        lbl.setText(f"{v} px")
        self.config.set("ink_width", v)
        self.ink_engine.stroke_width = float(v)
        if self._preview:
            self._preview.ink_engine.stroke_width = float(v)

    def _on_smooth_toggled(self, on: bool, strength_row: QWidget):
        self.config.set("smooth_lines", on)
        self.ink_engine.smooth_lines = on
        strength_row.setVisible(on)
        if self._preview:
            self._preview.ink_engine.smooth_lines = on

    def _on_smooth_strength_changed(self, v: int, lbl: QLabel):
        lbl.setText(str(v))
        self.config.set("smooth_strength", v)
        self.ink_engine.smooth_strength = v
        if self._preview:
            self._preview.ink_engine.smooth_strength = v

    def _set_fade(self, secs: object):
        sec_int = int(secs)
        self.config.set("fade_seconds", sec_int)
        for engine in (self.ink_engine, self._preview.ink_engine if self._preview else None):
            if engine is None:
                continue
            if sec_int == 0:
                engine.auto_fade = False
            else:
                engine.auto_fade = True
                engine.fade_duration = float(sec_int)

    def _on_sound_tile(self, key: str):
        for tile in self._sound_tiles:
            tile.setSelected(tile.key == key)
        if key == "off":
            self.sound_engine.enabled = False
        else:
            self.sound_engine.enabled = True
            self.sound_engine.set_sound(key)
            self.sound_engine.play_preview(key)
        self.config.set("sound_preset", key)
        if self.hud and hasattr(self.hud, "sync_sound"):
            self.hud.sync_sound(key, key != "off")

    def _on_volume_changed(self, v: int, lbl: QLabel):
        lbl.setText(f"{v}%")
        self.config.set("sound_volume", v / 100.0)
        self.sound_engine.set_volume(v / 100.0)

    def _on_laser_sound_toggled(self, on: bool):
        self.config.set("laser_sound", on)
        if self.overlay:
            self.overlay.laser_sound = on

    def _on_hold_key_changed(self, key: object):
        val = None if key == "off" else str(key)
        self.config.set("hold_to_draw_key", val)
        if self.overlay:
            self.overlay.hold_draw_key = val

    def _on_hotkey_changed(self, cfg_key: str, shortcut: str):
        self.config.set(cfg_key, shortcut)
        self.config.save()
        if self.input_hook and hasattr(self.input_hook, "update_hotkeys"):
            self.input_hook.update_hotkeys(
                toggle=self.config.get("hotkey_toggle", "ctrl+alt+h"),
                clear=self.config.get("hotkey_clear", "ctrl+alt+x"),
                spotlight=self.config.get("hotkey_spotlight", "ctrl+alt+s"),
                drawing=self.config.get("hotkey_draw", "ctrl+alt+d"),
            )

    def _add_custom_hand(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Transparent Hand PNG", "", "PNG Images (*.png)"
        )
        if not path:
            return
        os.makedirs(self.custom_hands_dir, exist_ok=True)
        filename = os.path.basename(path)
        dest = os.path.join(self.custom_hands_dir, filename)
        try:
            shutil.copy2(path, dest)
            stem = os.path.splitext(filename)[0]
            key = f"custom_{stem}"
            name = stem.replace("_", " ").title()
            self.config.add_custom_hand(key, name, filename)
            asset = self.overlay.add_custom_hand(key, dest) if self.overlay else None
            if self.hud and hasattr(self.hud, "add_custom_hand"):
                col = asset.default_ink if asset else QColor(C_ACCENT)
                self.hud.add_custom_hand(key, name, col)
            self._refresh_custom_hands()
            self._rebuild_pointer_grid()
            self._select_pointer(key)
        except Exception:
            pass

    def _refresh_custom_hands(self):
        while self._custom_hands_vbox.count():
            item = self._custom_hands_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        hands = self.config.get("custom_hands", [])
        if not hands:
            self._custom_hands_vbox.addWidget(_label("No custom hands uploaded yet.", 11, muted=True))
            return
        for entry in hands:
            k = entry.get("key", "")
            self._custom_hands_vbox.addWidget(
                self._make_custom_row(
                    entry.get("name", "Custom Hand"),
                    on_use=lambda _k=k: self._select_pointer(_k),
                    on_remove=lambda _k=k: self._remove_custom_hand(_k),
                )
            )

    def _remove_custom_hand(self, key: str):
        self.config.remove_custom_hand(key)
        if self.overlay:
            self.overlay.remove_custom_hand(key)
        if self.hud and hasattr(self.hud, "remove_custom_hand"):
            self.hud.remove_custom_hand(key)
        self._refresh_custom_hands()
        self._rebuild_pointer_grid()
        self._refresh_summary()

    def _add_custom_sound(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Add Custom Tap Sound", "", "Audio Files (*.wav *.mp3)"
        )
        if not path:
            return
        os.makedirs(self.custom_sounds_dir, exist_ok=True)
        filename = os.path.basename(path)
        dest = os.path.join(self.custom_sounds_dir, filename)
        try:
            shutil.copy2(path, dest)
            stem = os.path.splitext(filename)[0]
            key = f"custom_{stem}"
            label = stem.replace("_", " ").title()
            self.config.add_custom_sound(key, label, filename)
            self.sound_engine.add_custom_sound(key, dest)
            self._refresh_custom_sounds()
            self._on_sound_tile(key)
        except Exception:
            pass

    def _refresh_custom_sounds(self):
        while self._custom_sounds_vbox.count():
            item = self._custom_sounds_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        sounds = self.config.get("custom_sounds", [])
        if not sounds:
            self._custom_sounds_vbox.addWidget(_label("No custom sounds uploaded yet.", 11, muted=True))
            return
        for entry in sounds:
            k = entry.get("key", "")
            self._custom_sounds_vbox.addWidget(
                self._make_custom_row(
                    entry.get("label", "Custom Sound"),
                    on_use=lambda _k=k: self._on_sound_tile(_k),
                    on_remove=lambda _k=k: self._remove_custom_sound(_k),
                )
            )

    def _remove_custom_sound(self, key: str):
        self.config.remove_custom_sound(key)
        self.sound_engine.remove_custom_sound(key)
        self._refresh_custom_sounds()

    def _make_custom_row(
        self,
        name: str,
        on_use: Callable[[], None],
        on_remove: Callable[[], None],
    ) -> QWidget:
        row = QWidget()
        row.setObjectName("CustomUploadRow")
        row.setStyleSheet(
            f"#CustomUploadRow {{ background: {C_CONTROL_BG}; "
            "border: 1px solid rgba(255,255,255,0.07); border-radius: 7px; }"
        )
        hl = QHBoxLayout(row)
        hl.setContentsMargins(10, 6, 8, 6)
        hl.setSpacing(8)
        hl.addWidget(_label(name, 12, C_TEXT, bold=True))
        hl.addStretch()

        use_btn = QPushButton("Use")
        use_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        use_btn.setStyleSheet(
            f"QPushButton {{ background: rgba(59,130,246,0.18); color: {C_ACCENT_LIGHT}; "
            "border: none; border-radius: 5px; padding: 3px 10px; font-size: 11px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {C_ACCENT}; color: #FFFFFF; }}"
        )
        use_btn.clicked.connect(on_use)
        hl.addWidget(use_btn)

        rm_btn = QPushButton("Remove")
        rm_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        rm_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C_DANGER}; border: none; "
            "padding: 3px 6px; font-size: 11px; font-weight: 500; }}"
            "QPushButton:hover { color: #FFFFFF; }"
        )
        rm_btn.clicked.connect(on_remove)
        hl.addWidget(rm_btn)
        return row

    def _reset_all_settings(self):
        reply = QMessageBox.question(
            self,
            "Reset All Settings",
            "Reset all preferences to factory defaults?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config.reset_defaults()
            self._select_pointer("coral")
            self._size_slider.setValue(2)
            self._set_ink("match", "#3B82F6")
            self._on_sound_tile("boop")

    @staticmethod
    def _combo_qss() -> str:
        return (
            f"QComboBox {{ background: {C_CONTROL_BG}; color: {C_TEXT}; "
            "border: 1px solid rgba(255, 255, 255, 0.10); border-radius: 7px; "
            "padding: 4px 10px; font-size: 12px; font-family: 'Segoe UI'; }"
            "QComboBox:hover { border-color: rgba(255, 255, 255, 0.25); }"
            "QComboBox::drop-down { border: none; width: 20px; }"
            f"QComboBox QAbstractItemView {{ background: {C_SURFACE}; color: {C_TEXT}; "
            "border: 1px solid rgba(255, 255, 255, 0.14); "
            f"selection-background-color: {C_ACCENT}; selection-color: #FFFFFF; }}"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 48:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def closeEvent(self, event):
        if self._preview:
            self._preview.cleanup()
        if self.config:
            self.config.save()
        super().closeEvent(event)
