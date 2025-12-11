"""
Professional Theme System for Scraper Platform Desktop Application.

Provides a comprehensive design system with:
- Consistent color palette with semantic naming
- Professional typography hierarchy
- Standardized spacing and sizing
- Dark and Light theme variants
- Component-specific styling with proper states
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QApplication, QWidget


class DesignTokens:
    """Design tokens for consistent styling across the application."""

    # Spacing scale (4px increments)
    SPACE_XS = "4px"
    SPACE_SM = "8px"
    SPACE_MD = "12px"
    SPACE_LG = "16px"
    SPACE_XL = "20px"
    SPACE_2XL = "24px"

    # Border radius
    RADIUS_SM = "4px"
    RADIUS_MD = "6px"
    RADIUS_LG = "8px"
    RADIUS_XL = "12px"

    # Typography
    FONT_FAMILY = "'Inter', 'Segoe UI', 'SF Pro Display', 'Roboto', -apple-system, sans-serif"
    FONT_MONO = "'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace"

    # Font sizes
    FONT_XS = "11px"
    FONT_SM = "12px"
    FONT_MD = "13px"
    FONT_LG = "14px"
    FONT_XL = "16px"
    FONT_2XL = "18px"
    FONT_3XL = "22px"
    FONT_4XL = "28px"

    # Font weights
    WEIGHT_NORMAL = "400"
    WEIGHT_MEDIUM = "500"
    WEIGHT_SEMIBOLD = "600"
    WEIGHT_BOLD = "700"

    # Transitions
    TRANSITION_FAST = "150ms ease"
    TRANSITION_NORMAL = "250ms ease"
    TRANSITION_SLOW = "350ms ease"


class ThemeManager:
    """Manages application themes with professional, clean aesthetics."""

    # ========================================
    # DARK THEME - "Obsidian"
    # Modern, professional dark theme with excellent contrast
    # ========================================

    DARK_THEME = """
        /* ========================================
           GLOBAL STYLES
           ======================================== */

        QMainWindow {
            background-color: #0a0e17;
            color: #e2e8f0;
        }

        QWidget {
            background-color: #0a0e17;
            color: #e2e8f0;
            font-family: 'Inter', 'Segoe UI', 'SF Pro Display', 'Roboto', sans-serif;
            font-size: 13px;
            font-weight: 400;
        }

        /* ========================================
           PANELS & CONTAINERS
           ======================================== */

        QFrame, QGroupBox {
            background-color: #111827;
            border: 1px solid #1f2937;
            border-radius: 8px;
            padding: 12px;
        }

        QGroupBox {
            margin-top: 20px;
            padding-top: 12px;
            font-weight: 600;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            color: #cbd5e1;
            font-weight: 600;
            font-size: 13px;
            letter-spacing: 0.3px;
        }

        /* ========================================
           BUTTONS
           ======================================== */

        QPushButton {
            background-color: #1e293b;
            color: #e2e8f0;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: 500;
            font-size: 13px;
            min-height: 20px;
        }

        QPushButton:hover {
            background-color: #334155;
            border-color: #475569;
            color: #ffffff;
        }

        QPushButton:pressed {
            background-color: #0f172a;
            border-color: #1e293b;
        }

        QPushButton:disabled {
            background-color: #1e293b;
            color: #475569;
            border-color: #1e293b;
        }

        /* Primary Button Style */
        QPushButton[class="primary"] {
            background-color: #3b82f6;
            color: #ffffff;
            border: 1px solid #3b82f6;
            font-weight: 600;
        }

        QPushButton[class="primary"]:hover {
            background-color: #2563eb;
            border-color: #2563eb;
        }

        QPushButton[class="primary"]:pressed {
            background-color: #1d4ed8;
        }

        /* Success Button Style */
        QPushButton[class="success"] {
            background-color: #10b981;
            color: #ffffff;
            border: 1px solid #10b981;
            font-weight: 600;
        }

        QPushButton[class="success"]:hover {
            background-color: #059669;
            border-color: #059669;
        }

        QPushButton[class="success"]:pressed {
            background-color: #047857;
        }

        /* Danger Button Style */
        QPushButton[class="danger"] {
            background-color: #ef4444;
            color: #ffffff;
            border: 1px solid #ef4444;
            font-weight: 600;
        }

        QPushButton[class="danger"]:hover {
            background-color: #dc2626;
            border-color: #dc2626;
        }

        QPushButton[class="danger"]:pressed {
            background-color: #b91c1c;
        }

        /* Warning Button Style */
        QPushButton[class="warning"] {
            background-color: #f59e0b;
            color: #ffffff;
            border: 1px solid #f59e0b;
            font-weight: 600;
        }

        QPushButton[class="warning"]:hover {
            background-color: #d97706;
            border-color: #d97706;
        }

        /* ========================================
           INPUTS
           ======================================== */

        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {
            background-color: #0f172a;
            color: #e2e8f0;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 13px;
            selection-background-color: #3b82f6;
        }

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {
            border: 2px solid #3b82f6;
            background-color: #0a0e17;
            padding: 7px 11px;
        }

        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {
            background-color: #1e293b;
            color: #64748b;
            border-color: #1e293b;
        }

        /* ========================================
           COMBOBOX
           ======================================== */

        QComboBox {
            background-color: #0f172a;
            color: #e2e8f0;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 13px;
            min-width: 100px;
        }

        QComboBox:hover {
            border-color: #3b82f6;
        }

        QComboBox:focus {
            border: 2px solid #3b82f6;
            padding: 7px 11px;
        }

        QComboBox::drop-down {
            border: none;
            width: 24px;
            padding-right: 4px;
        }

        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #94a3b8;
            margin-right: 8px;
        }

        QComboBox QAbstractItemView {
            background-color: #1e293b;
            color: #e2e8f0;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 4px;
            selection-background-color: #3b82f6;
            selection-color: #ffffff;
            outline: none;
        }

        QComboBox QAbstractItemView::item {
            padding: 8px 12px;
            border-radius: 4px;
            min-height: 20px;
        }

        QComboBox QAbstractItemView::item:hover {
            background-color: #334155;
        }

        /* ========================================
           CHECKBOXES & RADIO BUTTONS
           ======================================== */

        QCheckBox, QRadioButton {
            color: #e2e8f0;
            spacing: 8px;
            font-size: 13px;
        }

        QCheckBox::indicator, QRadioButton::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #334155;
            border-radius: 4px;
            background-color: #0f172a;
        }

        QRadioButton::indicator {
            border-radius: 9px;
        }

        QCheckBox::indicator:hover, QRadioButton::indicator:hover {
            border-color: #3b82f6;
        }

        QCheckBox::indicator:checked, QRadioButton::indicator:checked {
            background-color: #3b82f6;
            border-color: #3b82f6;
        }

        /* ========================================
           TABS
           ======================================== */

        QTabWidget::pane {
            border: 1px solid #1f2937;
            background-color: #111827;
            border-radius: 8px;
            padding: 16px;
        }

        QTabWidget::tab-bar {
            left: 8px;
        }

        QTabBar::tab {
            background-color: transparent;
            color: #94a3b8;
            padding: 10px 20px;
            margin-right: 4px;
            border-bottom: 3px solid transparent;
            font-weight: 500;
            font-size: 13px;
            min-width: 80px;
        }

        QTabBar::tab:hover {
            color: #e2e8f0;
            background-color: #1e293b;
            border-radius: 6px 6px 0 0;
        }

        QTabBar::tab:selected {
            color: #3b82f6;
            border-bottom: 3px solid #3b82f6;
            font-weight: 600;
        }

        /* ========================================
           TABLES
           ======================================== */

        QTableWidget, QTableView, QTreeWidget, QTreeView {
            background-color: #111827;
            alternate-background-color: #0f172a;
            color: #e2e8f0;
            gridline-color: #1f2937;
            border: 1px solid #1f2937;
            border-radius: 8px;
            padding: 4px;
            selection-background-color: #1e40af;
            font-size: 13px;
        }

        QHeaderView::section {
            background-color: #1e293b;
            color: #cbd5e1;
            padding: 12px 16px;
            border: none;
            border-right: 1px solid #334155;
            border-bottom: 2px solid #334155;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }

        QHeaderView::section:hover {
            background-color: #334155;
        }

        QTableWidget::item, QTableView::item, QTreeWidget::item, QTreeView::item {
            padding: 8px;
            border: none;
        }

        QTableWidget::item:selected, QTableView::item:selected,
        QTreeWidget::item:selected, QTreeView::item:selected {
            background-color: #1e40af;
            color: #ffffff;
        }

        QTableWidget::item:hover, QTableView::item:hover {
            background-color: #1e293b;
        }

        /* ========================================
           LIST WIDGETS
           ======================================== */

        QListWidget {
            background-color: #111827;
            color: #e2e8f0;
            border: 1px solid #1f2937;
            border-radius: 8px;
            padding: 4px;
            font-size: 13px;
        }

        QListWidget::item {
            padding: 10px 12px;
            border-radius: 6px;
            margin: 2px;
        }

        QListWidget::item:hover {
            background-color: #1e293b;
        }

        QListWidget::item:selected {
            background-color: #1e40af;
            color: #ffffff;
        }

        /* ========================================
           SCROLLBARS
           ======================================== */

        QScrollBar:vertical {
            background: #0a0e17;
            width: 12px;
            margin: 0;
            border-radius: 6px;
        }

        QScrollBar::handle:vertical {
            background: #334155;
            min-height: 30px;
            border-radius: 6px;
            margin: 2px;
        }

        QScrollBar::handle:vertical:hover {
            background: #475569;
        }

        QScrollBar::handle:vertical:pressed {
            background: #3b82f6;
        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }

        QScrollBar:horizontal {
            background: #0a0e17;
            height: 12px;
            margin: 0;
            border-radius: 6px;
        }

        QScrollBar::handle:horizontal {
            background: #334155;
            min-width: 30px;
            border-radius: 6px;
            margin: 2px;
        }

        QScrollBar::handle:horizontal:hover {
            background: #475569;
        }

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }

        /* ========================================
           SPLITTERS
           ======================================== */

        QSplitter::handle {
            background-color: #1f2937;
            width: 2px;
            height: 2px;
        }

        QSplitter::handle:hover {
            background-color: #3b82f6;
        }

        /* ========================================
           STATUS BAR
           ======================================== */

        QStatusBar {
            background-color: #0a0e17;
            color: #64748b;
            border-top: 1px solid #1f2937;
            padding: 4px 8px;
            font-size: 12px;
        }

        QStatusBar::item {
            border: none;
        }

        /* ========================================
           MENU BAR & MENUS
           ======================================== */

        QMenuBar {
            background-color: #0a0e17;
            border-bottom: 1px solid #1f2937;
            padding: 4px;
        }

        QMenuBar::item {
            spacing: 4px;
            padding: 6px 12px;
            background: transparent;
            border-radius: 6px;
            color: #e2e8f0;
        }

        QMenuBar::item:selected {
            background-color: #1e293b;
        }

        QMenuBar::item:pressed {
            background-color: #334155;
        }

        QMenu {
            background-color: #1e293b;
            color: #e2e8f0;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 4px;
        }

        QMenu::item {
            padding: 8px 24px 8px 12px;
            border-radius: 4px;
            margin: 2px;
        }

        QMenu::item:selected {
            background-color: #3b82f6;
            color: #ffffff;
        }

        QMenu::separator {
            height: 1px;
            background-color: #334155;
            margin: 4px 8px;
        }

        /* ========================================
           TOOLBAR
           ======================================== */

        QToolBar {
            background-color: #0a0e17;
            border-bottom: 1px solid #1f2937;
            spacing: 8px;
            padding: 8px;
        }

        QToolBar::separator {
            background-color: #334155;
            width: 1px;
            margin: 4px 8px;
        }

        /* ========================================
           PROGRESS BARS
           ======================================== */

        QProgressBar {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 6px;
            text-align: center;
            color: #e2e8f0;
            font-weight: 600;
            font-size: 12px;
            min-height: 20px;
        }

        QProgressBar::chunk {
            background-color: #3b82f6;
            border-radius: 5px;
        }

        /* ========================================
           LABELS
           ======================================== */

        QLabel {
            color: #e2e8f0;
            font-size: 13px;
        }

        QLabel[class="heading"] {
            font-size: 18px;
            font-weight: 600;
            color: #f1f5f9;
        }

        QLabel[class="subheading"] {
            font-size: 14px;
            font-weight: 500;
            color: #cbd5e1;
        }

        QLabel[class="caption"] {
            font-size: 11px;
            color: #94a3b8;
        }

        QLabel[class="muted"] {
            color: #64748b;
        }

        /* ========================================
           TEXT BROWSER
           ======================================== */

        QTextBrowser {
            background-color: #0f172a;
            color: #e2e8f0;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px;
            font-size: 13px;
            selection-background-color: #3b82f6;
        }
    """

    # ========================================
    # LIGHT THEME - "Porcelain"
    # Clean, minimal, professional light theme
    # ========================================

    LIGHT_THEME = """
        /* ========================================
           MINIMAL CLEAN WHITE THEME
           No blue, no dark colors - pure minimal
           ======================================== */

        QMainWindow {
            background-color: #ffffff;
            color: #2d3748;
        }

        QWidget {
            background-color: #ffffff;
            color: #2d3748;
            font-family: 'Segoe UI', 'SF Pro Display', 'Roboto', sans-serif;
            font-size: 13px;
            font-weight: 400;
        }

        /* ========================================
           PANELS & CONTAINERS
           ======================================== */

        QFrame, QGroupBox {
            background-color: #fafafa;
            border: 1px solid #e5e7eb;
            border-radius: 4px;
            padding: 12px;
        }

        QGroupBox {
            margin-top: 18px;
            padding-top: 10px;
            font-weight: 500;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 6px;
            color: #4b5563;
            font-weight: 500;
            font-size: 13px;
        }

        /* ========================================
           BUTTONS - Minimal gray tones
           ======================================== */

        QPushButton {
            background-color: #f9fafb;
            color: #374151;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: 400;
            font-size: 13px;
            min-height: 18px;
        }

        QPushButton:hover {
            background-color: #f3f4f6;
            border-color: #9ca3af;
            color: #1f2937;
        }

        QPushButton:pressed {
            background-color: #e5e7eb;
        }

        QPushButton:disabled {
            background-color: #f3f4f6;
            color: #9ca3af;
            border-color: #e5e7eb;
        }

        QPushButton[class="primary"] {
            background-color: #4b5563;
            color: #ffffff;
            border: 1px solid #4b5563;
            font-weight: 500;
        }

        QPushButton[class="primary"]:hover {
            background-color: #374151;
        }

        QPushButton[class="success"] {
            background-color: #6b7280;
            color: #ffffff;
            border: 1px solid #6b7280;
            font-weight: 500;
        }

        QPushButton[class="success"]:hover {
            background-color: #4b5563;
        }

        QPushButton[class="danger"] {
            background-color: #9ca3af;
            color: #ffffff;
            border: 1px solid #9ca3af;
            font-weight: 500;
        }

        QPushButton[class="danger"]:hover {
            background-color: #6b7280;
        }

        QPushButton[class="warning"] {
            background-color: #d1d5db;
            color: #374151;
            border: 1px solid #d1d5db;
            font-weight: 500;
        }

        QPushButton[class="warning"]:hover {
            background-color: #9ca3af;
            color: #ffffff;
        }

        /* ========================================
           INPUTS
           ======================================== */

        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {
            background-color: #ffffff;
            color: #1f2937;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            padding: 7px 10px;
            font-size: 13px;
            selection-background-color: #e5e7eb;
            selection-color: #1f2937;
        }

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {
            border: 1px solid #9ca3af;
            background-color: #fafafa;
        }

        /* ========================================
           COMBOBOX
           ======================================== */

        QComboBox {
            background-color: #ffffff;
            color: #1f2937;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            padding: 7px 10px;
            font-size: 13px;
        }

        QComboBox:hover {
            border-color: #9ca3af;
        }

        QComboBox::drop-down {
            border: none;
            width: 20px;
        }

        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #6b7280;
            margin-right: 6px;
        }

        QComboBox QAbstractItemView {
            background-color: #ffffff;
            color: #1f2937;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            padding: 2px;
            selection-background-color: #f3f4f6;
            selection-color: #1f2937;
            outline: none;
        }

        QComboBox QAbstractItemView::item {
            padding: 6px 10px;
            border-radius: 2px;
            min-height: 18px;
        }

        QComboBox QAbstractItemView::item:hover {
            background-color: #f9fafb;
        }

        /* ========================================
           CHECKBOXES & RADIO BUTTONS
           ======================================== */

        QCheckBox, QRadioButton {
            color: #374151;
            spacing: 6px;
            font-size: 13px;
        }

        QCheckBox::indicator, QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid #d1d5db;
            border-radius: 3px;
            background-color: #ffffff;
        }

        QRadioButton::indicator {
            border-radius: 8px;
        }

        QCheckBox::indicator:hover, QRadioButton::indicator:hover {
            border-color: #9ca3af;
        }

        QCheckBox::indicator:checked, QRadioButton::indicator:checked {
            background-color: #6b7280;
            border-color: #6b7280;
        }

        /* ========================================
           TABS - Minimal underline style
           ======================================== */

        QTabWidget::pane {
            border: 1px solid #e5e7eb;
            background-color: #ffffff;
            border-radius: 4px;
            padding: 12px;
        }

        QTabWidget::tab-bar {
            left: 6px;
        }

        QTabBar::tab {
            background-color: transparent;
            color: #6b7280;
            padding: 8px 16px;
            margin-right: 2px;
            border-bottom: 2px solid transparent;
            font-weight: 400;
            font-size: 13px;
            min-width: 70px;
        }

        QTabBar::tab:hover {
            color: #374151;
            background-color: #f9fafb;
            border-radius: 4px 4px 0 0;
        }

        QTabBar::tab:selected {
            color: #1f2937;
            border-bottom: 2px solid #4b5563;
            font-weight: 500;
        }

        /* ========================================
           TABLES - Clean minimal grid
           ======================================== */

        QTableWidget, QTableView, QTreeWidget, QTreeView {
            background-color: #ffffff;
            alternate-background-color: #fafafa;
            color: #374151;
            gridline-color: #f3f4f6;
            border: 1px solid #e5e7eb;
            border-radius: 4px;
            padding: 2px;
            selection-background-color: #f3f4f6;
            selection-color: #1f2937;
            font-size: 13px;
        }

        QHeaderView::section {
            background-color: #fafafa;
            color: #4b5563;
            padding: 10px 12px;
            border: none;
            border-right: 1px solid #f3f4f6;
            border-bottom: 1px solid #e5e7eb;
            font-weight: 500;
            font-size: 12px;
        }

        QHeaderView::section:hover {
            background-color: #f3f4f6;
        }

        QTableWidget::item, QTableView::item, QTreeWidget::item, QTreeView::item {
            padding: 6px;
            border: none;
        }

        QTableWidget::item:selected, QTableView::item:selected,
        QTreeWidget::item:selected, QTreeView::item:selected {
            background-color: #f3f4f6;
            color: #1f2937;
        }

        QTableWidget::item:hover, QTableView::item:hover {
            background-color: #f9fafb;
        }

        /* ========================================
           LIST WIDGETS
           ======================================== */

        QListWidget {
            background-color: #ffffff;
            color: #374151;
            border: 1px solid #e5e7eb;
            border-radius: 4px;
            padding: 2px;
            font-size: 13px;
        }

        QListWidget::item {
            padding: 8px 10px;
            border-radius: 3px;
            margin: 1px;
        }

        QListWidget::item:hover {
            background-color: #f9fafb;
        }

        QListWidget::item:selected {
            background-color: #f3f4f6;
            color: #1f2937;
        }

        /* ========================================
           SCROLLBARS - Minimal light gray
           ======================================== */

        QScrollBar:vertical {
            background: #fafafa;
            width: 10px;
            margin: 0;
            border-radius: 5px;
        }

        QScrollBar::handle:vertical {
            background: #d1d5db;
            min-height: 25px;
            border-radius: 5px;
            margin: 2px;
        }

        QScrollBar::handle:vertical:hover {
            background: #9ca3af;
        }

        QScrollBar::handle:vertical:pressed {
            background: #6b7280;
        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }

        QScrollBar:horizontal {
            background: #fafafa;
            height: 10px;
            margin: 0;
            border-radius: 5px;
        }

        QScrollBar::handle:horizontal {
            background: #d1d5db;
            min-width: 25px;
            border-radius: 5px;
            margin: 2px;
        }

        QScrollBar::handle:horizontal:hover {
            background: #9ca3af;
        }

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }

        /* ========================================
           SPLITTERS
           ======================================== */

        QSplitter::handle {
            background-color: #e5e7eb;
            width: 1px;
            height: 1px;
        }

        QSplitter::handle:hover {
            background-color: #9ca3af;
        }

        /* ========================================
           STATUS BAR
           ======================================== */

        QStatusBar {
            background-color: #fafafa;
            color: #6b7280;
            border-top: 1px solid #e5e7eb;
            padding: 3px 6px;
            font-size: 12px;
        }

        QStatusBar::item {
            border: none;
        }

        /* ========================================
           MENU BAR & MENUS
           ======================================== */

        QMenuBar {
            background-color: #ffffff;
            border-bottom: 1px solid #e5e7eb;
            padding: 3px;
        }

        QMenuBar::item {
            spacing: 3px;
            padding: 5px 10px;
            background: transparent;
            border-radius: 4px;
            color: #374151;
        }

        QMenuBar::item:selected {
            background-color: #f3f4f6;
        }

        QMenuBar::item:pressed {
            background-color: #e5e7eb;
        }

        QMenu {
            background-color: #ffffff;
            color: #374151;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            padding: 3px;
        }

        QMenu::item {
            padding: 6px 20px 6px 10px;
            border-radius: 3px;
            margin: 1px;
        }

        QMenu::item:selected {
            background-color: #f3f4f6;
            color: #1f2937;
        }

        QMenu::separator {
            height: 1px;
            background-color: #e5e7eb;
            margin: 3px 6px;
        }

        /* ========================================
           TOOLBAR
           ======================================== */

        QToolBar {
            background-color: #ffffff;
            border-bottom: 1px solid #e5e7eb;
            spacing: 6px;
            padding: 6px;
        }

        QToolBar::separator {
            background-color: #e5e7eb;
            width: 1px;
            margin: 3px 6px;
        }

        /* ========================================
           PROGRESS BARS
           ======================================== */

        QProgressBar {
            background-color: #f3f4f6;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            text-align: center;
            color: #4b5563;
            font-weight: 500;
            font-size: 12px;
            min-height: 18px;
        }

        QProgressBar::chunk {
            background-color: #6b7280;
            border-radius: 3px;
        }

        /* ========================================
           LABELS
           ======================================== */

        QLabel {
            color: #374151;
            font-size: 13px;
        }

        QLabel[class="heading"] {
            font-size: 16px;
            font-weight: 500;
            color: #1f2937;
        }

        QLabel[class="subheading"] {
            font-size: 14px;
            font-weight: 400;
            color: #4b5563;
        }

        QLabel[class="caption"] {
            font-size: 11px;
            color: #6b7280;
        }

        QLabel[class="muted"] {
            color: #9ca3af;
        }

        /* ========================================
           TEXT BROWSER
           ======================================== */

        QTextBrowser {
            background-color: #fafafa;
            color: #374151;
            border: 1px solid #e5e7eb;
            border-radius: 4px;
            padding: 10px;
            font-size: 13px;
            selection-background-color: #e5e7eb;
            selection-color: #1f2937;
        }
    """

    def __init__(self) -> None:
        """Initialize the theme manager."""
        self.current_theme: Optional[str] = None

    def apply_theme(self, widget: QWidget, theme: str) -> None:
        """Apply a theme to the application."""
        if theme == "dark":
            stylesheet = self.DARK_THEME
        elif theme == "light":
            stylesheet = self.LIGHT_THEME
        else:
            raise ValueError(f"Unknown theme: {theme}")

        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet)

        self.current_theme = theme
