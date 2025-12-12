# Modern UI Integration Guide

This guide explains how to use the new enterprise-grade UI components in the Scraper Platform.

## Overview

The platform now includes modern UI components inspired by enterprise SaaS applications like Notion, Linear, and Asana. These components provide a clean, professional interface with:

- **80px icon-based sidebar** - Minimal navigation
- **Card components** - Modern content containers
- **Activity panels** - Right-side activity feeds
- **Enhanced light theme** - Professional color palette

## Quick Start

### 1. Standalone Reference Implementation

The fastest way to see the modern UI in action is to run the standalone reference implementation:

```bash
cd examples/modern-ui-reference
python main.py
```

This demonstrates:
- 3-pane layout (sidebar | content | activity panel)
- Modern card components
- Professional typography
- Clean hover effects

### 2. Using Components in Your Code

Import the components:

```python
from src.ui.modern_components import (
    IconSidebar,
    Card,
    ActivityCard,
    SectionHeader,
    BulletList,
    ActivityPanel,
)
```

## Component Reference

### IconSidebar

An 80px icon-based navigation sidebar.

**Features:**
- Fixed 80px width
- Icon buttons (24px)
- Background: #f7f7f7
- Border-right: 1px solid #e0e0e0
- Hover effect: #ececec

**Usage:**

```python
from src.ui.modern_components import IconSidebar

# Create sidebar
sidebar = IconSidebar()

# Add buttons
sidebar.add_button(
    icon=QIcon("path/to/icon.png"),
    tooltip="Dashboard",
    page_index=0,
    checked=True
)

sidebar.add_button(
    icon=QIcon("path/to/icon.png"),
    tooltip="Settings",
    page_index=1
)

# Add spacer to separate button groups
sidebar.add_spacer()

# Connect to page changes
sidebar.page_changed.connect(lambda page: print(f"Page {page}"))
```

### Card

A modern card component with clean styling.

**Features:**
- White background
- 1px solid #e5e5e5 border
- 8px border radius
- Hover effect
- Optional click handling

**Usage:**

```python
from src.ui.modern_components import Card

# Create a simple card
card = Card(
    title="Task Completed",
    body="The data processing pipeline completed successfully.",
    timestamp="2h ago",
    clickable=True
)

# Connect to clicks
card.clicked.connect(lambda: print("Card clicked!"))

# Update card content
card.set_title("New Title")
card.set_body("Updated body text")
card.set_timestamp("Just now")
```

### ActivityCard

Specialized card for activity feeds and email threads.

**Features:**
- Extends Card with sender/preview display
- Automatic text truncation
- Unread indicator
- Preview text limited to ~100 characters

**Usage:**

```python
from src.ui.modern_components import ActivityCard

card = ActivityCard(
    sender="John Doe",
    subject="Pipeline Run Complete",
    preview="Your scheduled pipeline run completed successfully. All 1,245 records processed.",
    timestamp="5m ago",
    unread=True
)

card.clicked.connect(lambda: handle_activity_click())
```

### ActivityPanel

A 350px right panel for activity feeds.

**Features:**
- Fixed 350px width
- Vertical card list
- Automatic scrolling
- 10px spacing between cards

**Usage:**

```python
from src.ui.modern_components import ActivityPanel

# Create panel
panel = ActivityPanel(title="Recent Activity")

# Add activity cards
panel.add_card(
    sender="System",
    subject="Backup Complete",
    preview="Automated backup completed successfully.",
    timestamp="10m ago"
)

panel.add_card(
    sender="Alice Johnson",
    subject="Data Review",
    preview="I've reviewed the data quality report. Looks good!",
    timestamp="1h ago",
    unread=True
)

# Clear all cards
panel.clear_cards()
```

### SectionHeader

A styled section header with optional action button.

**Usage:**

```python
from src.ui.modern_components import SectionHeader

header = SectionHeader(
    title="Recent Jobs",
    action_text="View All",
    action_callback=lambda: print("View all clicked")
)

# Add to layout
layout.addWidget(header)
```

### BulletList

A modern bullet list with hover effects.

**Usage:**

```python
from src.ui.modern_components import BulletList

# Create list
bullet_list = BulletList()

# Add items
bullet_list.add_item(
    text="Pipeline execution completed successfully",
    right_label="Lisa Torres",
    clickable=True
)

bullet_list.add_item(
    text="Data validation passed all checks",
    right_label="2h ago"
)

# Clear items
bullet_list.clear()
```

## Layout Patterns

### 3-Pane Layout (Recommended)

The modern enterprise pattern: Sidebar | Content | Activity Panel

```python
from PySide6.QtWidgets import QHBoxLayout
from src.ui.modern_components import IconSidebar, ActivityPanel

# Main horizontal layout
layout = QHBoxLayout()
layout.setContentsMargins(0, 0, 0, 0)
layout.setSpacing(0)

# Left: Sidebar (80px)
sidebar = IconSidebar()
layout.addWidget(sidebar)

# Center: Main content (flexible)
content = YourContentWidget()
layout.addWidget(content, 1)  # stretch factor = 1

# Right: Activity panel (350px)
activity = ActivityPanel(title="Activity Feed")
layout.addWidget(activity)
```

### Content Panel with Cards

Create a clean content area with modern cards:

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from src.ui.modern_components import Card, SectionHeader

# Container
container = QWidget()
layout = QVBoxLayout(container)
layout.setContentsMargins(32, 32, 32, 32)
layout.setSpacing(24)

# Add header
header = SectionHeader(
    title="Pipeline Runs",
    action_text="Refresh",
    action_callback=refresh_runs
)
layout.addWidget(header)

# Add cards
for run in recent_runs:
    card = Card(
        title=f"Run #{run.id}",
        body=f"Status: {run.status}",
        timestamp=run.timestamp,
        clickable=True
    )
    card.clicked.connect(lambda r=run: view_run_details(r))
    layout.addWidget(card)
```

## Theme Customization

The enhanced light theme is automatically applied when you use `ThemeManager`:

```python
from src.ui.theme import ThemeManager

theme_manager = ThemeManager()
theme_manager.apply_theme(self, "light")  # Enterprise-grade light theme
```

### Custom Colors

You can customize colors in [src/ui/theme.py](src/ui/theme.py):

**Key Color Variables:**
- Sidebar background: `#f7f7f7`
- Border colors: `#e5e5e5`, `#e0e0e0`
- Hover effects: `#f2f2f2`, `#ececec`
- Text colors: `#1a1a1a` (primary), `#666666` (muted), `#777777` (secondary)

### Custom Styling

Apply custom styles to components using QSS properties:

```python
# Card with custom border color
card = Card("Title", "Body")
card.setStyleSheet("""
    QFrame[cardStyle="true"] {
        border: 2px solid #4b5563;
    }
""")

# Custom sidebar button
button.setObjectName("sidebarIconButton")
# Style applied automatically via theme
```

## Integration Examples

### Example 1: Modern Dashboard Page

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout
from src.ui.modern_components import SectionHeader, Card, BulletList

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)

        # Header
        layout.addWidget(SectionHeader("Dashboard", "Refresh", self.refresh))

        # Stats cards
        stats_card = Card(
            title="Pipeline Statistics",
            body="12 runs today, 10 successful, 2 pending"
        )
        layout.addWidget(stats_card)

        # Recent activity
        layout.addWidget(SectionHeader("Recent Activity"))
        recent_list = BulletList()
        recent_list.add_item("Pipeline completed", "2m ago")
        recent_list.add_item("Data exported", "15m ago")
        layout.addWidget(recent_list)

    def refresh(self):
        # Refresh logic
        pass
```

### Example 2: Activity Feed

```python
from src.ui.modern_components import ActivityPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Create activity panel
        self.activity_panel = ActivityPanel("System Events")

        # Add to layout
        main_layout.addWidget(self.activity_panel)

        # Populate with events
        self.load_recent_events()

    def load_recent_events(self):
        events = get_recent_events()

        for event in events:
            self.activity_panel.add_card(
                sender=event.user,
                subject=event.title,
                preview=event.description,
                timestamp=event.time_ago,
                unread=not event.read
            )
```

### Example 3: Icon Sidebar Navigation

```python
from PySide6.QtWidgets import QStackedWidget, QStyle
from src.ui.modern_components import IconSidebar

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Create sidebar
        self.sidebar = IconSidebar()

        # Add navigation buttons
        style = self.style()
        self.sidebar.add_button(
            style.standardIcon(QStyle.SP_FileDialogContentsView),
            "Dashboard", 0, checked=True
        )
        self.sidebar.add_button(
            style.standardIcon(QStyle.SP_FileIcon),
            "Jobs", 1
        )

        # Create stacked widget for pages
        self.pages = QStackedWidget()
        self.pages.addWidget(DashboardPage())
        self.pages.addWidget(JobsPage())

        # Connect sidebar to pages
        self.sidebar.page_changed.connect(self.pages.setCurrentIndex)
```

## Best Practices

### 1. Consistent Spacing

Use the design system spacing:
- Small: 8-12px
- Medium: 16-20px
- Large: 24-32px

### 2. Typography Hierarchy

- **Headings**: 22px, weight 600
- **Section Titles**: 16px, weight 600
- **Body**: 14px, weight 400
- **Secondary**: 13px, color #777777
- **Timestamps**: 12px, color #999999

### 3. Card Usage

- Use cards for distinct content blocks
- Keep card content concise
- Use timestamps for time-sensitive info
- Enable clickable for interactive cards

### 4. Activity Panel

- Limit to ~5-10 recent items
- Use timestamps consistently
- Mark unread items clearly
- Update in real-time when possible

### 5. Icon Sidebar

- Keep icons simple and clear
- Use consistent icon style
- Limit to 5-8 main items
- Group related items with spacers

## Migration Guide

### Updating Existing Pages

To migrate an existing page to use modern components:

1. **Replace standard layouts with content panel:**
   ```python
   # Old
   layout = QVBoxLayout()
   layout.addWidget(QLabel("Title"))

   # New
   layout = QVBoxLayout()
   layout.setContentsMargins(32, 32, 32, 32)
   layout.addWidget(SectionHeader("Title"))
   ```

2. **Replace lists with BulletList:**
   ```python
   # Old
   list_widget = QListWidget()
   list_widget.addItem("Item 1")

   # New
   bullet_list = BulletList()
   bullet_list.add_item("Item 1", right_label="Info")
   ```

3. **Replace panels with Cards:**
   ```python
   # Old
   panel = QGroupBox("Title")
   label = QLabel("Content")

   # New
   card = Card(title="Title", body="Content")
   ```

## Troubleshooting

### Icons Not Showing
- Ensure QStyle icons are used for cross-platform compatibility
- Check icon file paths are correct
- Verify icon size is set: `setIconSize(Qt.Size(24, 24))`

### Styling Not Applied
- Verify theme is applied: `theme_manager.apply_theme(widget, "light")`
- Check object names are set correctly (e.g., `setObjectName("modernSidebar")`)
- Ensure properties are set (e.g., `setProperty("cardStyle", True)`)

### Layout Issues
- Use `setContentsMargins(0, 0, 0, 0)` for tight layouts
- Use `addStretch()` to push items to top/bottom
- Set size policies: `setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)`

## Resources

- **Reference Implementation**: `examples/modern-ui-reference/`
- **Component Source**: `src/ui/modern_components.py`
- **Theme Source**: `src/ui/theme.py`
- **PySide6 Docs**: https://doc.qt.io/qtforpython/
- **Qt Stylesheets**: https://doc.qt.io/qt-6/stylesheet-reference.html

## Support

For questions or issues with the modern UI components:
1. Check this guide first
2. Review the reference implementation
3. Examine the component source code
4. Test with the standalone example

---

**Version**: 1.0
**Last Updated**: 2025-12-12
**Compatible with**: PySide6 6.0+
