"""
Main Content Panel Component.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget


class MainContent(QFrame):
    """
    Main content panel with enterprise styling.

    Features:
    - White background
    - Generous padding (24-32px)
    - Clean typography
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mainContent")

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # Header
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(16)

        # Title
        self.title_label = QLabel("Dashboard")
        self.title_label.setProperty("heading", True)
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()

        layout.addLayout(self.header_layout)

        # Subtitle row (optional metadata)
        self.subtitle_layout = QHBoxLayout()
        self.subtitle_layout.setSpacing(20)
        self.subtitle_layout.addStretch()
        layout.addLayout(self.subtitle_layout)

        # Content area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(20)

        layout.addWidget(self.content_widget, 1)

    def add_section(self, title):
        """Add a section to the content area."""
        section_title = QLabel(title)
        section_title.setProperty("sectionTitle", True)
        section_title.setContentsMargins(0, 20, 0, 10)
        self.content_layout.addWidget(section_title)
        return section_title

    def add_bullet_item(self, text, right_label=""):
        """Add a bullet list item."""
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 6, 0, 6)
        item_layout.setSpacing(12)

        # Bullet
        bullet = QLabel("•")
        bullet.setStyleSheet("font-size: 16px; color: #666666;")
        item_layout.addWidget(bullet)

        # Text
        text_label = QLabel(text)
        text_label.setStyleSheet("font-size: 14px; color: #1a1a1a;")
        item_layout.addWidget(text_label, 1)

        # Right label
        if right_label:
            right_widget = QLabel(right_label)
            right_widget.setProperty("muted", True)
            item_layout.addWidget(right_widget)

        # Hover effect
        item_widget.setStyleSheet("""
            QWidget:hover {
                background-color: #f2f2f2;
                border-radius: 4px;
            }
        """)

        self.content_layout.addWidget(item_widget)
        return item_widget
