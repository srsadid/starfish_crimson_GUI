"""
STARFiShCrimsonGUI — 3D Slicer Scripted Module

Loads the standalone VascularEditorWidget from the local vnc_ui copy
(with PythonQt patches applied) directly inside the Slicer side panel.

Cross-platform notes (Linux / macOS / Windows):
  - The NetlistEditor C++ binary path is resolved dynamically per-OS.
  - All Qt property accesses use PythonQt-safe helpers (no super() calls).
  - The PySide6 shim maps any stray PySide6 imports to Slicer's qt module.
"""

import os
import sys
import types
import importlib
import importlib.util
import qt
import slicer
from slicer.ScriptedLoadableModule import *

# ─────────────────────────────────────────────────────────────────────────────
# 1. Paths
# ─────────────────────────────────────────────────────────────────────────────
_DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
_LIB_DIR  = os.path.join(_DEMO_DIR, "lib")   # PythonQt-patched copies

# ─────────────────────────────────────────────────────────────────────────────
# 2. Add dependencies and configure path
# ─────────────────────────────────────────────────────────────────────────────
# Insert DEMO_DIR first so Python finds our local vnc_ui/UtilityLib/NetworkLib
for _p in (_DEMO_DIR,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Stub out modules that can't run inside Slicer (standalone launcher)
# ─────────────────────────────────────────────────────────────────────────────
for _stub in ("vnc_ui.slicer_panel",):
    if _stub not in sys.modules:
        sys.modules[_stub] = types.ModuleType(_stub)

# ─────────────────────────────────────────────────────────────────────────────
# 3b. Ensure dependencies for visualization_qt are installed
# ─────────────────────────────────────────────────────────────────────────────
try:
    import h5py
    import matplotlib
except ImportError:
    print("Installing STARFiSh visualization dependencies (h5py, matplotlib)...")
    import slicer
    slicer.util.pip_install("h5py matplotlib")
    import h5py
    import matplotlib

# ─────────────────────────────────────────────────────────────────────────────
# 4. PySide6 → qt shim  (catches any remaining "from PySide6 import …")
# ─────────────────────────────────────────────────────────────────────────────
if "PySide6" not in sys.modules:
    _pyside6 = types.ModuleType("PySide6")
    _pyside6.__version__ = "6.0.0"
    for _sub in ("QtWidgets", "QtCore", "QtGui", "QtSvg"):
        _m = types.ModuleType("PySide6." + _sub)
        _m.__getattr__ = lambda name, _qt=qt: getattr(_qt, name)
        sys.modules["PySide6." + _sub] = _m
        setattr(_pyside6, _sub, _m)
    sys.modules["PySide6"] = _pyside6

if "shiboken6" not in sys.modules:
    _shiboken6 = types.ModuleType("shiboken6")
    _shiboken6.isValid = lambda obj: True
    sys.modules["shiboken6"] = _shiboken6


# ═════════════════════════════════════════════════════════════════════════════
# Module metadata
# ═════════════════════════════════════════════════════════════════════════════
class STARFiShCrimsonGUI(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title        = "Model Builder Demo"
        self.parent.categories   = ["STARFiSh-CRIMSON"]
        self.parent.dependencies = []
        self.parent.contributors = ["Sadman Sadid, University of Michigan <sadid@umich.edu>"]
        self.parent.helpText     = (
            "STARFiSh-CRIMSON vascular network canvas — running natively inside 3D Slicer."
        )
        self.parent.acknowledgementText = ""


# ═════════════════════════════════════════════════════════════════════════════
# Module widget
# ═════════════════════════════════════════════════════════════════════════════
class STARFiShCrimsonGUIWidget(ScriptedLoadableModuleWidget):

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        try:
            self._setupWithRealVncUI()
        except Exception as exc:
            errLabel = qt.QLabel(
                "<b>Import error:</b> {}<br><br>"
                "Check the Python console for details.".format(str(exc))
            )
            errLabel.setWordWrap(True)
            errLabel.setStyleSheet("color:red; padding:10px;")
            self.layout.addWidget(errLabel)
            import traceback
            traceback.print_exc()

    # ──────────────────────────────────────────────────────────────────────
    def _setupWithRealVncUI(self):
        """
        Instantiate the full VascularEditorWidget and embed it in the
        Slicer side-panel.  All logic (canvas, properties, save/load,
        netlist editor launch) lives inside the widget itself.
        """
        from vnc_ui.editor import VascularEditorWidget
        self._editorWidget = VascularEditorWidget(enable_visualization_tab=True)

        # ── Make the widget shrinkable so Slicer's dock doesn't lock its width ──
        self._editorWidget.setSizePolicy(
            qt.QSizePolicy.Ignored, qt.QSizePolicy.Expanding
        )
        self._editorWidget.setMinimumWidth(100)

        # Wire up the "Open Netlist Editor" button to the cross-platform launcher
        try:
            self._editorWidget.prop_panel.btn_open_netlist_editor.clicked.connect(
                self._openNetlistEditor
            )
        except AttributeError:
            pass  # Button may not exist in all panel layouts

        self.layout.addWidget(self._editorWidget)

    # ──────────────────────────────────────────────────────────────────────
    def _openNetlistEditor(self):
        """
        Launch the pre-compiled CRIMSONBCT (NetlistEditor) binary.
        Resolves the correct executable name for each OS.
        """
        import subprocess
        import platform

        # Determine OS-specific binary name and path
        system = platform.system()
        if system == "Windows":
            binary_path = os.path.join(_DEMO_DIR, "bin", "windows", "CRIMSONBCT.exe")
            instructions_file = os.path.join(_DEMO_DIR, "bin", "windows", "BUILD_INSTRUCTIONS.md")
        elif system == "Darwin":
            binary_path = os.path.join(_DEMO_DIR, "bin", "macos", "CRIMSON Boundary Condition Toolbox.app", "Contents", "MacOS", "CRIMSONBCT")
            instructions_file = os.path.join(_DEMO_DIR, "bin", "macos", "BUILD_INSTRUCTIONS.md")
        else:
            binary_path = os.path.join(_DEMO_DIR, "bin", "linux", "CRIMSONBCT")
            instructions_file = os.path.join(_DEMO_DIR, "bin", "linux", "BUILD_INSTRUCTIONS.md")

        binary_path = os.path.normpath(binary_path)
        instructions_file = os.path.normpath(instructions_file)

        if not os.path.exists(binary_path):
            qt.QMessageBox.warning(
                slicer.util.mainWindow(),
                "NetlistEditor Not Found",
                "Could not find the pre-compiled NetlistEditor binary for your OS at:\n{}\n\n"
                "If you want to build it from scratch, please follow the instructions in:\n{}".format(binary_path, instructions_file)
            )
            return

        try:
            subprocess.Popen([binary_path])
        except Exception as exc:
            qt.QMessageBox.critical(
                slicer.util.mainWindow(),
                "NetlistEditor Launch Failed",
                "Failed to launch the NetlistEditor:\n{}".format(str(exc))
            )
