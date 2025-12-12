"""
Enterprise-Grade PySide6 UI Reference Implementation.

A complete example of modern, clean UI design inspired by:
- Notion
- Linear
- Asana
- Modern SaaS dashboards

Features:
- 80px icon-based sidebar
- Main content panel with clean typography
- Right panel for email/activity threads
- Professional light theme
- Card-based components
"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
)

# Import components
from components.sidebar import Sidebar
from components.main_content import MainContent
from components.email_panel import EmailPanel


class MainWindow(QMainWindow):
    """Main application window with 3-pane layout."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enterprise-Grade UI - Reference Implementation")
        self.setGeometry(100, 100, 1400, 900)

        # Setup UI
        self.setup_ui()

        # Load sample data
        self.load_sample_data()

    def setup_ui(self):
        """Setup the main 3-pane layout."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main horizontal layout: Sidebar | Content | Email Panel
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # LEFT: Sidebar (80px)
        self.sidebar = Sidebar(self)
        self.sidebar.page_changed.connect(self.on_page_changed)

        # Add sidebar buttons with standard icons
        app = QApplication.instance()
        style = app.style()

        # Use Qt standard icons (cross-platform)
        from PySide6.QtWidgets import QStyle

        self.sidebar.add_button(
            style.standardIcon(QStyle.SP_FileDialogContentsView),
            "Dashboard",
            0,
            checked=True
        )
        self.sidebar.add_button(
            style.standardIcon(QStyle.SP_FileDialogDetailedView),
            "Projects",
            1
        )
        self.sidebar.add_button(
            style.standardIcon(QStyle.SP_FileIcon),
            "Documents",
            2
        )
        self.sidebar.add_button(
            style.standardIcon(QStyle.SP_DirIcon),
            "Files",
            3
        )

        # Spacer
        self.sidebar.add_spacer()

        # Settings at bottom
        self.sidebar.add_button(
            style.standardIcon(QStyle.SP_FileDialogInfoView),
            "Settings",
            4
        )

        main_layout.addWidget(self.sidebar)

        # MIDDLE: Main Content Panel (flexible width)
        self.main_content = MainContent(self)
        main_layout.addWidget(self.main_content, 1)

        # RIGHT: Email Panel (350px)
        self.email_panel = EmailPanel(self)
        main_layout.addWidget(self.email_panel)

    def load_sample_data(self):
        """Load sample data to demonstrate the UI.

        NOTE: This is demonstration data only. In production, replace this method
        with real data loading from your application's data sources.

        Example production usage:
            # Load from database
            updates = get_recent_updates()
            for update in updates:
                self.main_content.add_bullet_item(update.text, update.author)

            # Load from API
            activities = fetch_user_activities()
            for activity in activities:
                self.email_panel.add_email_card(
                    activity.title,
                    activity.preview,
                    activity.timestamp
                )
        """
        # Demonstration sections - replace with real data in production
        self.main_content.add_section("Recent Updates")
        self.main_content.add_bullet_item("No recent updates")

        self.main_content.add_section("Items")
        self.main_content.add_bullet_item("No items to display")

        self.main_content.add_section("Quick Links")
        self.main_content.add_bullet_item("Add your content here")

        # Demonstration activity - replace with real data in production
        self.email_panel.add_email_card(
            "Welcome",
            "This is a demonstration of the Modern UI components. Replace with real data in production.",
            "Now"
        )

    def on_page_changed(self, page_index):
        """Handle sidebar navigation."""
        print(f"Switched to page: {page_index}")
        # In a real app, you would switch the main content here
        pages = ["Dashboard", "Projects", "Documents", "Files", "Settings"]
        if page_index < len(pages):
            self.main_content.title_label.setText(pages[page_index])


def main():
    """Main entry point."""
    app = QApplication(sys.argv)

    # Load stylesheet
    qss_path = Path(__file__).parent / "theme.qss"
    if qss_path.exists():
        with open(qss_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
