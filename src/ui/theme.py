"""
Theme management for the desktop application.

Supports dark and light themes with smooth transitions.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QApplication, QWidget


class ThemeManager:
    """Manages application themes."""
    
    DARK_THEME = """
        QMainWindow {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QWidget {
            background-color: #252526;
            color: #cccccc;
        }
        QTabWidget::pane {
            border: 1px solid #3e3e42;
            background-color: #252526;
        }
        QTabBar::tab {
            background-color: #2d2d30;
            color: #cccccc;
            padding: 8px 16px;
            border: 1px solid #3e3e42;
        }
        QTabBar::tab:selected {
            background-color: #007acc;
            color: #ffffff;
        }
        QTableWidget {
            background-color: #1e1e1e;
            alternate-background-color: #252526;
            color: #cccccc;
            gridline-color: #3e3e42;
        }
        QHeaderView::section {
            background-color: #2d2d30;
            color: #ffffff;
            padding: 4px;
            border: 1px solid #3e3e42;
        }
        QTextEdit, QLineEdit {
            background-color: #1e1e1e;
            color: #cccccc;
            border: 1px solid #3e3e42;
            padding: 4px;
        }
        QPushButton {
            background-color: #0e639c;
            color: #ffffff;
            border: none;
            padding: 6px 12px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #1177bb;
        }
        QPushButton:pressed {
            background-color: #0a4d75;
        }
        QPushButton:disabled {
            background-color: #3e3e42;
            color: #808080;
        }
        QComboBox {
            background-color: #1e1e1e;
            color: #cccccc;
            border: 1px solid #3e3e42;
            padding: 4px;
        }
        QTreeWidget {
            background-color: #1e1e1e;
            color: #cccccc;
            alternate-background-color: #252526;
        }
        QStatusBar {
            background-color: #007acc;
            color: #ffffff;
        }
    """
    
    LIGHT_THEME = """
        QMainWindow {
            background-color: #ffffff;
            color: #000000;
        }
        QWidget {
            background-color: #f5f5f5;
            color: #000000;
        }
        QTabWidget::pane {
            border: 1px solid #d0d0d0;
            background-color: #ffffff;
        }
        QTabBar::tab {
            background-color: #e0e0e0;
            color: #000000;
            padding: 8px 16px;
            border: 1px solid #d0d0d0;
        }
        QTabBar::tab:selected {
            background-color: #0078d4;
            color: #ffffff;
        }
        QTableWidget {
            background-color: #ffffff;
            alternate-background-color: #f5f5f5;
            color: #000000;
            gridline-color: #d0d0d0;
        }
        QHeaderView::section {
            background-color: #e0e0e0;
            color: #000000;
            padding: 4px;
            border: 1px solid #d0d0d0;
        }
        QTextEdit, QLineEdit {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #d0d0d0;
            padding: 4px;
        }
        QPushButton {
            background-color: #0078d4;
            color: #ffffff;
            border: none;
            padding: 6px 12px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
        QPushButton:disabled {
            background-color: #d0d0d0;
            color: #808080;
        }
        QComboBox {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #d0d0d0;
            padding: 4px;
        }
        QTreeWidget {
            background-color: #ffffff;
            color: #000000;
            alternate-background-color: #f5f5f5;
        }
        QStatusBar {
            background-color: #0078d4;
            color: #ffffff;
        }
    """
    
    def __init__(self) -> None:
        """Initialize the theme manager."""
        self.current_theme: Optional[str] = None
    
    def apply_theme(self, widget: QWidget, theme: str) -> None:
        """Apply a theme to the application.
        
        Args:
            widget: Root widget to apply theme to
            theme: Theme name ('dark' or 'light')
        """
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

