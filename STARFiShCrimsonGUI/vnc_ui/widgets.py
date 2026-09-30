"""
widgets.py — PythonQt-compatible drop-in replacement for vnc_ui/widgets.py

The only change from the original is in FixedPopupComboBox.eventFilter():
    PySide6:  return super().eventFilter(obj, event)
    PythonQt: return qt.QObject.eventFilter(self, obj, event)

PythonQt does not expose virtual C++ base methods through super() in
multiple-inheritance chains, so we call them explicitly on the C++ class.
"""

import qt  # Slicer's PythonQt binding

# Make QtWidgets / QtCore point to qt so the rest of the file
# is identical in shape to the original widgets.py
QtWidgets = qt
QtCore    = qt


# ── Wheel-suppression mixin ──────────────────────────────────────────
class NoWheelMixin:
    def wheelEvent(self, event):
        event.ignore()


class NoWheelComboBox(NoWheelMixin, qt.QComboBox):
    pass


class NoWheelSpinBox(NoWheelMixin, qt.QSpinBox):
    pass


class NoWheelDoubleSpinBox(NoWheelMixin, qt.QDoubleSpinBox):
    pass


# ── Fixed-height popup combo ─────────────────────────────────────────
# PythonQt cannot call super().showPopup() across multiple-inheritance chains,
# so we drop the custom popup sizing and use a plain scrollable dropdown instead.
class FixedPopupComboBox(NoWheelComboBox):
    """Plain scrollable dropdown — PythonQt-safe replacement for the
    fixed-height popup variant that crashed in Slicer's PythonQt binding."""
    def __init__(self, max_items=5, parent=None):
        qt.QComboBox.__init__(self, parent)
        self._max_popup_items = max_items   # kept for API compatibility

    def set_popup_max_items(self, max_items):
        self._max_popup_items = max_items
