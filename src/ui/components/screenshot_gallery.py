"""
Screenshot Gallery Component.

Provides a timeline viewer for browsing screenshots:
- Thumbnail grid view
- Fullscreen viewer
- Timeline scrubbing
- Metadata display
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QImage, QIcon
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QPushButton,
    QSlider,
    QFileDialog,
    QMessageBox,
    QScrollArea,
)

from src.common.logging_utils import get_logger

log = get_logger("ui.components.screenshot_gallery")


class ScreenshotGallery(QWidget):
    """
    Screenshot gallery component for browsing captured screenshots.

    Features:
    - Thumbnail grid view
    - Fullscreen image viewer
    - Timeline navigation
    - Screenshot metadata
    - Export capabilities

    Signals:
        screenshot_selected: Emitted when a screenshot is selected (filepath)
        screenshot_opened: Emitted when opening screenshot in fullscreen (filepath)
    """

    screenshot_selected = Signal(str)  # filepath
    screenshot_opened = Signal(str)  # filepath

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.screenshots: List[Path] = []
        self.current_index = 0
        self.screenshot_dir = Path("screenshots")
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Screenshot Gallery")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1f2937;")
        header.addWidget(title)
        header.addStretch()

        # Browse button
        browse_btn = QPushButton("Browse Folder")
        browse_btn.clicked.connect(self._browse_folder)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        header.addWidget(browse_btn)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # Thumbnail grid
        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setViewMode(QListWidget.IconMode)
        self.thumbnail_list.setIconSize(QSize(150, 150))
        self.thumbnail_list.setSpacing(10)
        self.thumbnail_list.setResizeMode(QListWidget.Adjust)
        self.thumbnail_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.thumbnail_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.thumbnail_list.setStyleSheet("""
            QListWidget {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 4px;
            }
            QListWidget::item {
                background-color: white;
                border: 2px solid #e5e7eb;
                border-radius: 4px;
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: #dbeafe;
                border-color: #3b82f6;
            }
            QListWidget::item:hover {
                border-color: #93c5fd;
            }
        """)
        layout.addWidget(self.thumbnail_list, 3)

        # Timeline slider
        timeline_layout = QHBoxLayout()
        timeline_layout.addWidget(QLabel("Timeline:"))

        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setMinimum(0)
        self.timeline_slider.setMaximum(0)
        self.timeline_slider.valueChanged.connect(self._on_slider_changed)
        timeline_layout.addWidget(self.timeline_slider, 1)

        self.position_label = QLabel("0 / 0")
        timeline_layout.addWidget(self.position_label)

        layout.addLayout(timeline_layout)

        # Preview section
        preview_label = QLabel("Preview")
        preview_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 8px;")
        layout.addWidget(preview_label)

        # Scrollable preview area
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setMinimumHeight(200)
        preview_scroll.setMaximumHeight(300)

        self.preview_image = QLabel()
        self.preview_image.setAlignment(Qt.AlignCenter)
        self.preview_image.setStyleSheet("background-color: #1f2937; padding: 8px;")
        self.preview_image.setText("No screenshot selected")
        self.preview_image.setTextFormat(Qt.PlainText)
        self.preview_image.setScaledContents(False)

        preview_scroll.setWidget(self.preview_image)
        layout.addWidget(preview_scroll, 1)

        # Metadata section
        self.metadata_label = QLabel("Metadata: No screenshot selected")
        self.metadata_label.setStyleSheet("""
            QLabel {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10px;
            }
        """)
        self.metadata_label.setWordWrap(True)
        layout.addWidget(self.metadata_label)

        # Action buttons
        action_layout = QHBoxLayout()

        open_fullscreen_btn = QPushButton("Open Fullscreen")
        open_fullscreen_btn.clicked.connect(self._open_fullscreen)
        open_fullscreen_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        action_layout.addWidget(open_fullscreen_btn)

        export_btn = QPushButton("Export Selected")
        export_btn.clicked.connect(self._export_selected)
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        action_layout.addWidget(export_btn)

        action_layout.addStretch()

        layout.addLayout(action_layout)

    def _browse_folder(self) -> None:
        """Browse for screenshot folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Screenshot Folder",
            str(self.screenshot_dir)
        )

        if folder:
            self.screenshot_dir = Path(folder)
            self.refresh()

    def refresh(self) -> None:
        """Refresh the screenshot gallery."""
        try:
            # Find all screenshot files
            if not self.screenshot_dir.exists():
                self.screenshot_dir.mkdir(parents=True, exist_ok=True)

            # Look for common image formats
            patterns = ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp"]
            screenshots = []
            for pattern in patterns:
                screenshots.extend(self.screenshot_dir.glob(pattern))

            # Sort by modification time
            screenshots.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            self.screenshots = screenshots
            self._populate_thumbnails()

            log.info(f"Found {len(screenshots)} screenshots in {self.screenshot_dir}")

        except Exception as e:
            log.error(f"Failed to refresh screenshot gallery: {e}")
            QMessageBox.warning(self, "Refresh Error", f"Failed to load screenshots: {e}")

    def _populate_thumbnails(self) -> None:
        """Populate the thumbnail grid."""
        self.thumbnail_list.clear()

        for screenshot in self.screenshots:
            try:
                # Load image
                pixmap = QPixmap(str(screenshot))

                if pixmap.isNull():
                    continue

                # Create thumbnail
                thumbnail = pixmap.scaled(
                    150, 150,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )

                # Create list item
                item = QListWidgetItem(QIcon(thumbnail), screenshot.name)
                item.setData(Qt.UserRole, str(screenshot))
                self.thumbnail_list.addItem(item)

            except Exception as e:
                log.warning(f"Failed to load thumbnail for {screenshot}: {e}")

        # Update timeline slider
        self.timeline_slider.setMaximum(max(0, len(self.screenshots) - 1))
        self._update_position_label()

    def _on_selection_changed(self) -> None:
        """Handle thumbnail selection."""
        items = self.thumbnail_list.selectedItems()
        if items:
            filepath = items[0].data(Qt.UserRole)
            self._load_preview(filepath)
            self.screenshot_selected.emit(filepath)

            # Update timeline slider
            index = self._get_screenshot_index(filepath)
            if index >= 0:
                self.current_index = index
                self.timeline_slider.setValue(index)

    def _on_slider_changed(self, value: int) -> None:
        """Handle timeline slider change."""
        if 0 <= value < len(self.screenshots):
            self.current_index = value
            filepath = str(self.screenshots[value])
            self._load_preview(filepath)
            self._update_position_label()

            # Select in thumbnail list
            for i in range(self.thumbnail_list.count()):
                item = self.thumbnail_list.item(i)
                if item.data(Qt.UserRole) == filepath:
                    self.thumbnail_list.setCurrentItem(item)
                    break

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on thumbnail."""
        filepath = item.data(Qt.UserRole)
        self._open_fullscreen_path(filepath)

    def _load_preview(self, filepath: str) -> None:
        """Load preview image."""
        try:
            pixmap = QPixmap(filepath)

            if pixmap.isNull():
                self.preview_image.setText("Failed to load image")
                return

            # Scale to fit preview area while maintaining aspect ratio
            scaled = pixmap.scaled(
                self.preview_image.width() - 16,
                self.preview_image.height() - 16,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            self.preview_image.setPixmap(scaled)

            # Load metadata
            self._load_metadata(Path(filepath))

        except Exception as e:
            log.error(f"Failed to load preview: {e}")
            self.preview_image.setText(f"Error: {e}")

    def _load_metadata(self, filepath: Path) -> None:
        """Load and display screenshot metadata."""
        try:
            stat = filepath.stat()
            metadata = [
                f"Filename: {filepath.name}",
                f"Size: {stat.st_size / 1024:.1f} KB",
                f"Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}",
                f"Path: {filepath}",
            ]

            # Try to get image dimensions
            try:
                image = QImage(str(filepath))
                metadata.append(f"Dimensions: {image.width()} x {image.height()}")
            except:
                pass

            self.metadata_label.setText("\n".join(metadata))

        except Exception as e:
            log.error(f"Failed to load metadata: {e}")
            self.metadata_label.setText(f"Metadata: Error loading - {e}")

    def _update_position_label(self) -> None:
        """Update position label."""
        total = len(self.screenshots)
        current = self.current_index + 1 if total > 0 else 0
        self.position_label.setText(f"{current} / {total}")

    def _get_screenshot_index(self, filepath: str) -> int:
        """Get the index of a screenshot by filepath."""
        for i, screenshot in enumerate(self.screenshots):
            if str(screenshot) == filepath:
                return i
        return -1

    def _open_fullscreen(self) -> None:
        """Open selected screenshot in fullscreen."""
        items = self.thumbnail_list.selectedItems()
        if items:
            filepath = items[0].data(Qt.UserRole)
            self._open_fullscreen_path(filepath)

    def _open_fullscreen_path(self, filepath: str) -> None:
        """Open a screenshot in fullscreen viewer."""
        # For now, just open with default system viewer
        import os
        import sys
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl.fromLocalFile(filepath))
        self.screenshot_opened.emit(filepath)

    def _export_selected(self) -> None:
        """Export selected screenshot."""
        items = self.thumbnail_list.selectedItems()
        if not items:
            QMessageBox.warning(self, "No Selection", "Please select a screenshot to export")
            return

        filepath = items[0].data(Qt.UserRole)
        source_path = Path(filepath)

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Screenshot",
            source_path.name,
            f"Images (*{source_path.suffix});;All Files (*)"
        )

        if save_path:
            try:
                import shutil
                shutil.copy2(filepath, save_path)
                QMessageBox.information(self, "Export Complete", f"Screenshot exported to:\n{save_path}")
                log.info(f"Screenshot exported to {save_path}")
            except Exception as e:
                log.error(f"Failed to export screenshot: {e}")
                QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")

    def set_screenshot_dir(self, directory: Path) -> None:
        """Set the screenshot directory."""
        self.screenshot_dir = directory
        self.refresh()

    def get_selected_screenshot(self) -> Optional[str]:
        """Get the currently selected screenshot filepath."""
        items = self.thumbnail_list.selectedItems()
        if items:
            return items[0].data(Qt.UserRole)
        return None
