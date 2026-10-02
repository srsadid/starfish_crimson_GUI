"""
theme.py — Shared STARFiSh UI theme for all panels.

A single stylesheet applied at the VascularEditorWidget level cascades
to all child panels (Model Builder, VMTK Centerlines, Result Visualization).
"""

STARFISH_STYLESHEET = """
QWidget {
    font-size: 12px;
}

QLabel#sectionHeader {
    font-size: 11px;
    font-weight: 600;
    color: #9ab0cc;
    padding: 5px 0 2px 0;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

QGroupBox {
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 4px;
    margin-top: 14px;
    padding: 10px 6px 6px 6px;
    font-size: 11px;
    font-weight: 600;
    color: #a0b4cc;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: #a0b4cc;
    background: transparent;
}

QPushButton {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.16);
    border-radius: 3px;
    color: #d8e4f0;
    font-size: 12px;
    min-height: 22px;
    padding: 3px 8px;
}
QPushButton:hover {
    background: rgba(255,255,255,0.14);
    border-color: rgba(255,255,255,0.26);
}
QPushButton:pressed {
    background: rgba(0,0,0,0.2);
}
QPushButton:disabled {
    color: rgba(200,210,220,0.35);
    border-color: rgba(255,255,255,0.07);
}

QPushButton[sfRole="primary"] {
    background: rgba(45,108,200,0.75);
    border: 1px solid rgba(80,140,230,0.6);
    color: #ffffff;
    font-weight: 600;
}
QPushButton[sfRole="primary"]:hover  { background: rgba(55,120,215,0.9); }
QPushButton[sfRole="primary"]:pressed { background: rgba(30,80,160,0.9); }

QPushButton[sfRole="danger"] {
    background: rgba(160,35,35,0.55);
    border: 1px solid rgba(200,60,60,0.5);
    color: #f5b0b0;
}
QPushButton[sfRole="danger"]:hover { background: rgba(185,40,40,0.75); }

QPushButton[sfRole="success"] {
    background: rgba(30,130,70,0.6);
    border: 1px solid rgba(50,170,90,0.55);
    color: #a8f0c0;
    font-weight: 600;
}
QPushButton[sfRole="success"]:hover { background: rgba(35,150,80,0.8); }

QPushButton[sfRole="secondary"] {
    background: rgba(45,80,130,0.35);
    border: 1px solid rgba(70,110,170,0.45);
    color: #88b8e8;
}
QPushButton[sfRole="secondary"]:hover { background: rgba(50,90,150,0.55); }



QLineEdit {
    background: rgba(0,0,0,0.2);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 3px;
    color: #d4e0ec;
    font-size: 12px;
    min-height: 22px;
    max-height: 26px;
    padding: 1px 6px;
    selection-background-color: rgba(45,108,200,0.6);
}
QLineEdit:read-only { color: rgba(180,195,210,0.7); }

QTextEdit {
    background: rgba(0,0,0,0.2);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 3px;
    color: #c0d0e0;
    font-size: 11px;
}

QCheckBox {
    color: #c8d8e8;
    font-size: 12px;
    spacing: 5px;
}
QCheckBox::indicator {
    width: 13px;
    height: 13px;
    border: 1px solid rgba(255,255,255,0.22);
    border-radius: 2px;
    background: rgba(0,0,0,0.2);
}
QCheckBox::indicator:checked {
    background: rgba(45,108,200,0.85);
    border-color: rgba(80,140,230,0.7);
}

QSlider::groove:horizontal {
    height: 4px;
    background: rgba(255,255,255,0.12);
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 12px;
    height: 12px;
    margin: -4px 0;
    background: rgba(45,108,200,0.85);
    border: 1px solid rgba(80,140,230,0.7);
    border-radius: 6px;
}
QSlider::sub-page:horizontal {
    background: rgba(45,108,200,0.55);
    border-radius: 2px;
}

QTableWidget, QListWidget {
    background: rgba(0,0,0,0.15);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 3px;
    color: #c8d8e8;
    font-size: 12px;
    gridline-color: rgba(255,255,255,0.06);
    alternate-background-color: rgba(255,255,255,0.025);
    selection-background-color: rgba(45,108,200,0.5);
    selection-color: #ffffff;
}
QHeaderView::section {
    background: rgba(255,255,255,0.06);
    border: none;
    border-bottom: 1px solid rgba(255,255,255,0.12);
    color: #8aa4c0;
    padding: 3px 6px;
    font-size: 11px;
    font-weight: 600;
}

QSplitter::handle { background: rgba(255,255,255,0.08); width: 4px; }
QSplitter::handle:hover { background: rgba(45,108,200,0.5); }

QTabWidget::pane {
    border: 1px solid rgba(255,255,255,0.1);
    border-top: none;
}
QTabBar::tab {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-bottom: none;
    border-radius: 3px 3px 0 0;
    color: #8aa0b8;
    font-size: 12px;
    padding: 4px 14px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: rgba(45,108,200,0.3);
    border-color: rgba(45,108,200,0.5);
    color: #d0e4f8;
    font-weight: 600;
}
QTabBar::tab:hover:!selected {
    background: rgba(255,255,255,0.09);
    color: #b0c8e0;
}

QScrollArea { border: none; background: transparent; }
QScrollBar:vertical {
    width: 8px;
    background: rgba(255,255,255,0.04);
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.2);
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: rgba(45,108,200,0.6); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ── VMTK panel overrides ── */
QFrame#vmtkHeader {
    background: rgba(20,40,70,0.6);
    border-bottom: 1px solid rgba(45,108,200,0.4);
}
QLabel#vmtkTitle   { font-size: 14px; font-weight: 700; color: #d0e4f8; }
QLabel#vmtkSubtitle { font-size: 11px; color: #6a90b8; }
QFrame#vmtkCard {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 4px;
}
QLabel#vmtkBadge {
    background: rgba(45,108,200,0.7);
    color: #ffffff;
    font-size: 10px;
    font-weight: 700;
    border-radius: 9px;
    padding: 1px 6px;
}
QLabel#vmtkStepLabel  { font-size: 12px; font-weight: 600; color: #b8cce0; }
QLabel#vmtkFieldLabel { font-size: 11px; color: #7090a8; }
QLabel#vmtkCountLabel { font-size: 11px; color: #6888a0; font-style: italic; }
QListWidget#vmtkList {
    background: rgba(0,0,0,0.18);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 3px;
    color: #b8cce0;
    font-size: 11px;
}
QListWidget#vmtkList::item:selected { background: rgba(45,108,200,0.5); color: #ffffff; }
QTextEdit#vmtkLog {
    background: rgba(0,0,0,0.25);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 3px;
    color: #6888a8;
    font-size: 10px;
    font-family: monospace;
}
"""


def apply_to(widget):
    """Apply the shared STARFiSh stylesheet to a widget."""
    widget.setStyleSheet(STARFISH_STYLESHEET)


def set_role(button, role):
    """
    Set a semantic colour role on a QPushButton and refresh its style.
    role: 'primary' | 'danger' | 'success' | 'secondary'
    """
    button.setProperty("sfRole", role)
    try:
        button.style().unpolish(button)
        button.style().polish(button)
    except Exception:
        pass
