# -*- coding: utf-8 -*-
"""
Settings Window for TinyHand Windows.
Centralized translucent dual-theme architecture (Dark Graphite & Soft Light Gray):
  - Single root QSS stylesheet driven by DARK_THEME / LIGHT_THEME dictionaries
  - Zero scattered inline child stylesheets; instant synchronized theme switching
  - Native Windows DWM blur-behind translucency on rounded frameless window
  - Single crisp Sun/Moon vector icon toggle in top-right title bar
  - 6 colorful rounded-square 24x24 vector sidebar navigation badges
  - Searchable 40+ Pointer Gallery, Style & FX, Ink & Draw, Sound, and About/Updater
"""

import math
import os
import shutil
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from PyQt6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    QThread,
    QTimer,
    QUrl,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QDesktopServices,
    QFont,
    QGuiApplication,
    QKeyEvent,
    QKeySequence,
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

from config import APP_NAME, APP_VERSION
from hand_engine import HAND_CATALOG, CustomFunnyPointers, HandAsset
from icons import make_sidebar_badge_pixmap, make_svg_icon
from ink_engine import InkEngine
from overlay_window import ClickRipple, ComicBubble


# ---------------------------------------------------------------------------
# Background Worker: Check for GitHub Releases asynchronously
# ---------------------------------------------------------------------------
class UpdateCheckerThread(QThread):
    """Background worker to query GitHub Releases without blocking the UI thread."""

    check_finished = pyqtSignal(dict)

    def __init__(
        self,
        current_version: str = "1.0.0",
        repo: str = "wajahat-alip/tinyhand-windows",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.current_version = str(current_version).lstrip("v")
        self.repo = repo

    def run(self):
        import json
        import urllib.request

        api_url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "TinyHand-Windows-Updater",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                tag_name = data.get("tag_name", "").lstrip("v")
                html_url = data.get("html_url", f"https://github.com/{self.repo}/releases")
                body = data.get("body", "")

                is_newer = False
                if tag_name:
                    curr_parts = [int(p) for p in self.current_version.split(".") if p.isdigit()]
                    tag_parts = [int(p) for p in tag_name.split(".") if p.isdigit()]
                    while len(curr_parts) < 3:
                        curr_parts.append(0)
                    while len(tag_parts) < 3:
                        tag_parts.append(0)
                    is_newer = tag_parts > curr_parts

                download_url = html_url
                for asset in data.get("assets", []):
                    if asset.get("name", "").endswith(".exe"):
                        download_url = asset.get("browser_download_url", html_url)
                        break

                self.check_finished.emit(
                    {
                        "success": True,
                        "latest_version": tag_name or APP_VERSION,
                        "is_new": is_newer,
                        "download_url": download_url,
                        "release_url": html_url,
                        "notes": (body[:260] + "...") if len(body) > 260 else body,
                        "error": "",
                    }
                )
        except Exception as e:
            self.check_finished.emit(
                {
                    "success": False,
                    "latest_version": self.current_version,
                    "is_new": False,
                    "download_url": f"https://github.com/{self.repo}/releases",
                    "release_url": f"https://github.com/{self.repo}/releases",
                    "notes": "",
                    "error": str(e),
                }
            )


# ---------------------------------------------------------------------------
# Centralized Theme Dictionaries: DARK_THEME & LIGHT_THEME
# ---------------------------------------------------------------------------
DARK_THEME: Dict[str, Any] = {
    "mode": "dark",
    # Window translucent glass backdrop
    "win_grad_start": QColor(24, 26, 31, 230),
    "win_grad_end": QColor(18, 20, 25, 238),
    "win_border": QColor(47, 51, 61, 210),
    # Structural chrome & dividers
    "c_titlebar": "rgba(20, 22, 27, 225)",
    "c_sidebar": "rgba(20, 22, 27, 220)",
    "c_sidebar_border": "#2F333D",
    "title_btn_hover": "rgba(255, 255, 255, 22)",
    # Surfaces & controls
    "c_surface": "rgba(30, 32, 37, 220)",
    "c_surface_hover": "rgba(37, 40, 48, 235)",
    "c_control_bg": "rgba(37, 40, 48, 220)",
    "c_input_bg": "#1E2025",
    "c_input_focus_bg": "#252830",
    "c_combo_popup_bg": "#1E2025",
    "c_border": "#2F333D",
    "c_border_light": "#454B59",
    "c_accent": "#3B82F6",
    "c_accent_light": "#60A5FA",
    "c_accent_hover": "#2563EB",
    "c_accent_fg": "#F8FAFC",
    "c_checked_bg": "#1E3A8A",
    "c_checked_fg": "#93C5FD",
    "c_checked_bd": "#3B82F6",
    # Typography
    "c_text": "#F3F4F6",
    "c_text_sec": "#D1D5DB",
    "c_text_muted": "#9CA3AF",
    "c_tile_sel_txt": "#F3F4F6",
    # Semantic
    "c_track_off": "#2F333D",
    "c_success": "#10B981",
    "c_danger": "#EF4444",
    "danger_bg": "rgba(239, 68, 68, 38)",
    "danger_fg": "#FCA5A5",
    "danger_bd": "rgba(239, 68, 68, 110)",
    "danger_hbg": "#DC2626",
    "danger_hfg": "#F8FAFC",
    "success_bg": "#064E3B",
    "success_fg": "#6EE7B7",
    "scroll_bg": "#3B404D",
    "scroll_hover": "#525866",
    # Segmented buttons & custom rows
    "seg_btn_fg": "#D1D5DB",
    "seg_btn_hover_bg": "#2E3547",
    "seg_btn_hover_fg": "#F3F4F6",
    "use_btn_bg": "#1E3A8A",
    "use_btn_fg": "#93C5FD",
    # QPainter shapes
    "ctrl_bg": QColor(37, 40, 48, 220),
    "card_bg": QColor(30, 32, 37, 205),
    "card_bg_hover": QColor(37, 40, 48, 225),
    "card_border": QColor(47, 51, 61, 195),
    "card_border_hover": QColor(69, 75, 89, 225),
    "tile_bg": QColor(30, 32, 37, 200),
    "tile_bg_hover": QColor(37, 40, 48, 225),
    "tile_border": QColor(47, 51, 61, 185),
    "tile_border_hover": QColor(69, 75, 89, 220),
    "tile_bg_selected": QColor(30, 48, 82, 230),
    "tile_border_selected": QColor("#3B82F6"),
    "stage_bg": QColor(17, 19, 24, 235),
    "stage_dot": QColor(255, 255, 255, 20),
    "stage_border": QColor(47, 51, 61, 200),
    "nav_active_bg": QColor(59, 130, 246, 42),
    "nav_active_border": QColor(59, 130, 246, 135),
    "nav_hover_bg": QColor(37, 40, 48, 175),
    "nav_hover_border": QColor(47, 51, 61, 160),
}

LIGHT_THEME: Dict[str, Any] = {
    "mode": "light",
    # Soft translucent Light Gray glass backdrop (zero stark #FFFFFF)
    "win_grad_start": QColor(230, 232, 236, 225),
    "win_grad_end": QColor(220, 224, 230, 232),
    "win_border": QColor(194, 199, 208, 230),
    # Structural chrome & dividers
    "c_titlebar": "rgba(222, 226, 232, 220)",
    "c_sidebar": "rgba(218, 222, 228, 218)",
    "c_sidebar_border": "#C2C7D0",
    "title_btn_hover": "rgba(24, 26, 31, 20)",
    # Surfaces & controls
    "c_surface": "rgba(220, 224, 230, 215)",
    "c_surface_hover": "rgba(209, 213, 219, 235)",
    "c_control_bg": "rgba(209, 213, 219, 215)",
    "c_input_bg": "#DCE0E6",
    "c_input_focus_bg": "#E6E8EC",
    "c_combo_popup_bg": "#DCE0E6",
    "c_border": "#C2C7D0",
    "c_border_light": "#9CA3AF",
    "c_accent": "#2563EB",
    "c_accent_light": "#3B82F6",
    "c_accent_hover": "#1D4ED8",
    "c_accent_fg": "#F8FAFC",
    "c_checked_bg": "#2563EB",
    "c_checked_fg": "#F8FAFC",
    "c_checked_bd": "#1D4ED8",
    # Typography
    "c_text": "#181A1F",
    "c_text_sec": "#374151",
    "c_text_muted": "#6B7280",
    "c_tile_sel_txt": "#1D4ED8",
    # Semantic
    "c_track_off": "#BFC5CF",
    "c_success": "#059669",
    "c_danger": "#DC2626",
    "danger_bg": "rgba(220, 38, 38, 28)",
    "danger_fg": "#B91C1C",
    "danger_bd": "rgba(220, 38, 38, 120)",
    "danger_hbg": "#DC2626",
    "danger_hfg": "#F8FAFC",
    "success_bg": "#D1FAE5",
    "success_fg": "#065F46",
    "scroll_bg": "#B8BFC9",
    "scroll_hover": "#8D96A5",
    # Segmented buttons & custom rows
    "seg_btn_fg": "#4B5563",
    "seg_btn_hover_bg": "#C8CED8",
    "seg_btn_hover_fg": "#181A1F",
    "use_btn_bg": "rgba(37, 99, 235, 28)",
    "use_btn_fg": "#1D4ED8",
    # QPainter shapes (soft light gray, zero stark white)
    "ctrl_bg": QColor(209, 213, 219, 220),
    "card_bg": QColor(226, 229, 234, 200),
    "card_bg_hover": QColor(232, 235, 240, 220),
    "card_border": QColor(194, 199, 208, 215),
    "card_border_hover": QColor(156, 163, 175, 230),
    "tile_bg": QColor(220, 224, 230, 215),
    "tile_bg_hover": QColor(228, 232, 238, 235),
    "tile_border": QColor(194, 199, 208, 205),
    "tile_border_hover": QColor(156, 163, 175, 225),
    "tile_bg_selected": QColor(205, 221, 248, 230),
    "tile_border_selected": QColor("#2563EB"),
    "stage_bg": QColor(216, 220, 227, 230),
    "stage_dot": QColor(148, 156, 168, 120),
    "stage_border": QColor(194, 199, 208, 220),
    "nav_active_bg": QColor(37, 99, 235, 34),
    "nav_active_border": QColor(37, 99, 235, 130),
    "nav_hover_bg": QColor(194, 199, 208, 110),
    "nav_hover_border": QColor(194, 199, 208, 160),
}

THEMES: Dict[str, Dict[str, Any]] = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
}

CURRENT_THEME: Dict[str, Any] = DARK_THEME


def set_active_theme(mode: str) -> Dict[str, Any]:
    global CURRENT_THEME
    if mode not in THEMES:
        mode = "dark"
    CURRENT_THEME = THEMES[mode]
    return CURRENT_THEME


def build_root_stylesheet(t: Dict[str, Any]) -> str:
    """Build one cohesive root QSS stylesheet governing every widget in the window."""
    return f"""
    #SettingsRoot {{
        background: transparent;
    }}
    #TitleBar {{
        background: {t['c_titlebar']};
        border-top-left-radius: 13px;
        border-top-right-radius: 13px;
    }}
    #TitleBadge {{
        background: {t['c_accent']};
        border-radius: 6px;
    }}
    #TitleLabel {{
        color: {t['c_text']};
        font-size: 13px;
        font-weight: 600;
        background: transparent;
        border: none;
        font-family: 'Segoe UI', sans-serif;
    }}
    #ThemeToggleBtn, #TitleMinBtn, #TitleCloseBtn {{
        background: transparent;
        border: none;
        border-radius: 6px;
    }}
    #ThemeToggleBtn:hover, #TitleMinBtn:hover {{
        background: {t['title_btn_hover']};
    }}
    #TitleCloseBtn:hover {{
        background: #DC2626;
    }}
    #Sidebar {{
        background: {t['c_sidebar']};
        border-bottom-left-radius: 13px;
    }}
    #PreviewDock {{
        background: {t['c_sidebar']};
        border-bottom-right-radius: 13px;
    }}
    #PreviewSummaryPill {{
        background: {t['c_surface']};
        border: 1px solid {t['c_border']};
        border-radius: 9px;
    }}
    #AboutHeroBadge {{
        background: {t['c_accent']};
        border-radius: 16px;
    }}
    #UpdateResultFrame {{
        background: {t['c_control_bg']};
        border: 1px solid {t['c_border']};
        border-radius: 8px;
    }}
    #CustomUploadRow {{
        background: {t['c_control_bg']};
        border: 1px solid {t['c_border']};
        border-radius: 7px;
    }}
    QWidget[role="divider"] {{
        background: {t['c_sidebar_border']};
        border: none;
    }}
    QFrame[role="hsep"] {{
        background: {t['c_sidebar_border']};
        border: none;
        margin: 3px 0;
    }}
    #PagesStack, #ScrollArea, #ScrollViewport, #ScrollInner, QWidget[role="transparentWrap"] {{
        background: transparent;
        border: none;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 4px 2px 4px 0;
    }}
    QScrollBar::handle:vertical {{
        background: {t['scroll_bg']};
        border-radius: 3px;
        min-height: 28px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {t['scroll_hover']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}

    /* Typography roles */
    QLabel {{
        background: transparent;
        border: none;
        font-family: 'Segoe UI', sans-serif;
    }}
    QLabel[role="text"] {{ color: {t['c_text']}; font-weight: 400; }}
    QLabel[role="textSec"] {{ color: {t['c_text_sec']}; font-weight: 400; }}
    QLabel[role="textMuted"] {{ color: {t['c_text_muted']}; font-weight: 400; }}
    QLabel[role="pageTitle"] {{ color: {t['c_text']}; font-weight: 600; }}
    QLabel[role="sectionLabel"] {{ color: {t['c_text_sec']}; font-size: 12px; font-weight: 600; padding-top: 2px; }}
    QLabel[role="tileTitle"] {{ color: {t['c_text_sec']}; font-size: 10px; font-weight: 500; }}
    QLabel[role="tileTitleSel"] {{ color: {t['c_tile_sel_txt']}; font-size: 10px; font-weight: 600; }}
    QLabel[role="soundTitle"] {{ color: {t['c_text_sec']}; font-size: 11px; font-weight: 500; }}
    QLabel[role="soundTitleHover"] {{ color: {t['c_text']}; font-size: 11px; font-weight: 500; }}
    QLabel[role="soundTitleSel"] {{ color: {t['c_accent']}; font-size: 11px; font-weight: 600; }}
    QLabel[role="statusSuccess"] {{ color: {t['c_success']}; font-weight: 600; }}
    QLabel[role="statusDanger"] {{ color: {t['c_danger']}; font-weight: 600; }}
    QLabel[role="statusAccent"] {{ color: {t['c_accent_light']}; font-weight: 600; }}
    QLabel[bold="true"] {{ font-weight: 600; }}
    QLabel[sz="10"] {{ font-size: 10px; }}
    QLabel[sz="11"] {{ font-size: 11px; }}
    QLabel[sz="12"] {{ font-size: 12px; }}
    QLabel[sz="13"] {{ font-size: 13px; }}
    QLabel[sz="18"] {{ font-size: 18px; }}
    QLabel[sz="20"] {{ font-size: 20px; }}

    /* Action buttons */
    QPushButton[role="btnDefault"] {{
        background: {t['c_control_bg']};
        color: {t['c_text']};
        border: 1px solid {t['c_border']};
        border-radius: 7px;
        padding: 7px 14px;
        font-weight: 500;
        font-size: 12px;
        font-family: 'Segoe UI', sans-serif;
    }}
    QPushButton[role="btnDefault"]:hover {{
        background: {t['c_surface_hover']};
        color: {t['c_text']};
        border-color: {t['c_border_light']};
    }}
    QPushButton[role="btnDefault"][copied="true"] {{
        background: {t['success_bg']};
        color: {t['success_fg']};
        border: 1px solid {t['c_success']};
        font-weight: 600;
    }}
    QPushButton[role="btnPrimary"] {{
        background: {t['c_accent']};
        color: {t['c_accent_fg']};
        border: 1px solid {t['c_accent_light']};
        border-radius: 7px;
        padding: 7px 14px;
        font-weight: 600;
        font-size: 12px;
        font-family: 'Segoe UI', sans-serif;
    }}
    QPushButton[role="btnPrimary"]:hover {{
        background: {t['c_accent_hover']};
        border-color: {t['c_accent_light']};
    }}
    QPushButton[role="btnPrimary"]:disabled {{
        background: {t['c_border']};
        color: {t['c_text_muted']};
        border-color: {t['c_border']};
    }}
    QPushButton[role="btnOutline"] {{
        background: transparent;
        color: {t['c_text']};
        border: 1px solid {t['c_border']};
        border-radius: 7px;
        padding: 7px 14px;
        font-weight: 500;
        font-size: 12px;
        font-family: 'Segoe UI', sans-serif;
    }}
    QPushButton[role="btnOutline"]:hover {{
        background: {t['c_surface_hover']};
        color: {t['c_text']};
        border-color: {t['c_border_light']};
    }}
    QPushButton[role="btnDanger"] {{
        background: {t['danger_bg']};
        color: {t['danger_fg']};
        border: 1px solid {t['danger_bd']};
        border-radius: 7px;
        padding: 7px 14px;
        font-weight: 600;
        font-size: 12px;
        font-family: 'Segoe UI', sans-serif;
    }}
    QPushButton[role="btnDanger"]:hover {{
        background: {t['danger_hbg']};
        color: {t['danger_hfg']};
        border-color: #EF4444;
    }}
    QPushButton[role="btnUse"] {{
        background: {t['use_btn_bg']};
        color: {t['use_btn_fg']};
        border: 1px solid {t['c_accent_light']};
        border-radius: 5px;
        padding: 3px 10px;
        font-size: 11px;
        font-weight: 600;
        font-family: 'Segoe UI', sans-serif;
    }}
    QPushButton[role="btnUse"]:hover {{
        background: {t['c_accent']};
        color: {t['c_accent_fg']};
    }}
    QPushButton[role="btnRemove"] {{
        background: transparent;
        color: {t['c_danger']};
        border: none;
        padding: 3px 6px;
        font-size: 11px;
        font-weight: 500;
        font-family: 'Segoe UI', sans-serif;
    }}
    QPushButton[role="btnRemove"]:hover {{
        color: {t['c_text']};
    }}
    QPushButton[role="previewCtrl"] {{
        background: {t['c_control_bg']};
        color: {t['c_text']};
        border: 1px solid {t['c_border']};
        border-radius: 7px;
        padding: 3px 8px;
        font-size: 11px;
        font-weight: 500;
        font-family: 'Segoe UI', sans-serif;
    }}
    QPushButton[role="previewCtrl"]:hover {{
        background: {t['c_surface_hover']};
        color: {t['c_text']};
        border-color: {t['c_border_light']};
    }}
    QPushButton[role="previewCtrl"]:checked {{
        background: {t['c_checked_bg']};
        color: {t['c_checked_fg']};
        border-color: {t['c_checked_bd']};
        font-weight: 600;
    }}

    /* Hotkey button */
    HotkeyButton {{
        background: {t['c_control_bg']};
        color: {t['c_text']};
        border: 1px solid {t['c_border']};
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 10px;
        font-family: 'Segoe UI', sans-serif;
    }}
    HotkeyButton:hover {{
        border-color: {t['c_border_light']};
        background: {t['c_surface_hover']};
        color: {t['c_text']};
    }}
    HotkeyButton[recording="true"] {{
        background: #1E3A8A;
        color: #F8FAFC;
        border: 1px solid #60A5FA;
    }}

    /* SegmentedControl inner pills */
    SegmentedControl QPushButton {{
        background: transparent;
        color: {t['seg_btn_fg']};
        border: none;
        border-radius: 6px;
        padding: 3px 11px;
        font-size: 11px;
        font-weight: 500;
        font-family: 'Segoe UI', sans-serif;
    }}
    SegmentedControl QPushButton:hover {{
        color: {t['seg_btn_hover_fg']};
        background: {t['seg_btn_hover_bg']};
    }}
    SegmentedControl QPushButton:checked {{
        background: {t['c_accent']};
        color: {t['c_accent_fg']};
        font-weight: 600;
    }}

    /* Inputs & Comboboxes */
    QLineEdit {{
        background: {t['c_input_bg']};
        color: {t['c_text']};
        border: 1px solid {t['c_border']};
        border-radius: 8px;
        padding: 3px 10px;
        font-size: 12px;
        font-family: 'Segoe UI', sans-serif;
    }}
    QLineEdit:focus {{
        border: 1px solid {t['c_accent_light']};
        background: {t['c_input_focus_bg']};
    }}
    QComboBox {{
        background: {t['c_control_bg']};
        color: {t['c_text']};
        border: 1px solid {t['c_border']};
        border-radius: 7px;
        padding: 4px 10px;
        font-size: 12px;
        font-family: 'Segoe UI', sans-serif;
    }}
    QComboBox:hover {{
        border-color: {t['c_border_light']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    QComboBox QAbstractItemView {{
        background: {t['c_combo_popup_bg']};
        color: {t['c_text']};
        border: 1px solid {t['c_border']};
        selection-background-color: {t['c_accent']};
        selection-color: {t['c_accent_fg']};
    }}

    /* Dialogs */
    QMessageBox {{
        background: {t['c_combo_popup_bg']};
        color: {t['c_text']};
    }}
    QMessageBox QLabel {{
        color: {t['c_text']};
        font-size: 12px;
    }}
    QMessageBox QPushButton {{
        background: {t['c_control_bg']};
        color: {t['c_text']};
        border: 1px solid {t['c_border']};
        border-radius: 6px;
        padding: 5px 14px;
        font-size: 12px;
        min-width: 68px;
    }}
    QMessageBox QPushButton:hover {{
        background: {t['c_surface_hover']};
        border-color: {t['c_border_light']};
    }}
    """


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
# Layout & Typography Builders (Zero Inline Stylesheets)
# ---------------------------------------------------------------------------
def _page_scroll() -> Tuple[QScrollArea, QWidget, QVBoxLayout]:
    scroll = QScrollArea()
    scroll.setObjectName("ScrollArea")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    vp = scroll.viewport()
    vp.setObjectName("ScrollViewport")
    vp.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    vp.setAutoFillBackground(False)
    vp.setStyleSheet("#ScrollViewport { background: transparent; }")

    inner = QWidget()
    inner.setObjectName("ScrollInner")
    inner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    vbox = QVBoxLayout(inner)
    vbox.setContentsMargins(24, 20, 22, 28)
    vbox.setSpacing(14)
    scroll.setWidget(inner)
    return scroll, inner, vbox


def _label(
    text: str,
    size: int = 12,
    role: str = "text",
    bold: bool = False,
    muted: bool = False,
) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("role", "textMuted" if muted else role)
    lbl.setProperty("sz", str(size))
    lbl.setProperty("bold", "true" if bold else "false")
    return lbl


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("role", "sectionLabel")
    return lbl


def _add_hsep(layout: QVBoxLayout):
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setFixedHeight(1)
    sep.setProperty("role", "hsep")
    sep.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    layout.addWidget(sep)


def _transparent_wrap() -> QWidget:
    w = QWidget()
    w.setProperty("role", "transparentWrap")
    w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    return w


# ===========================================================================
# Custom Controls
# ===========================================================================
class NavRailButton(QWidget):
    """Sidebar navigation item with colorful 24x24px rounded-square vector badge."""

    clicked = pyqtSignal()

    def __init__(
        self,
        icon_key: str,
        label: str,
        badge_color: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.icon_key = icon_key
        self.label = label
        self.badge_color = badge_color
        self._checked = False
        self._hovered = False
        self.setFixedHeight(40)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._badge_pm = make_sidebar_badge_pixmap(icon_key, badge_color, size=24, radius=6.0)

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
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        rect = QRectF(10, 2, self.width() - 20, self.height() - 4)
        pill = QPainterPath()
        pill.addRoundedRect(rect, 9.0, 9.0)

        if self._checked:
            p.fillPath(pill, CURRENT_THEME["nav_active_bg"])
            p.setPen(QPen(CURRENT_THEME["nav_active_border"], 1.0))
            p.drawPath(pill)
            bar_path = QPainterPath()
            bar_path.addRoundedRect(QRectF(12, 10, 3, self.height() - 20), 1.5, 1.5)
            p.fillPath(bar_path, QColor(CURRENT_THEME["c_accent"]))
        elif self._hovered:
            p.fillPath(pill, CURRENT_THEME["nav_hover_bg"])
            p.setPen(QPen(CURRENT_THEME["nav_hover_border"], 1.0))
            p.drawPath(pill)

        badge_y = int((self.height() - 24) * 0.5)
        p.drawPixmap(QRect(20, badge_y, 24, 24), self._badge_pm)

        txt_col = (
            QColor(CURRENT_THEME["c_accent"])
            if self._checked
            else (QColor(CURRENT_THEME["c_text"]) if self._hovered else QColor(CURRENT_THEME["c_text_sec"]))
        )
        weight = QFont.Weight.DemiBold if self._checked else QFont.Weight.Medium
        p.setFont(QFont("Segoe UI", 9, weight))
        p.setPen(txt_col)
        p.drawText(
            QRectF(53, 0, self.width() - 64, self.height()),
            Qt.AlignmentFlag.AlignVCenter,
            self.label,
        )
        p.end()


class SettingsGroup(QWidget):
    """Translucent card container with rounded border rendered dynamically from theme."""

    def __init__(self, body_layout, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._hovered = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        body = _transparent_wrap()
        body_layout.setContentsMargins(16, 14, 16, 14)
        body.setLayout(body_layout)
        outer.addWidget(body)

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 10.0, 10.0)

        card_fill = CURRENT_THEME["card_bg_hover"] if self._hovered else CURRENT_THEME["card_bg"]
        p.fillPath(path, card_fill)

        border_col = CURRENT_THEME["card_border_hover"] if self._hovered else CURRENT_THEME["card_border"]
        p.setPen(QPen(border_col, 1.1))
        p.drawPath(path)
        p.end()


class CleanToggle(QWidget):
    """Crisp 38 x 22 px animated sliding switch."""

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
        p.setBrush(QColor(CURRENT_THEME["c_accent"]) if self._checked else QColor(CURRENT_THEME["c_track_off"]))
        p.drawRoundedRect(track_r, 9.5, 9.5)

        if self._checked:
            knob_col = QColor("#F8FAFC")
        else:
            knob_col = QColor("#F3F4F6") if CURRENT_THEME["mode"] == "dark" else QColor("#E6E8EC")
        p.setBrush(knob_col)
        p.drawEllipse(QPointF(self._knob_x, 11.0), 7.0, 7.0)
        p.end()


class CleanSlider(QWidget):
    """Refined 4 px track slider with accent fill and crisp handle."""

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
        p.setBrush(QColor(CURRENT_THEME["c_track_off"]))
        p.drawRoundedRect(t, 2.0, 2.0)

        if tx > t.left():
            p.setBrush(QColor(CURRENT_THEME["c_accent"]))
            p.drawRoundedRect(QRectF(t.left(), t.top(), tx - t.left(), t.height()), 2.0, 2.0)

        p.setBrush(QColor(0, 0, 0, 70))
        p.drawEllipse(QPointF(tx, cy + 1.0), 7.5, 7.5)

        r = 7.0 if (self._dragging or self._hovered) else 6.2
        thumb_col = QColor("#F3F4F6") if CURRENT_THEME["mode"] == "dark" else QColor("#181A1F")
        p.setBrush(thumb_col)
        p.setPen(QPen(QColor(0, 0, 0, 50), 1.0))
        p.drawEllipse(QPointF(tx, cy), r, r)
        p.end()


class SegmentedControl(QWidget):
    """Segmented pill selector styled via root stylesheet."""

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
        p.fillPath(path, CURRENT_THEME["ctrl_bg"])
        p.setPen(QPen(QColor(CURRENT_THEME["c_border"]), 1.0))
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
        is_dark = CURRENT_THEME["mode"] == "dark"

        if self._checked:
            sel_ring = QColor("#F3F4F6") if is_dark else QColor("#181A1F")
            p.setPen(QPen(sel_ring, 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(c, 14.0, 14.0)
        elif self._hovered:
            hov_ring = QColor(255, 255, 255, 120) if is_dark else QColor(0, 0, 0, 100)
            p.setPen(QPen(hov_ring, 1.3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(c, 13.5, 13.5)

        base_pen = QPen(QColor(255, 255, 255, 35) if is_dark else QColor(0, 0, 0, 35), 1.0)
        p.setPen(base_pen)
        if self.key == "rainbow":
            cg = QConicalGradient(c, 0)
            for pos, col in [
                (0.0, "#EF4444"),
                (0.17, "#F59E0B"),
                (0.33, "#22C55E"),
                (0.50, "#06B6D4"),
                (0.67, "#3B82F6"),
                (0.83, "#A855F7"),
                (1.0, "#EF4444"),
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
            p.setPen(QColor("#F8FAFC"))
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "A")
        p.end()


class PointerThumb(QWidget):
    """88 x 102 pointer tile displaying cropped 3D hand or vector art."""

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
        layout.addWidget(self._img_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self._pixmap = build_hand_thumb_pixmap(key, assets_dir, hand_assets, 76, 62)
        self._apply_pixmap()

        self._name_lbl = QLabel(name)
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_lbl.setWordWrap(True)
        self._name_lbl.setProperty("role", "tileTitle")
        layout.addWidget(self._name_lbl)

    def _apply_pixmap(self):
        if self._pixmap and not self._pixmap.isNull():
            self._img_label.setPixmap(self._pixmap)
        else:
            self._img_label.setPixmap(
                make_svg_icon("hand", CURRENT_THEME["c_accent_light"], 28).pixmap(QSize(28, 28))
            )

    def update_theme(self):
        if self._pixmap is None or self._pixmap.isNull():
            self._apply_pixmap()
        self.update()

    def setSelected(self, state: bool):
        self._selected = state
        self._name_lbl.setProperty("role", "tileTitleSel" if state else "tileTitle")
        st = self._name_lbl.style()
        if st:
            st.unpolish(self._name_lbl)
            st.polish(self._name_lbl)
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
            p.fillPath(path, CURRENT_THEME["tile_bg_selected"])
            p.setPen(QPen(CURRENT_THEME["tile_border_selected"], 1.8))
        elif self._hovered:
            p.fillPath(path, CURRENT_THEME["tile_bg_hover"])
            p.setPen(QPen(CURRENT_THEME["tile_border_hover"], 1.0))
        else:
            p.fillPath(path, CURRENT_THEME["tile_bg"])
            p.setPen(QPen(CURRENT_THEME["tile_border"], 1.0))
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
        layout.addWidget(self._icon_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        self._name_lbl = QLabel(label)
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._name_lbl)
        self.update_theme()

    def update_theme(self):
        icon_col = (
            CURRENT_THEME["c_accent_light"]
            if self._selected
            else (CURRENT_THEME["c_text"] if self._hovered else CURRENT_THEME["c_text_muted"])
        )
        self._icon_lbl.setPixmap(make_svg_icon(self._icon_name, icon_col, 19).pixmap(QSize(19, 19)))
        role = (
            "soundTitleSel"
            if self._selected
            else ("soundTitleHover" if self._hovered else "soundTitle")
        )
        self._name_lbl.setProperty("role", role)
        st = self._name_lbl.style()
        if st:
            st.unpolish(self._name_lbl)
            st.polish(self._name_lbl)
        self.update()

    def setSelected(self, state: bool):
        if self._selected != state:
            self._selected = state
            self.update_theme()

    def enterEvent(self, event):
        self._hovered = True
        self.update_theme()

    def leaveEvent(self, event):
        self._hovered = False
        self.update_theme()

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
            p.fillPath(path, CURRENT_THEME["tile_bg_selected"])
            p.setPen(QPen(CURRENT_THEME["tile_border_selected"], 1.8))
        elif self._hovered:
            p.fillPath(path, CURRENT_THEME["tile_bg_hover"])
            p.setPen(QPen(CURRENT_THEME["tile_border_hover"], 1.0))
        else:
            p.fillPath(path, CURRENT_THEME["tile_bg"])
            p.setPen(QPen(CURRENT_THEME["tile_border"], 1.0))
        p.drawPath(path)
        p.end()


class HotkeyButton(QPushButton):
    """Click-to-record hotkey pill button styled via root stylesheet."""

    hotkeyChanged = pyqtSignal(str)

    def __init__(self, current: str = "", parent=None):
        super().__init__(parent)
        self._current = current
        self._recording = False
        self._update_text()
        self.clicked.connect(self._start_recording)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setProperty("recording", "false")
        self.setFixedHeight(28)
        self.setMinimumWidth(124)

    def _set_recording_state(self, recording: bool):
        self._recording = recording
        self.setProperty("recording", "true" if recording else "false")
        st = self.style()
        if st:
            st.unpolish(self)
            st.polish(self)
        self.update()

    def _update_text(self):
        self.setText(self._current.upper() if self._current else "None")

    def _start_recording(self):
        self._set_recording_state(True)
        self.setText("Press keys...")
        self.grabKeyboard()

    def keyPressEvent(self, event: QKeyEvent):
        if not self._recording:
            return super().keyPressEvent(event)
        if event.key() == Qt.Key.Key_Escape:
            self._set_recording_state(False)
            self._update_text()
            self.releaseKeyboard()
            return
        if event.key() in (
            Qt.Key.Key_Control,
            Qt.Key.Key_Alt,
            Qt.Key.Key_Shift,
            Qt.Key.Key_Meta,
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
        self._set_recording_state(False)
        self._update_text()
        self.releaseKeyboard()
        self.hotkeyChanged.emit(self._current)


# ===========================================================================
# Live Interactive Preview Stage
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

        p.fillRect(self.rect(), CURRENT_THEME["stage_bg"])
        p.setPen(QPen(CURRENT_THEME["stage_dot"], 1.5))
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
        p.setPen(QPen(CURRENT_THEME["stage_border"], 1.0))
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
# Helper Row & Button Builders (Zero Inline Stylesheets)
# ===========================================================================
def _toggle_row(
    label: str,
    sublabel: str = "",
    checked: bool = False,
) -> Tuple[QWidget, CleanToggle]:
    row = _transparent_wrap()
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 4, 0, 4)
    hl.setSpacing(12)

    col = QVBoxLayout()
    col.setSpacing(2)
    col.addWidget(_label(label, 12, "text", bold=True))
    if sublabel:
        sub = _label(sublabel, 11, muted=True)
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
    row = _transparent_wrap()
    vl = QVBoxLayout(row)
    vl.setContentsMargins(0, 2, 0, 2)
    vl.setSpacing(5)

    top = QHBoxLayout()
    top.setContentsMargins(0, 0, 0, 0)
    top.setSpacing(8)
    top.addWidget(_label(label, 12, "text", bold=True))
    if sublabel:
        top.addWidget(_label(sublabel, 11, muted=True))
    top.addStretch()
    val_lbl = _label(str(val), 12, role="textSec", bold=True)
    top.addWidget(val_lbl)
    vl.addLayout(top)

    slider = CleanSlider(lo, hi, val)
    vl.addWidget(slider)
    return row, slider, val_lbl


def _button(text: str, primary: bool = False, danger: bool = False, outline: bool = False) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    if danger:
        btn.setProperty("role", "btnDanger")
    elif primary:
        btn.setProperty("role", "btnPrimary")
    elif outline:
        btn.setProperty("role", "btnOutline")
    else:
        btn.setProperty("role", "btnDefault")
    return btn


# ===========================================================================
# Main Window: SettingsWindow
# ===========================================================================
class SettingsWindow(QWidget):
    """Unified translucent dual-theme Settings Window for TinyHand Windows."""

    WIN_W, WIN_H = 1008, 640
    SIDEBAR_W = 200
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
        self.setObjectName("SettingsRoot")
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
        self._last_update_info: Dict[str, object] = {}
        self._update_worker: Optional[UpdateCheckerThread] = None

        saved_mode = self.config.get("theme_mode", "dark") if self.config else "dark"
        self.theme_mode = "light" if saved_mode == "light" else "dark"
        set_active_theme(self.theme_mode)

        self.setFixedSize(self.WIN_W, self.WIN_H)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._enable_windows_blur()
        self._build_ui()
        self.apply_theme(self.theme_mode, persist=False)
        self._sync_preview_from_state()
        self._center_on_screen()

    def _enable_windows_blur(self):
        """Enable native Windows DWM blur-behind inside the rounded window region."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes

            class DWM_BLURBEHIND(ctypes.Structure):
                _fields_ = [
                    ("dwFlags", wintypes.DWORD),
                    ("fEnable", wintypes.BOOL),
                    ("hRgnBlur", wintypes.HRGN),
                    ("fTransitionOnMaximized", wintypes.BOOL),
                ]

            hrgn = ctypes.windll.gdi32.CreateRoundRectRgn(
                1, 1, self.WIN_W - 1, self.WIN_H - 1, 26, 26
            )
            bb = DWM_BLURBEHIND()
            bb.dwFlags = 0x00000001 | 0x00000002  # DWM_BB_ENABLE | DWM_BB_BLURREGION
            bb.fEnable = True
            bb.hRgnBlur = hrgn
            bb.fTransitionOnMaximized = False
            ctypes.windll.dwmapi.DwmEnableBlurBehindWindow(int(self.winId()), ctypes.byref(bb))
            if hrgn:
                ctypes.windll.gdi32.DeleteObject(hrgn)
        except Exception:
            pass

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        outer = QRectF(0.75, 0.75, self.WIN_W - 1.5, self.WIN_H - 1.5)
        path = QPainterPath()
        path.addRoundedRect(outer, 13.0, 13.0)

        grad = QLinearGradient(0, 0, self.WIN_W, self.WIN_H)
        grad.setColorAt(0.0, CURRENT_THEME["win_grad_start"])
        grad.setColorAt(1.0, CURRENT_THEME["win_grad_end"])
        p.fillPath(path, QBrush(grad))

        p.setPen(QPen(CURRENT_THEME["win_border"], 1.2))
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
    # Centralized Theme Engine
    # ------------------------------------------------------------------
    def _toggle_theme(self):
        next_mode = "light" if self.theme_mode == "dark" else "dark"
        self.apply_theme(next_mode, persist=True)

    def set_theme(self, mode: str):
        """Compatibility wrapper forwarding directly to apply_theme(mode)."""
        self.apply_theme(mode, persist=True)

    def apply_theme(self, mode: str, persist: bool = True):
        """Apply theme from a single root QSS stylesheet and re-polish every widget."""
        mode = "light" if mode == "light" else "dark"
        self.theme_mode = mode
        if persist and self.config:
            self.config.set("theme_mode", mode)
            self.config.save()

        theme = set_active_theme(mode)

        # Single centralized stylesheet on root window
        self.setStyleSheet(build_root_stylesheet(theme))

        # Update top-right theme Sun/Moon icon button
        if hasattr(self, "_btn_theme"):
            icon_name = "sun" if mode == "dark" else "moon"
            tip = "Switch to Light Mode" if mode == "dark" else "Switch to Dark Mode"
            self._btn_theme.setIcon(make_svg_icon(icon_name, theme["c_text_sec"], 15))
            self._btn_theme.setToolTip(tip)

        # Update window control icons
        if hasattr(self, "_btn_min"):
            self._btn_min.setIcon(make_svg_icon("minimize", theme["c_text_muted"], 12))
        if hasattr(self, "_btn_close"):
            self._btn_close.setIcon(make_svg_icon("close", theme["c_text_muted"], 12))

        # Update preview action icons
        self._refresh_preview_icons()

        # Update custom painted tiles & thumbnails
        for thumb in self._pointer_thumbs:
            thumb.update_theme()
        for tile in self._sound_tiles:
            tile.update_theme()

        # Recursively unpolish/polish/update all widgets so zero patches remain stale
        for widget in [self] + self.findChildren(QWidget):
            st = widget.style()
            if st is not None:
                st.unpolish(widget)
                st.polish(widget)
            widget.update()

    # ------------------------------------------------------------------
    # Shell Layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        shell = QVBoxLayout(self)
        shell.setContentsMargins(1, 1, 1, 1)
        shell.setSpacing(0)

        shell.addWidget(self._build_title_bar())

        self._hdiv = QWidget()
        self._hdiv.setFixedHeight(1)
        self._hdiv.setProperty("role", "divider")
        self._hdiv.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        shell.addWidget(self._hdiv)

        body = _transparent_wrap()
        self._body_hl = QHBoxLayout(body)
        self._body_hl.setContentsMargins(0, 0, 0, 0)
        self._body_hl.setSpacing(0)

        self._sidebar = self._build_sidebar()
        self._body_hl.addWidget(self._sidebar)

        self._vdiv1 = QWidget()
        self._vdiv1.setFixedWidth(1)
        self._vdiv1.setProperty("role", "divider")
        self._vdiv1.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._body_hl.addWidget(self._vdiv1)

        self._stack = self._build_pages()
        self._body_hl.addWidget(self._stack, 1)

        self._preview_divider = QWidget()
        self._preview_divider.setFixedWidth(1)
        self._preview_divider.setProperty("role", "divider")
        self._preview_divider.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._body_hl.addWidget(self._preview_divider)

        self._preview_dock = self._build_preview_dock()
        self._body_hl.addWidget(self._preview_dock)

        shell.addWidget(body, 1)

    # ------------------------------------------------------------------
    # Titlebar (Single Sun / Moon Vector Button + Minimize + Close)
    # ------------------------------------------------------------------
    def _build_title_bar(self) -> QWidget:
        self._title_bar = QWidget()
        self._title_bar.setObjectName("TitleBar")
        self._title_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._title_bar.setFixedHeight(44)

        hl = QHBoxLayout(self._title_bar)
        hl.setContentsMargins(16, 0, 12, 0)
        hl.setSpacing(10)

        badge = QLabel()
        badge.setObjectName("TitleBadge")
        badge.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        badge.setFixedSize(24, 24)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setPixmap(make_svg_icon("hand", "#FFFFFF", 13).pixmap(QSize(13, 13)))
        hl.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)

        self._title_lbl = QLabel("TinyHand Windows")
        self._title_lbl.setObjectName("TitleLabel")
        hl.addWidget(self._title_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        hl.addStretch()

        # Single sleek Sun / Moon vector icon button
        self._btn_theme = QPushButton()
        self._btn_theme.setObjectName("ThemeToggleBtn")
        self._btn_theme.setFixedSize(30, 26)
        self._btn_theme.setIconSize(QSize(15, 15))
        self._btn_theme.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_theme.clicked.connect(self._toggle_theme)
        hl.addWidget(self._btn_theme, 0, Qt.AlignmentFlag.AlignVCenter)

        self._btn_min = QPushButton()
        self._btn_min.setObjectName("TitleMinBtn")
        self._btn_min.setFixedSize(30, 26)
        self._btn_min.setIconSize(QSize(12, 12))
        self._btn_min.setToolTip("Minimize")
        self._btn_min.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_min.clicked.connect(self.showMinimized)
        hl.addWidget(self._btn_min, 0, Qt.AlignmentFlag.AlignVCenter)

        self._btn_close = QPushButton()
        self._btn_close.setObjectName("TitleCloseBtn")
        self._btn_close.setFixedSize(30, 26)
        self._btn_close.setIconSize(QSize(12, 12))
        self._btn_close.setToolTip("Close")
        self._btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_close.clicked.connect(self.hide)
        hl.addWidget(self._btn_close, 0, Qt.AlignmentFlag.AlignVCenter)

        return self._title_bar

    # ------------------------------------------------------------------
    # Left Navigation Rail (6 Colorful 24x24 Rounded-Square Badges)
    # ------------------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        sb = QWidget()
        sb.setObjectName("Sidebar")
        sb.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sb.setFixedWidth(self.SIDEBAR_W)

        vl = QVBoxLayout(sb)
        vl.setContentsMargins(0, 14, 0, 14)
        vl.setSpacing(4)

        nav_defs = [
            ("settings", "General", "#787C85"),
            ("hand", "Pointers", "#7C5DFA"),
            ("sparkles", "Style & FX", "#EC608A"),
            ("pen", "Ink & Draw", "#F59E0B"),
            ("sound_on", "Sound", "#3B82F6"),
            ("info_i", "About", "#6B7280"),
        ]
        for idx, (icon_key, title, badge_col) in enumerate(nav_defs):
            item = NavRailButton(icon_key, title, badge_col)
            item.setChecked(idx == 0)
            item.clicked.connect(lambda i=idx: self._switch_page(i))
            self._nav_items.append(item)
            vl.addWidget(item)

        vl.addStretch()

        ver_wrap = QHBoxLayout()
        ver_wrap.setContentsMargins(20, 0, 16, 0)
        ver_wrap.addWidget(_label(f"Version {APP_VERSION}", 11, muted=True))
        vl.addLayout(ver_wrap)

        return sb

    # ------------------------------------------------------------------
    # Right Dock: Live Preview
    # ------------------------------------------------------------------
    def _build_preview_dock(self) -> QWidget:
        dock = QWidget()
        dock.setObjectName("PreviewDock")
        dock.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        dock.setFixedWidth(self.PREVIEW_DOCK_W)

        vl = QVBoxLayout(dock)
        vl.setContentsMargins(14, 18, 14, 16)
        vl.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(2, 0, 2, 0)
        hdr.addWidget(_label("Preview", 12, "textSec", bold=True))
        hdr.addStretch()
        hdr.addWidget(_label("Click or drag", 11, muted=True))
        vl.addLayout(hdr)

        self._preview = LivePreviewStage(self.assets_dir, self.overlay.hand_assets)
        vl.addWidget(self._preview, 0, Qt.AlignmentFlag.AlignHCenter)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(6)

        self._pg_btn_draw = self._mini_ctrl_btn("Draw", "pen", checkable=True, checked=True)
        self._pg_btn_draw.toggled.connect(self._on_preview_draw_toggled)
        ctrl_row.addWidget(self._pg_btn_draw)

        self._pg_btn_spot = self._mini_ctrl_btn("Spot", "spotlight", checkable=True, checked=False)
        self._pg_btn_spot.toggled.connect(self._on_preview_spot_toggled)
        ctrl_row.addWidget(self._pg_btn_spot)

        self._btn_tap = self._mini_ctrl_btn("Tap", "pops", checkable=False)
        self._btn_tap.clicked.connect(lambda: self._preview.trigger_tap())
        ctrl_row.addWidget(self._btn_tap)

        self._btn_clr = self._mini_ctrl_btn("Clear", "clear", checkable=False)
        self._btn_clr.clicked.connect(self._preview.clear_ink)
        ctrl_row.addWidget(self._btn_clr)

        vl.addLayout(ctrl_row)

        self._preview_summary_wrap = QWidget()
        self._preview_summary_wrap.setObjectName("PreviewSummaryPill")
        self._preview_summary_wrap.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sum_vl = QVBoxLayout(self._preview_summary_wrap)
        sum_vl.setContentsMargins(12, 9, 12, 9)
        sum_vl.setSpacing(3)
        self._spec_pointer_lbl = _label("Coral Vinyl  ·  Size M", 12, "text", bold=True)
        self._spec_meta_lbl = _label("Match ink  ·  Shadow on", 11, muted=True)
        sum_vl.addWidget(self._spec_pointer_lbl)
        sum_vl.addWidget(self._spec_meta_lbl)
        vl.addWidget(self._preview_summary_wrap)

        vl.addStretch()
        return dock

    def _on_preview_draw_toggled(self, on: bool):
        if self._preview:
            self._preview.draw_enabled = on
        self._refresh_preview_icons()

    def _on_preview_spot_toggled(self, on: bool):
        if self._preview:
            self._preview.spotlight_preview = on
        self._refresh_preview_icons()

    def _refresh_preview_icons(self):
        if not hasattr(self, "_pg_btn_draw"):
            return
        for btn in (self._pg_btn_draw, self._pg_btn_spot, self._btn_tap, self._btn_clr):
            icon_name = getattr(btn, "_icon_name", None)
            if not icon_name:
                continue
            if btn.isCheckable() and btn.isChecked():
                col = CURRENT_THEME["c_checked_fg"]
            else:
                col = CURRENT_THEME["c_text_muted"]
            btn.setIcon(make_svg_icon(icon_name, col, 12))

    @staticmethod
    def _mini_ctrl_btn(
        text: str,
        icon_name: str,
        checkable: bool = False,
        checked: bool = False,
    ) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("role", "previewCtrl")
        btn.setCheckable(checkable)
        if checkable:
            btn.setChecked(checked)
        btn._icon_name = icon_name
        btn.setIconSize(QSize(12, 12))
        btn.setFixedHeight(29)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        return btn

    # ------------------------------------------------------------------
    # Pages Stack
    # ------------------------------------------------------------------
    def _build_pages(self) -> QStackedWidget:
        self._pointer_thumbs.clear()
        self._sound_tiles.clear()
        self._swatch_btns.clear()
        stack = QStackedWidget()
        stack.setObjectName("PagesStack")
        stack.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        stack.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
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
        vbox.addWidget(_label("General", 18, "pageTitle", bold=True))

        vbox.addWidget(_section_label("Shortcuts"))
        hk_body = QVBoxLayout()
        hk_body.setSpacing(6)
        for i, (cfg_key, lbl_txt) in enumerate(HOTKEY_ROWS):
            hk_row = QHBoxLayout()
            hk_row.setContentsMargins(0, 3, 0, 3)
            hk_row.addWidget(_label(lbl_txt, 12, "text"))
            hk_row.addStretch()
            hk_btn = HotkeyButton(self.config.get(cfg_key, ""))
            hk_btn.hotkeyChanged.connect(lambda v, k=cfg_key: self._on_hotkey_changed(k, v))
            hk_row.addWidget(hk_btn)
            hk_body.addLayout(hk_row)
            if i < len(HOTKEY_ROWS) - 1:
                _add_hsep(hk_body)
        vbox.addWidget(SettingsGroup(hk_body))

        vbox.addWidget(_section_label("Quick Draw"))
        draw_body = QVBoxLayout()
        draw_body.setSpacing(6)

        hd_hl = QHBoxLayout()
        hd_hl.setContentsMargins(0, 2, 0, 2)
        hd_col = QVBoxLayout()
        hd_col.setSpacing(2)
        hd_col.addWidget(_label("Hold-to-Draw Key", 12, "text", bold=True))
        hd_sub = _label("Hold while dragging to draw without Draw mode", 11, muted=True)
        hd_sub.setWordWrap(True)
        hd_col.addWidget(hd_sub)
        hd_hl.addLayout(hd_col, 1)

        hd_combo = QComboBox()
        hd_combo.setFixedWidth(124)
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

        vbox.addWidget(_section_label("Startup"))
        st_body = QVBoxLayout()
        st_body.setSpacing(6)
        startup_on = (
            self.config.get_launch_at_startup_state()
            if hasattr(self.config, "get_launch_at_startup_state")
            else False
        )
        st_row, st_toggle = _toggle_row(
            "Open TinyHand Windows when you sign in",
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

        vbox.addWidget(_label("Pointers", 18, "pageTitle", bold=True))

        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search pointers...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setFixedHeight(32)
        self._search_input.textChanged.connect(self._on_search_changed)
        filter_bar.addWidget(self._search_input, 1)

        cat_seg = SegmentedControl(
            [("All", "all"), ("Hands", "hands"), ("Special", "funny"), ("Custom", "custom")],
            current_val="all",
        )
        cat_seg.changed.connect(self._on_category_changed)
        filter_bar.addWidget(cat_seg)
        vbox.addLayout(filter_bar)

        grid_container = _transparent_wrap()
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
        vbox.addWidget(_label("Style & FX", 18, "pageTitle", bold=True))

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
            "Drop Shadow",
            "Render a soft silhouette shadow beneath the pointer",
            bool(self.config.get("show_shadow", True)),
        )
        self._shadow_toggle.toggled.connect(self._on_shadow_toggled)
        ptr_body.addWidget(sh_row)
        _add_hsep(ptr_body)

        rip_row, self._ripple_toggle = _toggle_row(
            "Click Ripple Ring",
            "Show an expanding pulse ring when clicking",
            bool(self.config.get("click_ripple", True)),
        )
        self._ripple_toggle.toggled.connect(self._on_ripple_toggled)
        ptr_body.addWidget(rip_row)
        vbox.addWidget(SettingsGroup(ptr_body))

        vbox.addWidget(_section_label("Tap Bubbles"))
        bub_body = QVBoxLayout()
        bub_body.setSpacing(6)
        bub_row, self._bubble_toggle = _toggle_row(
            "Comic Tap Bubbles",
            "Display short callout words above clicks",
            bool(self.config.get("show_comic_bubbles", True)),
        )
        self._bubble_toggle.toggled.connect(self._on_bubbles_toggled)
        bub_body.addWidget(bub_row)
        _add_hsep(bub_body)

        pack_row = QHBoxLayout()
        pack_row.setContentsMargins(0, 4, 0, 2)
        pack_row.addWidget(_label("Word Style", 12, "text", bold=True))
        pack_row.addStretch()
        pack_seg = SegmentedControl(
            [("Playful", "funny"), ("Minimal", "clean")],
            current_val=self.config.get("comic_word_pack", "funny"),
        )
        pack_seg.changed.connect(self._on_word_pack_changed)
        pack_row.addWidget(pack_seg)
        bub_body.addLayout(pack_row)
        vbox.addWidget(SettingsGroup(bub_body))

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
        vbox.addWidget(_label("Ink & Draw", 18, "pageTitle", bold=True))

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
            "Rainbow Ink",
            "Cycle colors smoothly while drawing strokes",
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
            "Smooth Lines",
            "Stabilize mouse shake for cleaner curves",
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
        fade_hl.addWidget(_label("Fade Out After", 12, "text", bold=True))
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
    # Page 4: Sound
    # ==================================================================
    def _page_sound(self) -> QScrollArea:
        scroll, _inner, vbox = _page_scroll()
        vbox.addWidget(_label("Sound", 18, "pageTitle", bold=True))

        vbox.addWidget(_section_label("Tap Sound"))
        tile_body = QVBoxLayout()
        tile_body.setSpacing(10)

        grid_w = _transparent_wrap()
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
            "Sound in Laser Mode",
            "Play tap audio when using the laser dot",
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
    # Page 5: About & Maintenance (Updates, Diagnostics & Bug Solvers)
    # ==================================================================
    def _page_about(self) -> QScrollArea:
        scroll, _inner, vbox = _page_scroll()

        vbox.addWidget(_label("About & Maintenance", 18, "pageTitle", bold=True))

        hero_body = QVBoxLayout()
        hero_body.setSpacing(6)

        icon_badge = QLabel()
        icon_badge.setObjectName("AboutHeroBadge")
        icon_badge.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        icon_badge.setFixedSize(60, 60)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setPixmap(make_svg_icon("hand", "#FFFFFF", 32).pixmap(QSize(32, 32)))
        hero_body.addWidget(icon_badge, 0, Qt.AlignmentFlag.AlignHCenter)

        title = _label("TinyHand Windows", 20, "pageTitle", bold=True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_body.addWidget(title)

        ver = _label(f"Version {APP_VERSION} · Windows 64-bit Native", 12, "textSec")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_body.addWidget(ver)

        tag = _label("Hardware-accelerated presentation pointer, vector ink & cinema spotlight.", 11, muted=True)
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_body.addWidget(tag)
        vbox.addWidget(SettingsGroup(hero_body))

        vbox.addWidget(_section_label("Software Updates"))
        update_body = QVBoxLayout()
        update_body.setSpacing(10)

        up_top_row = QHBoxLayout()
        up_top_row.setContentsMargins(0, 2, 0, 2)
        up_info_col = QVBoxLayout()
        up_info_col.setSpacing(2)

        self._update_status_lbl = _label(f"Installed Version: v{APP_VERSION}", 12, "text", bold=True)
        self._update_sub_lbl = _label("Check GitHub Releases for latest features and bug fixes.", 11, muted=True)
        self._update_sub_lbl.setWordWrap(True)
        up_info_col.addWidget(self._update_status_lbl)
        up_info_col.addWidget(self._update_sub_lbl)
        up_top_row.addLayout(up_info_col, 1)

        self._btn_check_update = _button("Check for Updates", primary=True)
        self._btn_check_update.clicked.connect(self._check_for_updates)
        up_top_row.addWidget(self._btn_check_update, 0, Qt.AlignmentFlag.AlignVCenter)
        update_body.addLayout(up_top_row)

        self._update_result_frame = QFrame()
        self._update_result_frame.setObjectName("UpdateResultFrame")
        self._update_result_frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._update_result_frame.setVisible(False)
        up_res_vl = QVBoxLayout(self._update_result_frame)
        up_res_vl.setContentsMargins(12, 10, 12, 10)
        up_res_vl.setSpacing(6)

        self._update_msg_lbl = _label("", 12, "text", bold=True)
        self._update_notes_lbl = _label("", 11, muted=True)
        self._update_notes_lbl.setWordWrap(True)
        up_res_vl.addWidget(self._update_msg_lbl)
        up_res_vl.addWidget(self._update_notes_lbl)

        self._update_actions_row = QHBoxLayout()
        self._update_actions_row.setSpacing(8)
        self._btn_download_update = _button("Download Update (.exe)", primary=True)
        self._btn_download_update.clicked.connect(self._on_download_update_clicked)
        self._btn_view_release = _button("View on GitHub", outline=True)
        self._btn_view_release.clicked.connect(self._on_view_release_clicked)
        self._update_actions_row.addWidget(self._btn_download_update)
        self._update_actions_row.addWidget(self._btn_view_release)
        self._update_actions_row.addStretch()
        up_res_vl.addLayout(self._update_actions_row)

        update_body.addWidget(self._update_result_frame)
        vbox.addWidget(SettingsGroup(update_body))

        vbox.addWidget(_section_label("Diagnostics & Bug Troubleshooting"))
        diag_body = QVBoxLayout()
        diag_body.setSpacing(8)

        diag_body.addWidget(
            _label("Encountering an issue or click behavior glitch? Use these tools to repair or report.", 11, muted=True)
        )

        diag_btns_row = QHBoxLayout()
        diag_btns_row.setSpacing(8)

        self._btn_copy_diag = _button("Copy System Diagnostics")
        self._btn_copy_diag.setProperty("copied", "false")
        self._btn_copy_diag.setToolTip("Copies OS, Python, DPI, and pointer config to clipboard for bug reports.")
        self._btn_copy_diag.clicked.connect(self._copy_diagnostic_info)
        diag_btns_row.addWidget(self._btn_copy_diag)

        self._btn_repair_cfg = _button("Verify && Repair Config")
        self._btn_repair_cfg.setToolTip("Validates and repairs missing config keys without losing custom uploads.")
        self._btn_repair_cfg.clicked.connect(self._repair_config)
        diag_btns_row.addWidget(self._btn_repair_cfg)

        self._btn_open_appdata = _button("Open AppData Folder")
        self._btn_open_appdata.setToolTip("Opens %LOCALAPPDATA%\\TinyHandWindows\\ where config and custom assets are stored.")
        self._btn_open_appdata.clicked.connect(self._open_appdata_folder)
        diag_btns_row.addWidget(self._btn_open_appdata)

        diag_btns_row.addStretch()
        diag_body.addLayout(diag_btns_row)

        _add_hsep(diag_body)

        report_row = QHBoxLayout()
        report_row.setContentsMargins(0, 2, 0, 2)
        report_row.addWidget(_label("Found a bug or have a suggestion?", 12, "text"))
        report_row.addStretch()
        btn_report = _button("Report Bug on GitHub", outline=True)
        btn_report.clicked.connect(self._report_bug)
        report_row.addWidget(btn_report)
        diag_body.addLayout(report_row)

        vbox.addWidget(SettingsGroup(diag_body))

        vbox.addWidget(_section_label("Specifications & Credits"))
        info_body = QVBoxLayout()
        info_body.setSpacing(6)
        for k, v in [
            ("Platform", "Windows 10 & 11 (64-bit Desktop)"),
            ("Rendering Engine", "PyQt6 Layered Transparent Overlay (Win32)"),
            ("Pointers Included", "36 3D Hands + 4 Vector FX + Custom PNGs"),
            ("Repository", "github.com/wajahat-alip/tinyhand-windows"),
            ("License", "100% Free & Open Source (MIT)"),
        ]:
            r = QHBoxLayout()
            r.addWidget(_label(k, 12, "textSec"))
            r.addStretch()
            r.addWidget(_label(v, 12, "text", bold=True))
            info_body.addLayout(r)
            if k != "License":
                _add_hsep(info_body)
        vbox.addWidget(SettingsGroup(info_body))

        credit = _label("Inspired by nilbuild/tinyhand (macOS) by Kamran Ahmed.", 11, muted=True)
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(credit)

        reset_btn = _button("Reset All Settings to Defaults", danger=True)
        reset_btn.setFixedWidth(220)
        reset_btn.clicked.connect(self._reset_all_settings)
        vbox.addWidget(reset_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        vbox.addSpacing(16)
        return scroll

    # -------------------------------------------------------------
    # Update & Diagnostics Action Handlers
    # -------------------------------------------------------------
    @staticmethod
    def _set_label_role(lbl: QLabel, role: str):
        lbl.setProperty("role", role)
        st = lbl.style()
        if st:
            st.unpolish(lbl)
            st.polish(lbl)
        lbl.update()

    def _check_for_updates(self):
        self._btn_check_update.setEnabled(False)
        self._btn_check_update.setText("Checking...")
        self._update_status_lbl.setText("Checking GitHub for releases...")
        self._update_sub_lbl.setText(
            "Querying https://api.github.com/repos/wajahat-alip/tinyhand-windows/releases/latest..."
        )

        self._update_worker = UpdateCheckerThread(APP_VERSION, "wajahat-alip/tinyhand-windows", self)
        self._update_worker.check_finished.connect(self._on_update_check_finished)
        self._update_worker.start()

    def _on_update_check_finished(self, res: dict):
        self._btn_check_update.setEnabled(True)
        self._btn_check_update.setText("Check for Updates")
        self._last_update_info = res

        if not res.get("success"):
            self._update_status_lbl.setText("Check Failed (Network Error)")
            self._set_label_role(self._update_status_lbl, "statusDanger")
            self._update_sub_lbl.setText(
                f"Could not reach GitHub ({res.get('error', 'Unknown')}). You can visit releases manually."
            )
            self._update_result_frame.setVisible(True)
            self._update_msg_lbl.setText("Unable to verify latest release automatically")
            self._set_label_role(self._update_msg_lbl, "statusDanger")
            self._update_notes_lbl.setText("Please check your internet connection or browse releases on GitHub.")
            self._btn_download_update.setVisible(False)
            self._btn_view_release.setVisible(True)
            self._btn_view_release.setText("Open GitHub Releases")
            return

        is_new = res.get("is_new", False)
        latest_ver = res.get("latest_version", APP_VERSION)
        notes = res.get("notes", "")

        self._update_result_frame.setVisible(True)
        if is_new:
            self._update_status_lbl.setText(f"Update Available: v{latest_ver}!")
            self._set_label_role(self._update_status_lbl, "statusAccent")
            self._update_sub_lbl.setText(f"A newer version (v{latest_ver}) is available for download.")
            self._update_msg_lbl.setText(f"New Version v{latest_ver} Available!")
            self._set_label_role(self._update_msg_lbl, "statusSuccess")
            self._update_notes_lbl.setText(notes if notes else "Performance improvements, bug fixes and enhancements.")
            self._btn_download_update.setVisible(True)
            self._btn_view_release.setVisible(True)
            self._btn_view_release.setText("View Release Notes")
        else:
            self._update_status_lbl.setText(f"You're Up to Date (v{APP_VERSION})")
            self._set_label_role(self._update_status_lbl, "statusSuccess")
            self._update_sub_lbl.setText("You are currently running the latest official version of TinyHand Windows.")
            self._update_msg_lbl.setText(f"TinyHand Windows v{APP_VERSION} is the latest version.")
            self._set_label_role(self._update_msg_lbl, "statusSuccess")
            self._update_notes_lbl.setText("No new updates are pending. All features are up to date.")
            self._btn_download_update.setVisible(False)
            self._btn_view_release.setVisible(True)
            self._btn_view_release.setText("Visit GitHub Releases")

    def _on_download_update_clicked(self):
        url = str(self._last_update_info.get("download_url") or "https://github.com/wajahat-alip/tinyhand-windows/releases/latest")
        QDesktopServices.openUrl(QUrl(url))

    def _on_view_release_clicked(self):
        url = str(self._last_update_info.get("release_url") or "https://github.com/wajahat-alip/tinyhand-windows/releases")
        QDesktopServices.openUrl(QUrl(url))

    def _gather_diagnostic_info(self) -> str:
        import platform

        screen = QGuiApplication.primaryScreen()
        scr_geom = screen.geometry() if screen else None
        dpr = screen.devicePixelRatio() if screen else 1.0

        info = [
            "### TinyHand Windows — Diagnostic Report",
            f"- **App Version**: {APP_VERSION}",
            f"- **OS**: Windows {platform.platform()} ({platform.architecture()[0]})",
            f"- **Python**: {platform.python_version()}",
            f"- **Screen Resolution**: {scr_geom.width()}x{scr_geom.height()} @ {dpr:.1f}x DPI" if scr_geom else "- **Screen**: Unknown",
            f"- **Active Pointer**: {self.config.get('pointer_style', 'coral')} (Scale: {self.config.get('pointer_scale', 2)})",
            f"- **Drawing Mode**: Smooth={self.config.get('smooth_lines', False)} (Strength={self.config.get('smooth_strength', 5)})",
            f"- **Config Path**: {os.path.join(self.app_dir, 'config.json')}",
            f"- **Custom Hands Loaded**: {len(self.config.get('custom_hands', []))}",
            f"- **Custom Sounds Loaded**: {len(self.config.get('custom_sounds', []))}",
        ]
        return "\n".join(info)

    def _copy_diagnostic_info(self):
        info = self._gather_diagnostic_info()
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(info)
            old_txt = self._btn_copy_diag.text()
            self._btn_copy_diag.setText("Copied to Clipboard!")
            self._btn_copy_diag.setProperty("copied", "true")
            st = self._btn_copy_diag.style()
            if st:
                st.unpolish(self._btn_copy_diag)
                st.polish(self._btn_copy_diag)
            QTimer.singleShot(2500, lambda: self._restore_copy_diag_btn(old_txt))

    def _restore_copy_diag_btn(self, old_txt: str):
        self._btn_copy_diag.setText(old_txt)
        self._btn_copy_diag.setProperty("copied", "false")
        st = self._btn_copy_diag.style()
        if st:
            st.unpolish(self._btn_copy_diag)
            st.polish(self._btn_copy_diag)

    def _repair_config(self):
        try:
            self.config.load()
            from config import DEFAULTS

            repaired = 0
            for k, v in DEFAULTS.items():
                if k not in self.config._data:
                    self.config._data[k] = v
                    repaired += 1
            self.config.save()
            QMessageBox.information(
                self,
                "Config Verification",
                f"Configuration is healthy and verified!\n{repaired} missing keys restored with defaults.\nCustom hands and sounds are preserved.",
            )
        except Exception as e:
            QMessageBox.warning(self, "Repair Warning", f"Could not verify config: {e}")

    def _open_appdata_folder(self):
        if os.path.exists(self.app_dir):
            os.startfile(self.app_dir)
        else:
            QMessageBox.information(self, "AppData Folder", f"Data path:\n{self.app_dir}")

    def _report_bug(self):
        QDesktopServices.openUrl(QUrl("https://github.com/wajahat-alip/tinyhand-windows/issues/new"))

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
                col = asset.default_ink if asset else QColor(CURRENT_THEME["c_accent"])
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
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hl = QHBoxLayout(row)
        hl.setContentsMargins(10, 6, 8, 6)
        hl.setSpacing(8)
        hl.addWidget(_label(name, 12, "text", bold=True))
        hl.addStretch()

        use_btn = QPushButton("Use")
        use_btn.setProperty("role", "btnUse")
        use_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        use_btn.clicked.connect(on_use)
        hl.addWidget(use_btn)

        rm_btn = QPushButton("Remove")
        rm_btn.setProperty("role", "btnRemove")
        rm_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
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
            self.apply_theme(self.config.get("theme_mode", "dark"), persist=True)

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
