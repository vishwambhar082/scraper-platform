"""
Modern UI Components for Enterprise-Grade Interface.

This module provides production-ready, reusable UI components for building
modern, clean desktop applications with PySide6.

Components:
    IconSidebar: 80px icon-based navigation sidebar
    Card: Modern card component with title, body, timestamp
    ActivityCard: Specialized card for activity/email threads
    SectionHeader: Styled section headers with optional actions
    BulletList: Modern bullet list container
    BulletListItem: Individual bullet list item
    ActivityPanel: Right panel for activity feeds (350px)

Design Philosophy:
    - Clean, minimal aesthetics
    - Professional enterprise styling
    - Consistent spacing and typography
    - WCAG AA compliant colors
    - Cross-platform compatibility

Usage:
    from src.ui.modern_components import IconSidebar, Card, ActivityPanel

    # Create components
    sidebar = IconSidebar()
    card = Card("Title", "Body", "2h ago", clickable=True)
    activity = ActivityPanel("Recent Activity")

Version: 1.0
Author: Claude Code
License: MIT
"""

from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

__all__ = [
    "IconSidebar",
    "Card",
    "ActivityCard",
    "SectionHeader",
    "BulletList",
    "BulletListItem",
    "ActivityPanel",
]


class IconSidebar(QFrame):
    """
    Modern 80px icon-based sidebar navigation.

    Features:
    - Fixed 80px width
    - Icon-based buttons (24px)
    - Hover effects (#ececec)
    - Background: #f7f7f7
    - Right border: 1px solid #e0e0e0
    """

    page_changed = Signal(int)  # Emits page index when button clicked

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("modernSidebar")
        self.setFixedWidth(80)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # Button group for exclusive selection
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        self.buttons: List[QPushButton] = []

    def add_button(
        self,
        icon: QIcon,
        tooltip: str,
        page_index: int,
        checked: bool = False
    ) -> QPushButton:
        """Add an icon button to the sidebar."""
        btn = QPushButton()
        btn.setObjectName("sidebarIconButton")
        btn.setIcon(icon)
        btn.setIconSize(Qt.Size(24, 24))
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setFixedSize(56, 56)

        # Connect to signal
        btn.clicked.connect(lambda: self.page_changed.emit(page_index))

        # Add to button group and list
        self.button_group.addButton(btn, page_index)
        self.buttons.append(btn)

        # Add to layout
        self.layout().addWidget(btn, 0, Qt.AlignHCenter)

        return btn

    def add_spacer(self):
        """Add a spacer to push subsequent buttons down."""
        self.layout().addStretch()


class Card(QFrame):
    """
    Modern card component with clean styling.

    Features:
    - White background
    - 1px solid #e5e5e5 border
    - 8px border radius
    - 12px padding
    - Hover effect
    """

    clicked = Signal()  # Emits when card is clicked

    def __init__(
        self,
        title: str = "",
        body: str = "",
        timestamp: str = "",
        clickable: bool = False,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setProperty("cardStyle", True)
        self.clickable = clickable

        if clickable:
            self.setCursor(QCursor(Qt.PointingHandCursor))

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Header row (title + timestamp)
        if title or timestamp:
            header_layout = QHBoxLayout()
            header_layout.setSpacing(8)

            if title:
                self.title_label = QLabel(title)
                self.title_label.setProperty("cardTitle", True)
                self.title_label.setWordWrap(False)
                header_layout.addWidget(self.title_label)

            header_layout.addStretch()

            if timestamp:
                self.timestamp_label = QLabel(timestamp)
                self.timestamp_label.setProperty("cardTimestamp", True)
                header_layout.addWidget(self.timestamp_label)

            layout.addLayout(header_layout)

        # Body
        if body:
            self.body_label = QLabel(body)
            self.body_label.setProperty("cardBody", True)
            self.body_label.setWordWrap(True)
            layout.addWidget(self.body_label)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse clicks if clickable.

        Args:
            event: The mouse event containing click information
        """
        if self.clickable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_title(self, title: str):
        """Update card title."""
        if hasattr(self, 'title_label'):
            self.title_label.setText(title)

    def set_body(self, body: str):
        """Update card body."""
        if hasattr(self, 'body_label'):
            self.body_label.setText(body)

    def set_timestamp(self, timestamp: str):
        """Update card timestamp."""
        if hasattr(self, 'timestamp_label'):
            self.timestamp_label.setText(timestamp)


class ActivityCard(Card):
    """
    Specialized card for activity/email threads.

    Extends Card with additional features:
    - Preview text truncation
    - Read/unread indicator
    - Sender name display
    """

    def __init__(
        self,
        sender: str = "",
        subject: str = "",
        preview: str = "",
        timestamp: str = "",
        unread: bool = False,
        parent: Optional[QWidget] = None
    ):
        # Truncate preview to ~100 characters
        if len(preview) > 100:
            preview = preview[:97] + "..."

        super().__init__(
            title=subject,
            body=f"{sender}\n{preview}" if sender else preview,
            timestamp=timestamp,
            clickable=True,
            parent=parent
        )

        self.unread = unread

        # Add unread indicator if needed
        if unread:
            self.setStyleSheet("""
                QFrame[cardStyle="true"] {
                    border-left: 3px solid #4b5563;
                }
            """)


class SectionHeader(QWidget):
    """
    Modern section header with clean typography.

    Features:
    - 16-17px font size
    - Weight: 600
    - Color: #1a1a1a
    - Optional action button
    """

    def __init__(
        self,
        title: str,
        action_text: str = "",
        action_callback: Optional[Callable] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 8)
        layout.setSpacing(12)

        # Title
        title_label = QLabel(title)
        title_label.setProperty("class", "subheading")
        layout.addWidget(title_label)

        layout.addStretch()

        # Optional action button
        if action_text and action_callback:
            action_btn = QPushButton(action_text)
            action_btn.setCursor(QCursor(Qt.PointingHandCursor))
            action_btn.clicked.connect(action_callback)
            layout.addWidget(action_btn)


class BulletListItem(QFrame):
    """
    Modern bullet list item with hover effect.

    Features:
    - Normal font: 14-15px
    - Vertical spacing: 6-10px
    - Hover background: #f2f2f2
    - Optional right-aligned label
    """

    clicked = Signal()

    def __init__(
        self,
        text: str,
        right_label: str = "",
        clickable: bool = True,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.clickable = clickable

        if clickable:
            self.setCursor(QCursor(Qt.PointingHandCursor))

        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
            }
            QFrame:hover {
                background-color: #f2f2f2;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Bullet point
        bullet = QLabel("•")
        bullet.setStyleSheet("font-size: 16px; color: #666666;")
        layout.addWidget(bullet)

        # Text
        text_label = QLabel(text)
        text_label.setStyleSheet("font-size: 14px; color: #1a1a1a;")
        text_label.setWordWrap(True)
        layout.addWidget(text_label, 1)

        # Right label (optional)
        if right_label:
            right_label_widget = QLabel(right_label)
            right_label_widget.setStyleSheet("font-size: 13px; color: #777777;")
            layout.addWidget(right_label_widget)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse clicks.

        Args:
            event: The mouse event containing click information
        """
        if self.clickable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class BulletList(QWidget):
    """
    Container for bullet list items.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

    def add_item(
        self,
        text: str,
        right_label: str = "",
        clickable: bool = True
    ) -> BulletListItem:
        """Add a bullet item to the list."""
        item = BulletListItem(text, right_label, clickable, self)
        self.layout.addWidget(item)
        return item

    def clear(self):
        """Clear all items from the list."""
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


class ActivityPanel(QFrame):
    """
    Right panel for email/activity threads (350px width).

    Features:
    - Fixed 350px width
    - Vertical list of ActivityCards
    - Scrollable
    - 10px spacing between cards
    """

    def __init__(self, title: str = "Activity", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedWidth(350)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header
        header = QLabel(title)
        header.setProperty("class", "subheading")
        main_layout.addWidget(header)

        # Scroll area for cards
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
        main_layout.addWidget(scroll, 1)

        self.cards: List[ActivityCard] = []

    def add_card(
        self,
        sender: str = "",
        subject: str = "",
        preview: str = "",
        timestamp: str = "",
        unread: bool = False
    ) -> ActivityCard:
        """Add an activity card to the panel."""
        card = ActivityCard(sender, subject, preview, timestamp, unread, self.card_container)

        # Insert before the stretch
        self.card_layout.insertWidget(self.card_layout.count() - 1, card)
        self.cards.append(card)

        return card

    def clear_cards(self):
        """Clear all cards from the panel."""
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()
