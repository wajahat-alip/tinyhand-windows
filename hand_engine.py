# -*- coding: utf-8 -*-
"""
Hand Engine for TinyHand Pro (Windows Edition).
Handles fast hand asset analysis, silhouette shadow caching,
telescopic rod kinematics, and custom animated pointers.
"""

import math
from typing import Dict, List, Optional, Tuple
from PIL import Image
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)


# Ordered catalog of all 36 built-in TinyHand 3D hand styles
HAND_CATALOG: List[Tuple[str, str]] = [
    ("coral", "Coral Vinyl"),
    ("lavender", "Lavender Toy"),
    ("glove", "Cursor Glove"),
    ("plush", "Plush"),
    ("robot", "Robot"),
    ("astro", "Astronaut"),
    ("neon", "Neon Glow"),
    ("chrome", "Chrome"),
    ("holo", "Holographic"),
    ("glass", "Frosted Glass"),
    ("jelly", "Jelly"),
    ("pink", "Bubblegum Pink"),
    ("blue", "Sky Blue"),
    ("mint", "Mint"),
    ("lemon", "Lemon"),
    ("pastel", "Pastel"),
    ("black", "Midnight"),
    ("fuzzy", "Fuzzy"),
    ("knit", "Knit Wool"),
    ("wood", "Carved Wood"),
    ("marble", "Marble"),
    ("terrazzo", "Terrazzo"),
    ("pixel", "Pixel Art"),
    ("lowpoly", "Low Poly"),
    ("skeleton", "Skeleton"),
    ("space", "Space Suit"),
    ("monster", "Monster"),
    ("mech", "Mech"),
    ("water", "Water"),
    ("lava", "Lava"),
    ("grass", "Grass"),
    ("cactus", "Cactus"),
    ("leaf", "Leaf"),
    ("cloud", "Cloud"),
    ("choco", "Chocolate"),
    ("cookie", "Gingerbread"),
]


class HandAsset:
    """Analyzes and caches a PNG hand sprite and its silhouette shadow."""

    def __init__(self, name: str, filepath: str):
        self.name = name
        self.filepath = filepath
        self.pixmap: Optional[QPixmap] = None
        self.shadow_pixmap: Optional[QPixmap] = None
        self.aspect = 1.0
        self.hand_top = 0.0
        self.tip = 0.0
        self.wrist = 0.5
        self.rod_end = 0.95
        self.tip_x = 0.5
        self.rod_x = 0.5
        self.default_ink = QColor("#EE4F98")
        self._analyze()

    def _analyze(self):
        try:
            with Image.open(self.filepath) as raw_img:
                img = raw_img.convert("RGBA")
                orig_w, orig_h = img.size
                self.aspect = orig_w / float(orig_h)

                # Analyze normalized proportions on a fast downsampled grid
                aw = 256
                ah = max(64, int(round(aw / self.aspect)))
                small = img.resize((aw, ah), Image.Resampling.BILINEAR)
                alpha_bytes = small.getchannel("A").tobytes()

                counts = [0] * ah
                row_min = [aw] * ah
                row_max = [0] * ah

                for y in range(ah):
                    row_off = y * aw
                    c = 0
                    rmin = aw
                    rmax = 0
                    for x in range(aw):
                        if alpha_bytes[row_off + x] > 50:
                            c += 1
                            if x < rmin:
                                rmin = x
                            if x > rmax:
                                rmax = x
                    counts[y] = c
                    row_min[y] = rmin
                    row_max[y] = rmax

                top = 0
                for y in range(ah):
                    if counts[y] > 0:
                        top = y
                        break

                search_end = min(ah, top + int(0.45 * ah))
                max_w = max(counts[top:search_end]) if search_end > top else aw // 2

                fist = top
                for y in range(top, ah):
                    if counts[y] > 0.55 * max_w:
                        fist = y
                        break

                wrist = fist
                for y in range(fist, ah):
                    if counts[y] < 0.38 * max_w:
                        wrist = y
                        break

                rod_w = counts[min(ah - 1, wrist + max(1, ah // 50))]
                last_row = ah - 1
                for y in range(ah - 1, -1, -1):
                    if counts[y] > 0:
                        last_row = y
                        break

                rod_end = last_row
                from_y = min(ah - 1, wrist + max(1, ah // 33))
                if rod_w > 0:
                    for y in range(from_y, ah):
                        if counts[y] > 1.8 * rod_w:
                            rod_end = y
                            break

                fah = float(ah)
                self.hand_top = max(0.0, (top - 0.004 * fah) / fah)
                self.tip = top / fah
                self.wrist = max(self.hand_top + 0.05, wrist / fah)
                self.rod_end = rod_end / fah

                tip_row = min(ah - 1, top + max(1, ah // 200))
                if counts[tip_row] > 0:
                    self.tip_x = ((row_min[tip_row] + row_max[tip_row]) * 0.5) / float(aw)
                else:
                    self.tip_x = 0.5

                mid_rod_row = min(ah - 1, (wrist + rod_end) // 2)
                if counts[mid_rod_row] > 0:
                    self.rod_x = ((row_min[mid_rod_row] + row_max[mid_rod_row]) * 0.5) / float(aw)
                else:
                    self.rod_x = 0.5

                self.default_ink = self._detect_dominant_color(small)

            self.pixmap = QPixmap(self.filepath)
            if not self.pixmap.isNull():
                self.shadow_pixmap = self._build_shadow_pixmap(self.pixmap)
        except Exception as exc:
            print(f"Error analyzing {self.filepath}: {exc}")

    @staticmethod
    def _build_shadow_pixmap(source: QPixmap) -> QPixmap:
        """Create a pure-black alpha silhouette of the hand for natural drop shadows."""
        shadow = QPixmap(source.size())
        shadow.fill(Qt.GlobalColor.transparent)
        p = QPainter(shadow)
        p.drawPixmap(0, 0, source)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        p.fillRect(shadow.rect(), QColor(0, 0, 0, 255))
        p.end()
        return shadow

    @staticmethod
    def _detect_dominant_color(small_img: Image.Image) -> QColor:
        try:
            tiny = small_img.resize((32, 32), Image.Resampling.BILINEAR)
            r_tot = g_tot = b_tot = count = 0
            for r, g, b, a in tiny.getdata():
                if a > 150 and (abs(r - g) > 15 or abs(g - b) > 15 or r > 120):
                    r_tot += r
                    g_tot += g
                    b_tot += b
                    count += 1
            if count > 0:
                return QColor(r_tot // count, g_tot // count, b_tot // count)
        except Exception:
            pass
        return QColor("#EE4F98")


class CustomFunnyPointers:
    """Renders custom animated vector pointers aligned precisely to the cursor tip."""

    @staticmethod
    def _begin_aim(painter: QPainter, cursor: QPointF, grip: QPointF) -> float:
        dx = cursor.x() - grip.x()
        dy = cursor.y() - grip.y()
        dist = math.hypot(dx, dy)
        angle_deg = math.degrees(math.atan2(dy, dx)) + 90.0
        painter.save()
        painter.translate(grip.x(), grip.y())
        painter.rotate(angle_deg)
        return max(80.0, dist)

    @staticmethod
    def draw_cat_paw(
        painter: QPainter,
        cursor: QPointF,
        grip: QPointF,
        press_amount: float,
        scale: float = 1.0,
    ):
        """Fluffy cat paw whose center toe pad aligns cleanly at the cursor tip."""
        dist = CustomFunnyPointers._begin_aim(painter, cursor, grip)
        s = scale * (1.0 - 0.05 * press_amount)
        paw_h = 46.0 * s
        paw_w = 56.0 * s
        # Position paw so the top of the front toe row lands right on cursor (-dist)
        paw_top = -dist + (2.0 * press_amount)
        paw_bot = paw_top + paw_h
        arm_w = 34.0 * s
        arm_top = paw_bot - 12.0 * s

        # Soft silhouette shadow
        painter.save()
        painter.translate(8.0 - 4.0 * press_amount, 10.0 - 5.0 * press_amount)
        shadow_col = QColor(0, 0, 0, int(45 + 20 * press_amount))
        sp = QPainterPath()
        sp.addRoundedRect(QRectF(-arm_w / 2, arm_top, arm_w, -arm_top), arm_w * 0.35, arm_w * 0.35)
        sp.addRoundedRect(QRectF(-paw_w / 2, paw_top, paw_w, paw_h), 22 * s, 22 * s)
        painter.fillPath(sp, QBrush(shadow_col))
        painter.restore()

        # Ginger tabby arm
        arm_grad = QLinearGradient(-arm_w / 2, 0, arm_w / 2, 0)
        arm_grad.setColorAt(0.0, QColor("#D97706"))
        arm_grad.setColorAt(0.45, QColor("#F59E0B"))
        arm_grad.setColorAt(1.0, QColor("#B45309"))
        arm_path = QPainterPath()
        arm_path.addRoundedRect(QRectF(-arm_w / 2, arm_top, arm_w, -arm_top), arm_w * 0.35, arm_w * 0.35)
        painter.fillPath(arm_path, QBrush(arm_grad))

        # Tabby stripes
        stripe_pen = QPen(QColor("#92400E"), 2.8 * s)
        stripe_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(stripe_pen)
        arm_len = -arm_top
        for frac in (0.28, 0.48, 0.68):
            sy = -arm_len * frac
            painter.drawLine(QPointF(-arm_w * 0.42, sy), QPointF(-arm_w * 0.12, sy + 5 * s))
            painter.drawLine(QPointF(arm_w * 0.42, sy), QPointF(arm_w * 0.12, sy + 5 * s))

        # Cream fluffy paw cushion
        paw_grad = QRadialGradient(QPointF(0, paw_top + paw_h * 0.45), paw_w * 0.6)
        paw_grad.setColorAt(0.0, QColor("#FFFFFF"))
        paw_grad.setColorAt(0.82, QColor("#F8FAFC"))
        paw_grad.setColorAt(1.0, QColor("#E2E8F0"))

        paw_path = QPainterPath()
        paw_path.addRoundedRect(QRectF(-paw_w / 2, paw_top, paw_w, paw_h), 22 * s, 22 * s)
        painter.fillPath(paw_path, QBrush(paw_grad))
        painter.setPen(QPen(QColor("#CBD5E1"), 1.4))
        painter.drawPath(paw_path)

        # Pink toe beans
        bean_pink = QColor("#FB7185")
        bean_edge = QColor("#E11D48")
        main_bean = QPainterPath()
        main_bean.addRoundedRect(QRectF(-13 * s, paw_bot - 22 * s, 26 * s, 16 * s), 8 * s, 8 * s)
        painter.fillPath(main_bean, QBrush(bean_pink))
        painter.setPen(QPen(QColor(225, 29, 72, 90), 1.0))
        painter.drawPath(main_bean)

        toe_offsets = [(-17 * s, paw_top + 13 * s), (-6 * s, paw_top + 7 * s), (6 * s, paw_top + 7 * s), (17 * s, paw_top + 13 * s)]
        for tx, ty in toe_offsets:
            tp = QPainterPath()
            tp.addEllipse(QRectF(tx - 4.8 * s, ty - 5.5 * s, 9.6 * s, 11 * s))
            painter.fillPath(tp, QBrush(bean_pink))

        # Retractable claws on click
        if press_amount > 0.05:
            claw_pen = QPen(QColor(254, 249, 195, int(240 * press_amount)), 2.4 * s)
            claw_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(claw_pen)
            claw_len = 8.0 * s * press_amount
            for tx, ty in toe_offsets:
                painter.drawLine(QPointF(tx, ty - 5 * s), QPointF(tx, ty - 5 * s - claw_len))

        painter.restore()

    @staticmethod
    def draw_magic_wand(
        painter: QPainter,
        cursor: QPointF,
        grip: QPointF,
        press_amount: float,
        ink_color: QColor,
        scale: float = 1.0,
    ):
        """Tapered dark ebony wizard wand with glowing crystal orb centered at cursor."""
        dist = CustomFunnyPointers._begin_aim(painter, cursor, grip)
        s = scale * (1.0 - 0.03 * press_amount)
        tip_y = -dist
        top_w = 6.5 * s
        bot_w = 17.0 * s

        # Shadow
        painter.save()
        painter.translate(7.0 - 3.5 * press_amount, 9.0 - 4.5 * press_amount)
        sp = QPainterPath()
        sp.moveTo(-bot_w / 2, 0)
        sp.lineTo(-top_w / 2, tip_y)
        sp.lineTo(top_w / 2, tip_y)
        sp.lineTo(bot_w / 2, 0)
        sp.closeSubpath()
        painter.fillPath(sp, QBrush(QColor(0, 0, 0, 45)))
        painter.restore()

        # Ebony wood shaft
        wand_path = QPainterPath()
        wand_path.moveTo(-bot_w / 2, 0)
        wand_path.lineTo(-top_w / 2, tip_y)
        wand_path.lineTo(top_w / 2, tip_y)
        wand_path.lineTo(bot_w / 2, 0)
        wand_path.closeSubpath()

        wood_grad = QLinearGradient(-bot_w / 2, 0, bot_w / 2, 0)
        wood_grad.setColorAt(0.0, QColor("#18100C"))
        wood_grad.setColorAt(0.38, QColor("#54331E"))
        wood_grad.setColorAt(0.72, QColor("#29170D"))
        wood_grad.setColorAt(1.0, QColor("#0F0906"))
        painter.fillPath(wand_path, QBrush(wood_grad))

        # Gold bands
        gold = QColor("#FACC15")
        painter.setPen(QPen(gold, 2.2 * s))
        for y_frac in (0.16, 0.28, 0.55, 0.82, 0.96):
            wy = tip_y * y_frac
            ww = bot_w + (top_w - bot_w) * y_frac
            painter.drawLine(QPointF(-ww / 2, wy), QPointF(ww / 2, wy))

        # Glowing crystal tip centered at (0, tip_y)
        glow_r = (14.0 + 10.0 * press_amount) * s
        tip_glow = QRadialGradient(QPointF(0, tip_y), glow_r)
        tip_glow.setColorAt(0.0, QColor(255, 255, 255, 255))
        tip_glow.setColorAt(0.3, QColor(125, 211, 252, 220))
        tip_glow.setColorAt(0.65, QColor(ink_color.red(), ink_color.green(), ink_color.blue(), 110))
        tip_glow.setColorAt(1.0, QColor(ink_color.red(), ink_color.green(), ink_color.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(tip_glow))
        painter.drawEllipse(QPointF(0, tip_y), glow_r, glow_r)

        # Star flare on press
        if press_amount > 0.08:
            star = 20.0 * s * press_amount
            diag = star * 0.65
            flare_pen = QPen(QColor(255, 255, 255, int(245 * press_amount)), 2.2 * s)
            flare_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(flare_pen)
            painter.drawLine(QPointF(0, tip_y - star), QPointF(0, tip_y + star))
            painter.drawLine(QPointF(-star, tip_y), QPointF(star, tip_y))
            painter.drawLine(QPointF(-diag, tip_y - diag), QPointF(diag, tip_y + diag))
            painter.drawLine(QPointF(-diag, tip_y + diag), QPointF(diag, tip_y - diag))

        painter.restore()

    @staticmethod
    def draw_boxing_glove(
        painter: QPainter,
        cursor: QPointF,
        grip: QPointF,
        press_amount: float,
        scale: float = 1.0,
    ):
        """Comic spring-loaded crimson boxing glove aligned to cursor."""
        dist = CustomFunnyPointers._begin_aim(painter, cursor, grip)
        s = scale
        gw = 54.0 * s
        gh = 62.0 * s
        glove_top = -dist - (8.0 * s * press_amount)
        glove_bot = glove_top + gh

        # Scissor spring coils from grip (0) up to glove cuff (glove_bot)
        spring_len = max(40.0, -glove_bot)
        num_coils = 14
        coil_w = 22.0 * s
        coil_step = spring_len / num_coils

        spring_pen = QPen(QColor("#94A3B8"), 3.2 * s)
        spring_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(spring_pen)
        for i in range(num_coils):
            y1 = -i * coil_step
            y2 = -(i + 1) * coil_step
            x_sign = 1 if i % 2 == 0 else -1
            painter.drawLine(QPointF(x_sign * coil_w * 0.5, y1), QPointF(-x_sign * coil_w * 0.5, y2))

        # Drop shadow under glove
        painter.save()
        painter.translate(8.0 - 4.0 * press_amount, 10.0 - 5.0 * press_amount)
        sp = QPainterPath()
        sp.addRoundedRect(QRectF(-gw / 2, glove_top, gw, gh), 22 * s, 22 * s)
        painter.fillPath(sp, QBrush(QColor(0, 0, 0, 50)))
        painter.restore()

        # Crimson leather glove body
        glove_grad = QRadialGradient(QPointF(-8 * s, glove_top + gh * 0.35), gw * 0.9)
        glove_grad.setColorAt(0.0, QColor("#F87171"))
        glove_grad.setColorAt(0.45, QColor("#DC2626"))
        glove_grad.setColorAt(1.0, QColor("#7F1D1D"))

        glove_path = QPainterPath()
        glove_path.addRoundedRect(QRectF(-gw / 2, glove_top, gw, gh), 22 * s, 22 * s)

        thumb_path = QPainterPath()
        thumb_path.addRoundedRect(QRectF(-gw / 2 - 11 * s, glove_top + gh * 0.28, 18 * s, 28 * s), 9 * s, 9 * s)

        painter.setPen(QPen(QColor("#7F1D1D"), 1.8))
        painter.fillPath(thumb_path, QBrush(glove_grad))
        painter.drawPath(thumb_path)
        painter.fillPath(glove_path, QBrush(glove_grad))
        painter.drawPath(glove_path)

        # White padded cuff
        cuff_rect = QRectF(-gw / 2 - 2 * s, glove_bot - 12 * s, gw + 4 * s, 14 * s)
        cuff_path = QPainterPath()
        cuff_path.addRoundedRect(cuff_rect, 4 * s, 4 * s)
        painter.fillPath(cuff_path, QBrush(QColor("#F8FAFC")))
        painter.setPen(QPen(QColor("#CBD5E1"), 1.3))
        painter.drawPath(cuff_path)

        painter.restore()

    @staticmethod
    def draw_laser_dot(
        painter: QPainter,
        cursor: QPointF,
        press_amount: float,
        ink_color: QColor,
        scale: float = 1.0,
    ):
        """High-contrast sci-fi laser dot with soft bloom and expanding tap pulse."""
        r = (6.5 + 2.5 * press_amount) * scale

        # Expanding sonar ring on tap
        ripple_r = r * (3.0 + 2.4 * press_amount)
        ripple_alpha = int(150 * (1.0 - 0.35 * press_amount))
        ripple_pen = QPen(QColor(ink_color.red(), ink_color.green(), ink_color.blue(), ripple_alpha), 1.6)
        painter.setPen(ripple_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(cursor, ripple_r, ripple_r)

        # Bloom halo
        aura_r = r * 2.6
        aura = QRadialGradient(cursor, aura_r)
        aura.setColorAt(0.0, QColor(ink_color.red(), ink_color.green(), ink_color.blue(), 235))
        aura.setColorAt(0.5, QColor(ink_color.red(), ink_color.green(), ink_color.blue(), 95))
        aura.setColorAt(1.0, QColor(ink_color.red(), ink_color.green(), ink_color.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(aura))
        painter.drawEllipse(cursor, aura_r, aura_r)

        # Hot white-to-color core
        core = QRadialGradient(cursor, r)
        core.setColorAt(0.0, QColor(255, 255, 255, 255))
        core.setColorAt(0.55, QColor(ink_color.red(), ink_color.green(), ink_color.blue(), 255))
        core.setColorAt(1.0, QColor(ink_color.red(), ink_color.green(), ink_color.blue(), 160))
        painter.setBrush(QBrush(core))
        painter.drawEllipse(cursor, r, r)
