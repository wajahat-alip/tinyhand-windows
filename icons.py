# -*- coding: utf-8 -*-
"""
Vector SVG Icon Helpers for TinyHand Pro (Windows Edition).
Generates crisp, DPI-aware QIcon instances with zero raw emoji dependencies.
"""

from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap
from PyQt6.QtSvg import QSvgRenderer


_SVG_TEMPLATES = {
    "hand": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M18 11V6a2 2 0 0 0-2-2 2 2 0 0 0-2 2"/>'
        '<path d="M14 10V4a2 2 0 0 0-2-2 2 2 0 0 0-2 2v6"/>'
        '<path d="M10 10.5V6a2 2 0 0 0-2-2 2 2 0 0 0-2 2v8"/>'
        '<path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6'
        'a2 2 0 0 1 2.83-2.82L7 15"/>'
        '</svg>'
    ),
    "pen": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 20h9"/>'
        '<path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4Z"/>'
        '</svg>'
    ),
    "spotlight": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="9"/>'
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M12 2v2"/><path d="M12 20v2"/>'
        '<path d="M2 12h2"/><path d="M20 12h2"/>'
        '</svg>'
    ),
    "clear": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="m7 21-4.3-4.3c-1-1-1-2.5 0-3.4l9.6-9.6c1-1 2.5-1 3.4 0l5.6 5.6'
        'c1 1 1 2.5 0 3.4L13 21"/>'
        '<path d="M22 21H7"/>'
        '<path d="m5 11 9 9"/>'
        '</svg>'
    ),
    "pops": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'
        '<path d="M9 10h.01"/><path d="M15 10h.01"/>'
        '</svg>'
    ),
    "sound_on": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>'
        '<path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>'
        '<path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>'
        '</svg>'
    ),
    "sound_off": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>'
        '<line x1="23" y1="9" x2="17" y2="15"/>'
        '<line x1="17" y1="9" x2="23" y2="15"/>'
        '</svg>'
    ),
    "minimize": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.2" '
        'stroke-linecap="round">'
        '<line x1="5" y1="12" x2="19" y2="12"/>'
        '</svg>'
    ),
    "close": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.2" '
        'stroke-linecap="round">'
        '<line x1="6" y1="6" x2="18" y2="18"/>'
        '<line x1="18" y1="6" x2="6" y2="18"/>'
        '</svg>'
    ),
    "grip": (
        '<svg viewBox="0 0 12 24" fill="{color}">'
        '<circle cx="3" cy="6" r="1.4"/><circle cx="9" cy="6" r="1.4"/>'
        '<circle cx="3" cy="12" r="1.4"/><circle cx="9" cy="12" r="1.4"/>'
        '<circle cx="3" cy="18" r="1.4"/><circle cx="9" cy="18" r="1.4"/>'
        '</svg>'
    ),
    "settings": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06'
        'a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09'
        'A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83'
        'l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09'
        'A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83'
        'l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09'
        'a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83'
        'l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09'
        'a1.65 1.65 0 0 0-1.51 1z"/>'
        '</svg>'
    ),
    "info": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/>'
        '<line x1="12" y1="16" x2="12" y2="12"/>'
        '<line x1="12" y1="8" x2="12.01" y2="8"/>'
        '</svg>'
    ),
    "info_i": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.4" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="6.5" r="1.2" fill="{color}" stroke="none"/>'
        '<line x1="12" y1="11" x2="12" y2="18.5"/>'
        '</svg>'
    ),
    "sparkles": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 3l1.9 5.2L19 10l-5.1 1.8L12 17l-1.9-5.2L5 10l5.1-1.8L12 3z"/>'
        '<path d="M19 16l.9 2.1L22 19l-2.1.9L19 22l-.9-2.1L16 19l2.1-.9L19 16z"/>'
        '</svg>'
    ),
    "sun": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.1" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="4.2"/>'
        '<line x1="12" y1="2.2" x2="12" y2="4.4"/>'
        '<line x1="12" y1="19.6" x2="12" y2="21.8"/>'
        '<line x1="4.93" y1="4.93" x2="6.49" y2="6.49"/>'
        '<line x1="17.51" y1="17.51" x2="19.07" y2="19.07"/>'
        '<line x1="2.2" y1="12" x2="4.4" y2="12"/>'
        '<line x1="19.6" y1="12" x2="21.8" y2="12"/>'
        '<line x1="4.93" y1="19.07" x2="6.49" y2="17.51"/>'
        '<line x1="17.51" y1="6.49" x2="19.07" y2="4.93"/>'
        '</svg>'
    ),
    "moon": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.1" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M20.5 13.2A8.5 8.5 0 1 1 10.8 3.5a6.8 6.8 0 0 0 9.7 9.7z"/>'
        '</svg>'
    ),
    "globe": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/>'
        '<line x1="2" y1="12" x2="22" y2="12"/>'
        '<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>'
        '</svg>'
    ),
}


def make_svg_icon(name: str, color: str = "#E2E8F0", size: int = 16) -> QIcon:
    """Render an inline SVG template at 2x resolution into a crisp QIcon."""
    template = _SVG_TEMPLATES.get(name, _SVG_TEMPLATES["hand"])
    svg_bytes = template.format(color=color).encode("utf-8")
    renderer = QSvgRenderer(QByteArray(svg_bytes))

    scale = 2
    px_size = size * scale
    pixmap = QPixmap(px_size, px_size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, px_size, px_size))
    painter.end()

    pixmap.setDevicePixelRatio(scale)
    return QIcon(pixmap)


def make_color_dot_icon(color: QColor, size: int = 10) -> QIcon:
    """Create a small anti-aliased colored circle icon for style dropdowns."""
    scale = 2
    px = size * scale
    pixmap = QPixmap(px, px)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QColor(255, 255, 255, 70))
    painter.setBrush(color)
    margin = 1.5 * scale
    painter.drawEllipse(QRectF(margin, margin, px - 2 * margin, px - 2 * margin))
    painter.end()

    pixmap.setDevicePixelRatio(scale)
    return QIcon(pixmap)


def make_tray_icon() -> QIcon:
    """Generate a crisp vector hand badge for the Windows system tray."""
    size = 32
    scale = 2
    px = size * scale
    pixmap = QPixmap(px, px)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    painter.setBrush(QColor("#2563EB"))
    painter.setPen(QColor(147, 197, 253, 180))
    painter.drawEllipse(QRectF(2 * scale, 2 * scale, (size - 4) * scale, (size - 4) * scale))

    svg_bytes = _SVG_TEMPLATES["hand"].format(color="#FFFFFF").encode("utf-8")
    renderer = QSvgRenderer(QByteArray(svg_bytes))
    pad = 7 * scale
    renderer.render(painter, QRectF(pad, pad, px - 2 * pad, px - 2 * pad))
    painter.end()

    pixmap.setDevicePixelRatio(scale)
    return QIcon(pixmap)


def make_sidebar_badge_pixmap(
    name: str,
    badge_color: str,
    size: int = 24,
    radius: float = 6.0,
) -> QPixmap:
    """Render a crisp 24x24 rounded-square colorful badge with a white SVG icon."""
    scale = 2
    px = size * scale
    pixmap = QPixmap(px, px)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    rect = QRectF(0.0, 0.0, float(px), float(px))
    path = QPainterPath()
    path.addRoundedRect(rect, radius * scale, radius * scale)
    painter.fillPath(path, QColor(badge_color))

    svg_bytes = _SVG_TEMPLATES.get(name, _SVG_TEMPLATES["hand"]).format(color="#FFFFFF").encode("utf-8")
    renderer = QSvgRenderer(QByteArray(svg_bytes))
    pad = 4.5 * scale
    renderer.render(painter, QRectF(pad, pad, px - 2 * pad, px - 2 * pad))
    painter.end()

    pixmap.setDevicePixelRatio(scale)
    return pixmap
