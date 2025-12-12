# Enterprise-Grade PySide6 UI - Reference Implementation

A complete reference implementation of a modern, clean, enterprise-grade UI built with PySide6.

## Design Inspiration

This implementation is inspired by modern SaaS applications:
- **Notion** - Clean, minimal interface
- **Linear** - Professional typography and spacing
- **Asana** - Card-based layouts
- Modern enterprise dashboards

## Features

### Architecture
- **3-Pane Layout**
  - Left: 80px icon-based sidebar
  - Center: Main content panel (flexible width)
  - Right: Activity/email panel (350px)

### Components
- **Sidebar** - Icon-based navigation with hover effects
- **MainContent** - Clean content area with sections and bullet lists
- **EmailPanel** - Card-based activity feed

### Styling
- Clean white background (#ffffff)
- Subtle borders (#e5e5e5)
- Hover effects (#f2f2f2, #ececec)
- Professional typography (Inter, Segoe UI, Roboto)
- Generous spacing and padding

## File Structure

```
examples/modern-ui-reference/
├── main.py                 # Main application entry point
├── theme.qss              # QSS stylesheet
├── components/
│   ├── __init__.py
│   ├── sidebar.py         # 80px icon sidebar
│   ├── main_content.py    # Main content panel
│   └── email_panel.py     # Email/activity panel
└── README.md
```

## Running the Application

### Prerequisites
- Python 3.8+
- PySide6

### Installation

```bash
# Install dependencies
pip install PySide6

# Run the application
cd examples/modern-ui-reference
python main.py
```

## Component Details

### Sidebar (80px)
- Fixed 80px width
- Icon-based buttons (24px icons)
- Background: #f7f7f7
- Border-right: 1px solid #e0e0e0
- Hover effect: #ececec
- Selected: #e0e0e0

### Main Content Panel
- White background
- 32px padding
- Large heading (22px, weight 600)
- Section headers (16px, weight 600)
- Bullet lists with hover effects

### Email Panel (350px)
- Fixed 350px width
- Card-based layout
- 8px border radius
- 1px solid #e5e5e5 border
- 10px spacing between cards
- Hover effect on cards

## Customization

### Colors
All colors are defined in `theme.qss`. Key colors:
- **Background**: #ffffff (white)
- **Sidebar**: #f7f7f7 (light gray)
- **Borders**: #e5e5e5, #e0e0e0
- **Hover**: #f2f2f2, #ececec
- **Text**: #1a1a1a (primary), #666666 (muted)

### Typography
- **Headings**: 22px, weight 600
- **Section Titles**: 16px, weight 600
- **Body**: 14px, weight 400
- **Secondary**: 13px
- **Timestamps**: 12px

### Layout
- **Sidebar width**: 80px (change in `sidebar.py`)
- **Email panel width**: 350px (change in `email_panel.py`)
- **Content padding**: 32px (change in `main_content.py`)

## Integration with Existing Projects

To integrate these components into your project:

1. **Copy the components** to your project's UI directory
2. **Copy the theme.qss** styles into your existing stylesheet
3. **Import and use** the components:

```python
from components import Sidebar, MainContent, EmailPanel

# In your main window
layout = QHBoxLayout()
layout.addWidget(Sidebar())
layout.addWidget(MainContent(), 1)  # Flexible width
layout.addWidget(EmailPanel())
```

## Design Principles

This implementation follows these principles:

1. **Minimal** - No unnecessary elements or decoration
2. **Clean** - Generous white space and clear hierarchy
3. **Professional** - Enterprise-grade aesthetics
4. **Consistent** - Uniform spacing, colors, and typography
5. **Accessible** - Clear contrast and readable fonts

## Screenshots

Run the application to see:
- Icon-based sidebar navigation
- Clean main content with sections
- Card-based email/activity panel
- Professional hover effects
- Enterprise-grade typography

## License

This reference implementation is provided as-is for educational and development purposes.

## Support

For questions or issues with this reference implementation, please refer to:
- PySide6 Documentation: https://doc.qt.io/qtforpython/
- Qt Stylesheet Reference: https://doc.qt.io/qt-6/stylesheet-reference.html
