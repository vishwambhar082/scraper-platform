"""
Modern 80px Icon-Based Sidebar Component.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QCursor
from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QButtonGroup


class Sidebar(QFrame):
    """
    80px icon-based sidebar with modern styling.

    Features:
    - Fixed 80px width
    - Icon buttons (24px)
    - Hover effect: #ececec
    - Selected: #e0e0e0
    """

    page_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(80)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # Button group
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        self.main_layout = layout

    def add_button(self, icon, tooltip, page_index, checked=False):
        """Add an icon button to the sidebar."""
        btn = QPushButton()
        btn.setObjectName("sidebarButton")
        btn.setIcon(icon)
        btn.setIconSize(Qt.Size(24, 24))
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setFixedSize(56, 56)

        btn.clicked.connect(lambda: self.page_changed.emit(page_index))

        self.button_group.addButton(btn, page_index)
        self.main_layout.addWidget(btn, 0, Qt.AlignHCenter)

        return btn

    def add_spacer(self):
        """Add a spacer to separate button groups."""
        self.main_layout.addStretch()
