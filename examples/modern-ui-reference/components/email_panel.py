"""
Email Thread Panel Component (Right Panel).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget


class EmailCard(QFrame):
    """
    Individual email thread card.
    """

    def __init__(self, title, body, timestamp, parent=None):
        super().__init__(parent)
        self.setProperty("emailCard", True)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header row (title + timestamp)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #1a1a1a;")
        title_label.setWordWrap(False)
        header_layout.addWidget(title_label, 1)

        # Timestamp
        time_label = QLabel(timestamp)
        time_label.setProperty("timestamp", True)
        time_label.setAlignment(Qt.AlignRight)
        header_layout.addWidget(time_label)

        layout.addLayout(header_layout)

        # Body
        body_label = QLabel(body)
        body_label.setProperty("secondary", True)
        body_label.setStyleSheet("font-size: 13px;")
        body_label.setWordWrap(True)
        layout.addWidget(body_label)


class EmailPanel(QFrame):
    """
    Right panel for email thread list (350px width).

    Features:
    - Fixed 350px width
    - Vertical card list
    - 10px spacing between cards
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(350)
        self.setStyleSheet("background-color: #ffffff; padding: 16px;")

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QLabel("Activity")
        header.setProperty("sectionTitle", True)
        layout.addWidget(header)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Container for cards
        self.card_container = QWidget()
        self.card_layout = QVBoxLayout(self.card_container)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setSpacing(10)
        self.card_layout.addStretch()

        scroll.setWidget(self.card_container)
        layout.addWidget(scroll, 1)

    def add_email_card(self, title, body, timestamp):
        """Add an email card to the panel."""
        card = EmailCard(title, body, timestamp, self.card_container)
        # Insert before the stretch
        self.card_layout.insertWidget(self.card_layout.count() - 1, card)
        return card
