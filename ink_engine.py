# -*- coding: utf-8 -*-
"""
Ink Engine for TinyHand Pro (Windows Edition).
Smooth quadratic-spline vector ink trails with fade-out timers and glow passes.
Supports rainbow mode and Chaikin smooth-line processing.
"""

import math
import time
from typing import List, Optional
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen


class Stroke:
    """Represents a single continuous ink path with fade-out lifecycle."""

    def __init__(
        self,
        color: QColor,
        width: float = 5.0,
        auto_fade: bool = True,
        fade_duration: float = 3.5,
    ):
        self.points: List[QPointF] = []
        self.color = color
        self.width = width
        self.auto_fade = auto_fade
        self.fade_duration = fade_duration
        self.created_at = time.time()
        self.completed_at: Optional[float] = None
        self.is_finished = False

    def add_point(self, pt: QPointF):
        if not self.points:
            self.points.append(pt)
            return

        last = self.points[-1]
        if math.hypot(pt.x() - last.x(), pt.y() - last.y()) >= 3.0:
            self.points.append(pt)

    def finish(self):
        self.is_finished = True
        self.completed_at = time.time()

    def get_alpha(self, current_time: float) -> float:
        if not self.auto_fade or not self.is_finished or self.completed_at is None:
            return 1.0

        elapsed = current_time - self.completed_at
        if elapsed < self.fade_duration - 1.0:
            return 1.0
        if elapsed >= self.fade_duration:
            return 0.0
        return max(0.0, self.fade_duration - elapsed)


def _chaikin_smooth(points: List[QPointF], iterations: int) -> List[QPointF]:
    """Apply Chaikin's corner-cutting algorithm for smooth lines.

    Each iteration replaces every segment with two new points at 1/4 and 3/4
    along the segment, producing progressively smoother curves.

    Args:
        points: Input list of QPointF control points.
        iterations: Number of subdivision passes (1-5 clamped internally).

    Returns:
        Smoothed list of QPointF points.
    """
    if len(points) < 3:
        return points

    iters = max(1, min(5, iterations))
    pts = points[:]

    for _ in range(iters):
        new_pts: List[QPointF] = [pts[0]]  # keep first point
        for i in range(len(pts) - 1):
            p0 = pts[i]
            p1 = pts[i + 1]
            q = QPointF(0.75 * p0.x() + 0.25 * p1.x(), 0.75 * p0.y() + 0.25 * p1.y())
            r = QPointF(0.25 * p0.x() + 0.75 * p1.x(), 0.25 * p0.y() + 0.75 * p1.y())
            new_pts.append(q)
            new_pts.append(r)
        new_pts.append(pts[-1])  # keep last point
        pts = new_pts

    return pts


class InkEngine:
    """Manages active and fading screen-drawing ink strokes.

    New features:
      - rainbow_mode: cycles hue across the HSV wheel as strokes are drawn.
      - smooth_lines: applies Chaikin corner-cutting before rendering.
      - smooth_strength: controls subdivision intensity (1-10).
    """

    def __init__(self):
        self.strokes: List[Stroke] = []
        self.current_stroke: Optional[Stroke] = None
        self.current_color = QColor("#EE4F98")
        self.stroke_width = 5.5
        self.auto_fade = True
        self.fade_duration = 3.5
        self.is_drawing = False

        # --- Rainbow mode ---
        self.rainbow_mode: bool = False
        self._hue: float = 0.0  # 0.0-1.0, cycled on each extend_stroke call

        # --- Smooth lines ---
        self.smooth_lines: bool = False
        self.smooth_strength: int = 5  # 1-10; maps to Chaikin iteration count

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rainbow_color(self) -> QColor:
        """Return the current rainbow colour without advancing the hue."""
        return QColor.fromHsvF(self._hue % 1.0, 0.9, 1.0)

    def _chaikin_iterations(self) -> int:
        """Map smooth_strength (1-10) to Chaikin iteration count (1-5)."""
        # strength 1-2 -> 1 iter, 3-4 -> 2, 5-6 -> 3, 7-8 -> 4, 9-10 -> 5
        return max(1, min(5, (self.smooth_strength + 1) // 2))

    # ------------------------------------------------------------------
    # Public API (preserved + extended)
    # ------------------------------------------------------------------

    def begin_stroke(self, pt: QPointF, color: Optional[QColor] = None):
        if self.rainbow_mode:
            c = self._rainbow_color()
        else:
            c = color or self.current_color
        self.current_stroke = Stroke(c, self.stroke_width, self.auto_fade, self.fade_duration)
        self.current_stroke.add_point(pt)
        self.strokes.append(self.current_stroke)
        self.is_drawing = True

    def extend_stroke(self, pt: QPointF):
        if self.current_stroke is not None:
            # Advance rainbow hue
            if self.rainbow_mode:
                self._hue = (self._hue + 0.002) % 1.0
                self.current_stroke.color = self._rainbow_color()

            self.current_stroke.add_point(pt)

    def end_stroke(self):
        if self.current_stroke is not None:
            self.current_stroke.finish()
            self.current_stroke = None
        self.is_drawing = False

    def clear(self):
        self.strokes.clear()
        self.current_stroke = None
        self.is_drawing = False

    def has_active_strokes(self) -> bool:
        return len(self.strokes) > 0

    def update_and_prune(self, now: float):
        """Remove strokes that have completely faded out."""
        if not self.auto_fade:
            return
        self.strokes = [s for s in self.strokes if s.get_alpha(now) > 0.001]

    def draw(self, painter: QPainter):
        now = time.time()
        self.update_and_prune(now)

        for stroke in self.strokes:
            pts = stroke.points
            if len(pts) < 2:
                continue

            alpha_val = stroke.get_alpha(now)
            if alpha_val <= 0.001:
                continue

            # Apply Chaikin smoothing when enabled and strength > 1
            if self.smooth_lines and self.smooth_strength > 1:
                draw_pts = _chaikin_smooth(pts, self._chaikin_iterations())
            else:
                draw_pts = pts

            path = QPainterPath()
            path.moveTo(draw_pts[0])
            if len(draw_pts) == 2:
                path.lineTo(draw_pts[1])
            else:
                for i in range(1, len(draw_pts) - 1):
                    p0 = draw_pts[i]
                    p1 = draw_pts[i + 1]
                    mid = QPointF((p0.x() + p1.x()) * 0.5, (p0.y() + p1.y()) * 0.5)
                    path.quadTo(p0, mid)
                path.lineTo(draw_pts[-1])

            painter.setBrush(Qt.BrushStyle.NoBrush)

            # 1. Outer Glow
            glow_col = QColor(stroke.color)
            glow_col.setAlpha(int(60 * alpha_val))
            glow_pen = QPen(glow_col, stroke.width * 2.4)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            glow_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(glow_pen)
            painter.drawPath(path)

            # 2. Main Stroke
            main_col = QColor(stroke.color)
            main_col.setAlpha(int(240 * alpha_val))
            main_pen = QPen(main_col, stroke.width)
            main_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            main_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(main_pen)
            painter.drawPath(path)

            # 3. Inner Highlight Core
            core_pen = QPen(QColor(255, 255, 255, int(150 * alpha_val)), max(1.5, stroke.width * 0.34))
            core_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            core_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(core_pen)
            painter.drawPath(path)
