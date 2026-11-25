# -*- coding: utf-8 -*-
"""
Modern Floating Frosted-Glass HUD Capsule for TinyHand Pro (Windows Edition).
DPI-aware dynamic layout with obsidian glass palette, custom vector SVG icons,
and zero raw emoji characters.
"""

from PyQt6.QtCore import QPoint, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hand_engine import HAND_CATALOG
from icons import make_app_icon, make_color_dot_icon, make_svg_icon


class StatusDot(QWidget):
    """Subtle optical status indicator dot (emerald when active, amber when hidden)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = True
        self.setFixedSize(10, 10)

    def set_active(self, active: bool):
        if self._active != active:
            self._active = active
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        core = QColor("#22C55E") if self._active else QColor("#F59E0B")
        halo = QColor(34, 197, 94, 70) if self._active else QColor(245, 158, 11, 70)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(halo)
        painter.drawEllipse(QRectF(0.5, 0.5, 9.0, 9.0))
        painter.setBrush(core)
        painter.drawEllipse(QRectF(2.5, 2.5, 5.0, 5.0))
        painter.end()


class GlassCapsule(QFrame):
    """Deep obsidian frosted-glass pill container with hairline rim highlight."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = min(24.0, rect.height() * 0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        # Deep translucent obsidian surface
        painter.fillPath(path, QColor(15, 18, 26, 224))

        # Subtle 1px translucent border
        painter.setPen(QPen(QColor(255, 255, 255, 22), 1.0))
        painter.drawPath(path)

        # Soft top specular edge
        highlight = QPainterPath()
        highlight.moveTo(rect.left() + radius, rect.top() + 1.0)
        highlight.lineTo(rect.right() - radius, rect.top() + 1.0)
        painter.setPen(QPen(QColor(255, 255, 255, 16), 1.0))
        painter.drawPath(highlight)

        painter.end()


class TinyHandHUD(QWidget):
    """Floating DPI-aware control capsule for TinyHand Pro."""

    _SHADOW_PAD = 14
    _SCALE_PRESETS = [("XS", 0.62), ("S", 0.80), ("M", 1.0), ("L", 1.22), ("XL", 1.44)]

    def __init__(self, overlay, sound_engine, config=None):
        super().__init__()
        self.overlay = overlay
        self.sound_engine = sound_engine
        self.config = config
        self.on_hud_changed = None
        self.is_collapsed = False
        self._drag_offset = QPoint()
        self._scale_idx = 2  # Medium default

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowIcon(make_app_icon())

        self._setup_ui()
        self._position_initial()

    def _setup_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(
            self._SHADOW_PAD, self._SHADOW_PAD, self._SHADOW_PAD, self._SHADOW_PAD
        )
        self.root_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        self.capsule = GlassCapsule(self)
        row = QHBoxLayout(self.capsule)
        row.setContentsMargins(14, 7, 12, 7)
        row.setSpacing(8)

        # 1. Grip, Status Dot & Brand Title
        brand_wrap = QWidget()
        brand_layout = QHBoxLayout(brand_wrap)
        brand_layout.setContentsMargins(2, 0, 4, 0)
        brand_layout.setSpacing(6)

        grip_lbl = QLabel()
        grip_lbl.setPixmap(make_svg_icon("grip", "#64748B", 12).pixmap(12, 16))
        grip_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_dot = StatusDot()
        title_lbl = QLabel("TinyHand")
        title_lbl.setStyleSheet(
            "color: #F8FAFC; font-family: 'Segoe UI', sans-serif; "
            "font-size: 12px; font-weight: 600; letter-spacing: 0.2px;"
        )

        brand_layout.addWidget(grip_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        brand_layout.addWidget(self.status_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        brand_layout.addWidget(title_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(brand_wrap, 0, Qt.AlignmentFlag.AlignVCenter)

        row.addWidget(self._create_separator())

        # 2. Pointer Style Selector (4 Custom + All 36 Original Hands)
        self.pointer_combo = QComboBox()
        self.pointer_combo.setIconSize(QSize(10, 10))
        self.pointer_combo.setMaxVisibleItems(14)
        self.pointer_combo.setToolTip("Select Pointer Style")
        self.pointer_combo.setStyleSheet(self._combo_stylesheet(min_width=142))

        custom_items = [
            ("Cat Paw (Funny)", "cat_paw", QColor("#FB7185")),
            ("Magic Wand", "magic_wand", QColor("#38BDF8")),
            ("Boxing Glove", "boxing_glove", QColor("#DC2626")),
            ("Cyber Laser", "laser", QColor("#EF4444")),
        ]
        for label, key, swatch in custom_items:
            self.pointer_combo.addItem(make_color_dot_icon(swatch), label, key)

        for key, label in HAND_CATALOG:
            if key in self.overlay.hand_assets:
                swatch = self.overlay.hand_assets[key].default_ink
                self.pointer_combo.addItem(make_color_dot_icon(swatch), label, key)

        # Sync default selection with overlay.current_style
        default_idx = self.pointer_combo.findData(self.overlay.current_style)
        if default_idx >= 0:
            self.pointer_combo.setCurrentIndex(default_idx)

        self.pointer_combo.currentIndexChanged.connect(self._on_pointer_changed)
        row.addWidget(self.pointer_combo, 0, Qt.AlignmentFlag.AlignVCenter)

        # Size Cycler (S / M / L)
        self.btn_size = QPushButton("M")
        self.btn_size.setFixedSize(28, 28)
        self.btn_size.setToolTip("Pointer Size (Small / Medium / Large)")
        self.btn_size.setStyleSheet(self._pill_button_stylesheet(compact=True))
        self.btn_size.clicked.connect(self._cycle_scale)
        row.addWidget(self.btn_size, 0, Qt.AlignmentFlag.AlignVCenter)

        row.addWidget(self._create_separator())

        # 3. Mode & Tool Toggles (SVG icons, zero emojis)
        self.btn_draw = self._create_tool_button("Draw", "pen", "Toggle Screen Drawing (Ctrl+Alt+D)")
        self.btn_draw.toggled.connect(self._toggle_drawing)
        row.addWidget(self.btn_draw, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_spotlight = self._create_tool_button(
            "Spot", "spotlight", "Toggle Cinema Spotlight (Ctrl+Alt+S)"
        )
        self.btn_spotlight.toggled.connect(self._toggle_spotlight)
        row.addWidget(self.btn_spotlight, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setIcon(make_svg_icon("clear", "#FDA4AF", 14))
        self.btn_clear.setIconSize(QSize(14, 14))
        self.btn_clear.setToolTip("Clear Screen Ink (Ctrl+Alt+X)")
        self.btn_clear.setStyleSheet(self._clear_button_stylesheet())
        self.btn_clear.clicked.connect(self.overlay.ink_engine.clear)
        row.addWidget(self.btn_clear, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_comic = self._create_tool_button(
            "Pops", "pops", "Toggle Comic Tap Bubbles", checked=True
        )
        self.btn_comic.toggled.connect(self._on_comic_toggled)
        row.addWidget(self.btn_comic, 0, Qt.AlignmentFlag.AlignVCenter)

        row.addWidget(self._create_separator())

        # 4. Audio Mute & Sound Preset
        self.btn_sound = QPushButton()
        self.btn_sound.setFixedSize(28, 28)
        self.btn_sound.setIcon(make_svg_icon("sound_on", "#E2E8F0", 15))
        self.btn_sound.setIconSize(QSize(15, 15))
        self.btn_sound.setToolTip("Mute / Unmute Tap Sound")
        self.btn_sound.setStyleSheet(self._pill_button_stylesheet(compact=True))
        self.btn_sound.clicked.connect(self._toggle_sound)
        row.addWidget(self.btn_sound, 0, Qt.AlignmentFlag.AlignVCenter)

        self.sound_combo = QComboBox()
        self.sound_combo.setToolTip("Tap Sound Preset")
        self.sound_combo.setStyleSheet(self._combo_stylesheet(min_width=78))
        for label, key in [
            ("Boop", "boop"),
            ("Click", "click"),
            ("Pop", "pop"),
            ("Thock", "thock"),
            ("Squeak", "squeak"),
            ("Wood", "wood"),
        ]:
            self.sound_combo.addItem(label, key)
        self.sound_combo.currentIndexChanged.connect(self._on_sound_changed)
        row.addWidget(self.sound_combo, 0, Qt.AlignmentFlag.AlignVCenter)

        row.addWidget(self._create_separator())

        # 5. Settings
        self.btn_settings = QPushButton()
        self.btn_settings.setFixedSize(26, 26)
        self.btn_settings.setIcon(make_svg_icon("settings", "#CBD5E1", 14))
        self.btn_settings.setIconSize(QSize(14, 14))
        self.btn_settings.setToolTip("Open Settings")
        self.btn_settings.setStyleSheet(self._icon_only_stylesheet())
        row.addWidget(self.btn_settings, 0, Qt.AlignmentFlag.AlignVCenter)

        # 6. Collapse to Orb & Close
        self.btn_min = QPushButton()
        self.btn_min.setFixedSize(26, 26)
        self.btn_min.setIcon(make_svg_icon("minimize", "#94A3B8", 13))
        self.btn_min.setIconSize(QSize(13, 13))
        self.btn_min.setToolTip("Collapse to Floating Orb")
        self.btn_min.setStyleSheet(self._icon_only_stylesheet())
        self.btn_min.clicked.connect(self._toggle_collapse)
        row.addWidget(self.btn_min, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_close = QPushButton()
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.setIcon(make_svg_icon("close", "#F87171", 13))
        self.btn_close.setIconSize(QSize(13, 13))
        self.btn_close.setToolTip("Exit TinyHand Pro")
        self.btn_close.setStyleSheet(self._icon_only_stylesheet(danger=True))
        self.btn_close.clicked.connect(self.close_all)
        row.addWidget(self.btn_close, 0, Qt.AlignmentFlag.AlignVCenter)

        # Collapsed Orb Button (hidden initially)
        self.btn_expand = QPushButton()
        self.btn_expand.setFixedSize(44, 44)
        self.btn_expand.setIcon(make_app_icon())
        self.btn_expand.setIconSize(QSize(26, 26))
        self.btn_expand.setToolTip("Expand TinyHand HUD")
        self.btn_expand.setStyleSheet("""
            QPushButton {
                background-color: rgba(15, 18, 26, 230);
                border: 1px solid rgba(96, 165, 250, 120);
                border-radius: 22px;
            }
            QPushButton:hover {
                background-color: rgba(37, 99, 235, 220);
                border-color: rgba(147, 197, 253, 220);
            }
        """)
        self.btn_expand.clicked.connect(self._toggle_collapse)
        self.btn_expand.hide()

        self.root_layout.addWidget(self.capsule)
        self.root_layout.addWidget(self.btn_expand)

        # Soft Gaussian drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 155))
        shadow.setOffset(0, 7)
        self.capsule.setGraphicsEffect(shadow)

        orb_shadow = QGraphicsDropShadowEffect(self)
        orb_shadow.setBlurRadius(22)
        orb_shadow.setColor(QColor(0, 0, 0, 155))
        orb_shadow.setOffset(0, 5)
        self.btn_expand.setGraphicsEffect(orb_shadow)

        self.adjustSize()

    def _position_initial(self):
        screen = QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else self.screen().availableGeometry()
        self.adjustSize()
        x = avail.x() + (avail.width() - self.width()) // 2
        y = avail.y() + avail.height() - self.height() - 12
        self.move(x, y)

    def _create_separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFixedSize(1, 20)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 22); border: none;")
        return line

    def _create_tool_button(
        self, label: str, icon_name: str, tooltip: str, checked: bool = False
    ) -> QPushButton:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setToolTip(tooltip)
        btn.setIcon(make_svg_icon(icon_name, "#FFFFFF" if checked else "#CBD5E1", 14))
        btn.setIconSize(QSize(14, 14))
        btn.setStyleSheet(self._pill_button_stylesheet(compact=False))
        btn.toggled.connect(
            lambda on, b=btn, ic=icon_name: b.setIcon(
                make_svg_icon(ic, "#FFFFFF" if on else "#CBD5E1", 14)
            )
        )
        return btn

    @staticmethod
    def _combo_stylesheet(min_width: int = 100) -> str:
        return f"""
            QComboBox {{
                background: rgba(255, 255, 255, 13);
                color: #F1F5F9;
                border: 1px solid rgba(255, 255, 255, 22);
                border-radius: 10px;
                padding: 4px 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 500;
                min-width: {min_width}px;
                min-height: 20px;
            }}
            QComboBox:hover {{
                background: rgba(255, 255, 255, 22);
                border-color: rgba(96, 165, 250, 140);
            }}
            QComboBox::drop-down {{
                border: none;
                width: 18px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #131620;
                color: #F1F5F9;
                selection-background-color: #2563EB;
                selection-color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 8px;
                padding: 4px;
                outline: none;
            }}
        """

    @staticmethod
    def _pill_button_stylesheet(compact: bool = False) -> str:
        pad = "0px" if compact else "4px 10px"
        return f"""
            QPushButton {{
                background: rgba(255, 255, 255, 12);
                color: #CBD5E1;
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 10px;
                padding: {pad};
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 600;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 24);
                color: #FFFFFF;
                border-color: rgba(96, 165, 250, 140);
            }}
            QPushButton:checked {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #3B82F6);
                color: #FFFFFF;
                border-color: rgba(147, 197, 253, 180);
            }}
        """

    @staticmethod
    def _clear_button_stylesheet() -> str:
        return """
            QPushButton {
                background: rgba(244, 63, 94, 24);
                color: #FDA4AF;
                border: 1px solid rgba(244, 63, 94, 60);
                border-radius: 10px;
                padding: 4px 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 600;
                min-height: 20px;
            }
            QPushButton:hover {
                background: rgba(244, 63, 94, 52);
                color: #FFFFFF;
                border-color: rgba(251, 113, 133, 170);
            }
        """

    @staticmethod
    def _icon_only_stylesheet(danger: bool = False) -> str:
        hover_bg = "rgba(239, 68, 68, 45)" if danger else "rgba(255, 255, 255, 22)"
        return f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 13px;
            }}
            QPushButton:hover {{
                background: {hover_bg};
            }}
        """

    def set_pointer_active(self, active: bool):
        self.status_dot.set_active(active)

    def sync_pointer(self, style: str):
        idx = self.pointer_combo.findData(style)
        if idx >= 0:
            self.pointer_combo.blockSignals(True)
            self.pointer_combo.setCurrentIndex(idx)
            self.pointer_combo.blockSignals(False)

    def sync_scale(self, idx: int):
        idx = max(0, min(len(self._SCALE_PRESETS) - 1, idx))
        self._scale_idx = idx
        label, _scale = self._SCALE_PRESETS[idx]
        self.btn_size.setText(label)

    def sync_comic_bubbles(self, enabled: bool):
        self.btn_comic.blockSignals(True)
        self.btn_comic.setChecked(enabled)
        self.btn_comic.blockSignals(False)

    def sync_sound(self, sound_key: str, enabled: bool):
        self.btn_sound.setIcon(
            make_svg_icon("sound_on" if enabled else "sound_off", "#E2E8F0" if enabled else "#64748B", 15)
        )
        idx = self.sound_combo.findData(sound_key)
        if idx >= 0:
            self.sound_combo.blockSignals(True)
            self.sound_combo.setCurrentIndex(idx)
            self.sound_combo.blockSignals(False)

    def add_custom_hand(self, key: str, label: str, color: QColor):
        if self.pointer_combo.findData(key) < 0:
            self.pointer_combo.addItem(make_color_dot_icon(color), label, key)

    def remove_custom_hand(self, key: str):
        idx = self.pointer_combo.findData(key)
        if idx >= 0:
            self.pointer_combo.removeItem(idx)

    def _notify_hud_changed(self):
        if callable(self.on_hud_changed):
            self.on_hud_changed()

    def _on_comic_toggled(self, val: bool):
        self.overlay.show_comic_bubbles = val
        if self.config:
            self.config.set("show_comic_bubbles", val)
        self._notify_hud_changed()

    def _cycle_scale(self):
        self._scale_idx = (self._scale_idx + 1) % len(self._SCALE_PRESETS)
        label, scale = self._SCALE_PRESETS[self._scale_idx]
        self.btn_size.setText(label)
        self.overlay.set_pointer_scale(scale)
        if self.config:
            self.config.set("pointer_scale", self._scale_idx)
        self._notify_hud_changed()

    def _toggle_drawing(self, checked: bool):
        self.overlay.drawing_mode = checked
        if not checked:
            self.overlay.ink_engine.end_stroke()

    def _toggle_spotlight(self, checked: bool):
        self.overlay.spotlight_mode = checked
        self.overlay.update()

    def _on_pointer_changed(self, _index: int):
        style = self.pointer_combo.currentData()
        if style:
            self.overlay.set_pointer_style(style)
            if self.config:
                self.config.set("pointer_style", style)
            self._notify_hud_changed()

    def _toggle_sound(self):
        is_on = self.sound_engine.toggle()
        self.btn_sound.setIcon(
            make_svg_icon("sound_on" if is_on else "sound_off", "#E2E8F0" if is_on else "#64748B", 15)
        )
        if self.config:
            if not is_on:
                self.config.set("sound_preset", "off")
            else:
                self.config.set("sound_preset", self.sound_engine.current_sound)
        self._notify_hud_changed()

    def _on_sound_changed(self, _index: int):
        sound_key = self.sound_combo.currentData()
        if sound_key:
            self.sound_engine.enabled = True
            self.sound_engine.set_sound(sound_key)
            self.btn_sound.setIcon(make_svg_icon("sound_on", "#E2E8F0", 15))
            if self.config:
                self.config.set("sound_preset", sound_key)
            self._notify_hud_changed()

    def _toggle_collapse(self):
        center_before = self.geometry().center()
        self.is_collapsed = not self.is_collapsed

        if self.is_collapsed:
            self.capsule.hide()
            self.btn_expand.show()
        else:
            self.btn_expand.hide()
            self.capsule.show()

        self.adjustSize()
        # Keep the widget anchored cleanly near its previous center without leaving screen
        screen = self.screen() or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        nx = max(avail.left(), min(center_before.x() - self.width() // 2, avail.right() - self.width()))
        ny = max(avail.top(), min(center_before.y() - self.height() // 2, avail.bottom() - self.height()))
        self.move(nx, ny)

    def close_all(self):
        QApplication.quit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_offset.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_offset = QPoint()
        super().mouseReleaseEvent(event)
