import math
import os
import subprocess
from vnc_ui.qt_compat import QtWidgets, QtCore


def _qprop(obj, name):
    """Safely read a Qt property that PythonQt may expose as a Python
    property (not callable) or as a method (callable).  Returns the value
    in either case, so code like ``_qprop(widget, 'text')`` works under
    both PySide6 and PythonQt."""
    attr = getattr(obj, name)
    return attr() if callable(attr) else attr
from UtilityLib.constants import newestNetworkXml as nxml
from UtilityLib.constants import variablesDict
from NetworkLib.classBoundaryConditions import *
from vnc_ui.widgets import (
    FixedPopupComboBox,
    NoWheelComboBox,
    NoWheelDoubleSpinBox,
    NoWheelSpinBox,
)
from vnc_ui.scene_items import VesselEdge, JunctionNode


# ─────────────────────────────────────────────────────────────────────────────
# PythonQt signal helper classes
# PythonQt does NOT support lambda functions in signal connections.
# These tiny helper objects replace lambdas while keeping the same logic.
# ─────────────────────────────────────────────────────────────────────────────

class _SignalHelper:
    """Calls panel.update_compliance_field(field_name) without a lambda."""
    def __init__(self, panel, field_name):
        self._panel = panel
        self._field_name = field_name

    def update_compliance(self, _val=None):
        self._panel.update_compliance_field(self._field_name)

    def update_compliance_no_arg(self):
        self._panel.update_compliance_field(self._field_name)


class _BrowseFileHelper:
    """Calls panel._browse_file(editor) without a lambda."""
    def __init__(self, panel, editor):
        self._panel = panel
        self._editor = editor

    def browse(self):
        self._panel._browse_file(self._editor)


class _BrowseNetlistHelper:
    """Calls panel._browse_netlist_branch_dat(editor) without a lambda."""
    def __init__(self, panel, editor):
        self._panel = panel
        self._editor = editor

    def browse(self):
        self._panel._browse_netlist_branch_dat(self._editor)


class _SolverParamHelper:
    """Calls solver_group.update_param(key, value) without a lambda."""
    def __init__(self, group, key):
        self._group = group
        self._key = key

    def update(self, value):
        self._group.update_param(self._key, value)


class _FluidFieldHelper:
    """Calls panel.update_fluid_field(field_name) without a lambda."""
    def __init__(self, panel, field_name):
        self._panel = panel
        self._field_name = field_name

    def update(self):
        self._panel.update_fluid_field(self._field_name)



class PropertiesPanel(QtWidgets.QWidget):
    def __init__(self, scene):
        QtWidgets.QWidget.__init__(self)
        self.scene = scene
        self.scene.connect("selectionChanged()", self.on_selection_changed)
        self.current_item = None

        panel_layout = QtWidgets.QVBoxLayout()
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel_layout.setSpacing(10)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setLayout(panel_layout)

        import ctk

        # 1. Vessel Geometry + Topology
        vessel_collapsible = ctk.ctkCollapsibleButton()
        vessel_collapsible.text = "1. Vessel Geometry"
        vessel_layout = QtWidgets.QFormLayout(vessel_collapsible)
        vessel_layout.setContentsMargins(8, 8, 8, 8)
        vessel_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        vessel_layout.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        vessel_layout.setLabelAlignment(QtCore.Qt.AlignLeft)
        vessel_layout.setHorizontalSpacing(10)
        vessel_layout.setVerticalSpacing(8)

        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.name_edit.connect("textChanged(QString)", self.update_name)

        self.type_combo = NoWheelComboBox()
        geometry_types = variablesDict.get('geometryType', {}).get('strCases', [])
        if not geometry_types:
            geometry_types = ['uniform', 'cone']
        self.type_combo.addItems(geometry_types)
        self.type_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.type_combo.connect("currentTextChanged(QString)", self.update_type)

        self.grid_points_edit = NoWheelSpinBox()
        self.grid_points_edit.setRange(2, 10000)
        self.grid_points_edit.connect("valueChanged(int)", self.update_grid_points)

        self.left_daughter_edit = QtWidgets.QLineEdit()
        self.left_daughter_edit.setReadOnly(True)
        self.right_daughter_edit = QtWidgets.QLineEdit()
        self.right_daughter_edit.setReadOnly(True)
        self.angle_y_edit = QtWidgets.QLineEdit()
        self.angle_y_edit.setPlaceholderText("rad")
        self.angle_y_edit.connect("editingFinished()", self.update_angle_y)

        self.length_m_edit = NoWheelDoubleSpinBox()
        self.length_m_edit.setRange(0.0, 10000.0)
        self.length_m_edit.setDecimals(6)
        self.length_m_edit.setSpecialValueText("N/A")
        self.length_m_edit.setSuffix(" m")
        self.length_m_edit.connect("valueChanged(double)", self.update_length_m)

        self.radius_prox_edit = NoWheelDoubleSpinBox()
        self.radius_prox_edit.setRange(0.0, 1000.0)
        self.radius_prox_edit.setDecimals(6)
        self.radius_prox_edit.setSpecialValueText("N/A")
        self.radius_prox_edit.setSuffix(" m")
        self.radius_prox_edit.connect("valueChanged(double)", self.update_radius_prox)

        self.radius_dist_edit = NoWheelDoubleSpinBox()
        self.radius_dist_edit.setRange(0.0, 1000.0)
        self.radius_dist_edit.setDecimals(6)
        self.radius_dist_edit.setSpecialValueText("N/A")
        self.radius_dist_edit.setSuffix(" m")
        self.radius_dist_edit.connect("valueChanged(double)", self.update_radius_dist)

        vessel_layout.addRow("Identifier:", self.name_edit)
        vessel_layout.addRow("Geometry Type:", self.type_combo)
        vessel_layout.addRow("N (Grid Points):", self.grid_points_edit)
        vessel_layout.addRow("Left Daughter:", self.left_daughter_edit)
        vessel_layout.addRow("Right Daughter:", self.right_daughter_edit)
        vessel_layout.addRow("Angle Y Mother:", self.angle_y_edit)
        vessel_layout.addRow("Length:", self.length_m_edit)
        vessel_layout.addRow("Radius Proximal:", self.radius_prox_edit)
        vessel_layout.addRow("Radius Distal:", self.radius_dist_edit)

        panel_layout.addWidget(vessel_collapsible)

        # 2. Vessel Compliance
        compliance_collapsible = ctk.ctkCollapsibleButton()
        compliance_collapsible.text = "2. Vessel Compliance"
        compliance_collapsible.collapsed = True
        compliance_layout = QtWidgets.QVBoxLayout(compliance_collapsible)
        compliance_layout.setContentsMargins(8, 8, 8, 8)

        compliance_header = QtWidgets.QFormLayout()
        compliance_header.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        compliance_header.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        compliance_header.setHorizontalSpacing(10)
        compliance_header.setVerticalSpacing(8)

        self.compliance_type_combo = NoWheelComboBox()
        self.compliance_type_combo.addItems(sorted(list(nxml.vesselComplianceElements.keys())))
        self.compliance_type_combo.connect("currentTextChanged(QString)", self.on_compliance_type_changed)
        compliance_header.addRow("Compliance Type:", self.compliance_type_combo)
        compliance_layout.addLayout(compliance_header)

        self.compliance_form_widget = QtWidgets.QWidget()
        self.compliance_form_layout = QtWidgets.QFormLayout()
        self.compliance_form_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.compliance_form_layout.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        self.compliance_form_layout.setHorizontalSpacing(10)
        self.compliance_form_layout.setVerticalSpacing(8)
        self.compliance_form_widget.setLayout(self.compliance_form_layout)
        compliance_layout.addWidget(self.compliance_form_widget)
        panel_layout.addWidget(compliance_collapsible)

        # 3. Vessel Fluid
        fluid_collapsible = ctk.ctkCollapsibleButton()
        fluid_collapsible.text = "3. Vessel Fluid"
        fluid_collapsible.collapsed = True
        fluid_layout = QtWidgets.QFormLayout(fluid_collapsible)
        fluid_layout.setContentsMargins(8, 8, 8, 8)
        fluid_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        fluid_layout.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        fluid_layout.setHorizontalSpacing(10)
        fluid_layout.setVerticalSpacing(8)

        self.apply_global_fluid_combo = NoWheelComboBox()
        self.apply_global_fluid_combo.addItems(["True", "False"])
        self.apply_global_fluid_combo.connect("currentTextChanged(QString)", self.update_apply_global_fluid)

        self.fluid_my_edit = QtWidgets.QLineEdit()
        self.fluid_my_edit.connect("editingFinished()", _FluidFieldHelper(self, 'my').update)
        self.fluid_rho_edit = QtWidgets.QLineEdit()
        self.fluid_rho_edit.connect("editingFinished()", _FluidFieldHelper(self, 'rho').update)
        self.fluid_gamma_edit = QtWidgets.QLineEdit()
        self.fluid_gamma_edit.connect("editingFinished()", _FluidFieldHelper(self, 'gamma').update)

        fluid_layout.addRow("Apply Global Fluid:", self.apply_global_fluid_combo)
        fluid_layout.addRow("my:", self.fluid_my_edit)
        fluid_layout.addRow("rho:", self.fluid_rho_edit)
        fluid_layout.addRow("gamma:", self.fluid_gamma_edit)
        panel_layout.addWidget(fluid_collapsible)
        
        # 4. Boundary Condition Manager
        self.bc_group = ctk.ctkCollapsibleButton()
        self.bc_group.text = "4. Boundary Condition Manager"
        self.bc_group.collapsed = True
        bc_layout = QtWidgets.QVBoxLayout(self.bc_group)
        bc_layout.setContentsMargins(8, 8, 8, 8)

        header_form = QtWidgets.QFormLayout()
        header_form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        header_form.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        header_form.setHorizontalSpacing(10)
        header_form.setVerticalSpacing(8)

        self.bc_type = FixedPopupComboBox(max_items=5)
        self.bc_type.addItems(self.available_bc_types())
        self.bc_type.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.bc_type.setMaxVisibleItems(5)
        list_view = QtWidgets.QListView()
        list_view.setUniformItemSizes(True)
        list_view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        list_view.setSpacing(2)
        self.bc_type.setView(list_view)
        self.bc_type.connect("activated(int)", self.on_bc_type_changed)

        self.bc_position = NoWheelComboBox()
        self.bc_position.addItems(["Start (0)", "End (-1)"])
        self.bc_position.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        header_form.addRow("BC Type:", self.bc_type)
        header_form.addRow("Position:", self.bc_position)
        bc_layout.addLayout(header_form)

        self.bc_form_widget = QtWidgets.QWidget()
        self.bc_form_layout = QtWidgets.QFormLayout()
        self.bc_form_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.bc_form_layout.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        self.bc_form_layout.setHorizontalSpacing(10)
        self.bc_form_layout.setVerticalSpacing(8)
        self.bc_form_widget.setLayout(self.bc_form_layout)
        bc_layout.addWidget(self.bc_form_widget)

        button_row = QtWidgets.QHBoxLayout()
        button_row.setSpacing(8)
        self.btn_bc_add = QtWidgets.QPushButton("+   Add / Update BC")
        self.btn_bc_delete = QtWidgets.QPushButton("Delete BC")
        self.btn_bc_open_netlist = QtWidgets.QPushButton("⎇   Open Netlist Editor")
        self.btn_bc_add.setObjectName("btn_bc_add")
        self.btn_bc_delete.setObjectName("btn_bc_delete")
        self.btn_bc_open_netlist.setObjectName("btn_bc_open_netlist")
        for button in (self.btn_bc_add, self.btn_bc_delete, self.btn_bc_open_netlist):
            button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            button.setMinimumHeight(42)
        self.btn_bc_add.connect("clicked()", self.add_or_update_boundary_condition)
        self.btn_bc_delete.connect("clicked()", self.delete_boundary_condition)
        self.btn_bc_open_netlist.connect("clicked()", self.open_netlist_editor)
        self.btn_bc_delete.setIcon(self._standard_icon("SP_TrashIcon", "SP_DialogDiscardButton"))
        self.btn_bc_delete.setIconSize(QtCore.QSize(18, 18))
        button_row.addWidget(self.btn_bc_add)
        button_row.addWidget(self.btn_bc_delete)
        bc_layout.addLayout(button_row)
        bc_layout.addWidget(self.btn_bc_open_netlist)

        panel_layout.addWidget(self.bc_group)
        
        # 5. Global Solver Setup
        # Wrap SolverSetupGroup in a ctkCollapsibleButton
        solver_collapsible = ctk.ctkCollapsibleButton()
        solver_collapsible.text = "Global Solver Configuration"
        solver_collapsible.collapsed = True
        solver_collapsible_layout = QtWidgets.QVBoxLayout(solver_collapsible)
        self.solver_setup_group = SolverSetupGroup(self.scene)
        solver_collapsible_layout.addWidget(self.solver_setup_group)
        panel_layout.addWidget(solver_collapsible)
        
        panel_layout.addStretch()
        self.set_enabled_fields(False)
        self.set_boundary_condition_fields_enabled(False)
        # (Save/Load project buttons will be connected by the main editor)
        self.bc_field_edits = {}
        self.bc_metadata_fields = set()
        self.compliance_field_edits = {}
        self._suspend_geometry_sync = False
        self._current_boundary_node = None
        self.on_bc_type_changed(_qprop(self.bc_type, 'currentIndex'))
        self.on_compliance_type_changed(_qprop(self.compliance_type_combo, 'currentText'))
        self._apply_responsive_styles(_qprop(self, 'width'))

    def _standard_icon(self, *names):
        standard_pixmap = getattr(QtWidgets.QStyle, "StandardPixmap", QtWidgets.QStyle)
        for name in names:
            pixmap = getattr(standard_pixmap, name, None)
            if pixmap is not None:
                return self.style().standardIcon(pixmap)
        return self.style().standardIcon(getattr(standard_pixmap, "SP_FileIcon"))

    def set_enabled_fields(self, enabled, is_edge=False):
        self.name_edit.setEnabled(enabled)
        self.type_combo.setEnabled(is_edge)
        self.left_daughter_edit.setEnabled(is_edge)
        self.right_daughter_edit.setEnabled(is_edge)
        self.angle_y_edit.setEnabled(is_edge)
        self.length_m_edit.setEnabled(is_edge)
        self.radius_prox_edit.setEnabled(is_edge)
        self.radius_dist_edit.setEnabled(is_edge)
        self.grid_points_edit.setEnabled(is_edge)
        self.compliance_type_combo.setEnabled(is_edge)
        self.compliance_form_widget.setEnabled(is_edge)
        self.apply_global_fluid_combo.setEnabled(is_edge)
        self.fluid_my_edit.setEnabled(is_edge)
        self.fluid_rho_edit.setEnabled(is_edge)
        self.fluid_gamma_edit.setEnabled(is_edge)

    def set_boundary_condition_fields_enabled(self, enabled):
        self.bc_group.setEnabled(enabled)
        self.bc_type.setEnabled(enabled)
        self.bc_position.setEnabled(enabled)
        self.bc_form_widget.setEnabled(enabled)
        self.btn_bc_add.setEnabled(enabled)
        self.btn_bc_delete.setEnabled(enabled)
        self.btn_bc_open_netlist.setEnabled(enabled)

    def _apply_responsive_styles(self, width):
        # Primary actions
        for btn in [self.btn_bc_add]:
            btn.setProperty("sfRole", "primary")
            
        # Danger actions
        for btn in [self.btn_bc_delete]:
            btn.setProperty("sfRole", "danger")

        # Secondary actions
        for btn in [self.btn_bc_open_netlist]:
            btn.setProperty("sfRole", "secondary")

    def resizeEvent(self, event):
        QtWidgets.QWidget.resizeEvent(self, event)
        self._apply_responsive_styles(_qprop(self, 'width'))

    def on_selection_changed(self):
        selected = self.scene.selectedItems()
        if not selected or len(selected) > 1:
            self.current_item = None
            self.set_enabled_fields(False)
            self.set_boundary_condition_fields_enabled(False)
            self.name_edit.clear()
            self.left_daughter_edit.clear()
            self.right_daughter_edit.clear()
            self.angle_y_edit.clear()
            self.length_m_edit.setValue(0.0)
            self.radius_prox_edit.setValue(0.0)
            self.radius_dist_edit.setValue(0.0)
            self.grid_points_edit.setValue(2)
            self.compliance_type_combo.setCurrentIndex(-1)
            self._build_compliance_editor(None)
            self.apply_global_fluid_combo.setCurrentIndex(0)
            self.fluid_my_edit.clear()
            self.fluid_rho_edit.clear()
            self.fluid_gamma_edit.clear()
            self.refresh_boundary_conditions_view()
            return

        item = selected[0]
        self.current_item = item

        self.blockSignals(True)
        self.name_edit.blockSignals(True)
        self.type_combo.blockSignals(True)
        self.left_daughter_edit.blockSignals(True)
        self.right_daughter_edit.blockSignals(True)
        self.angle_y_edit.blockSignals(True)
        self.length_m_edit.blockSignals(True)
        self.radius_prox_edit.blockSignals(True)
        self.radius_dist_edit.blockSignals(True)
        self.grid_points_edit.blockSignals(True)
        self.compliance_type_combo.blockSignals(True)
        self.apply_global_fluid_combo.blockSignals(True)

        self.name_edit.setText(item.name)

        if isinstance(item, VesselEdge):
            self.set_enabled_fields(True, is_edge=True)
            self.set_boundary_condition_fields_enabled(False)
            self.type_combo.setCurrentText(item.geometry_type if hasattr(item, 'geometry_type') else item.vessel_type)
            self._suspend_geometry_sync = True
            self.length_m_edit.setValue(float(item.length_mm) / 1000.0)
            self.radius_prox_edit.setValue(self._area_mm2_to_radius_m(item.area_start_mm2))
            self.radius_dist_edit.setValue(self._area_mm2_to_radius_m(item.area_end_mm2))
            self.grid_points_edit.setValue(int(getattr(item, 'grid_points', 2)))
            self._suspend_geometry_sync = False
            self.angle_y_edit.setText(str(getattr(item, 'angle_y_mother', 0.0)))
            left_edge, right_edge = self._get_daughter_edges(item)
            self.left_daughter_edit.setText(left_edge.name if left_edge else '')
            self.right_daughter_edit.setText(right_edge.name if right_edge else '')
            comp_type = getattr(item, 'compliance_type', '')
            if comp_type:
                self.compliance_type_combo.setCurrentText(comp_type)
                self._build_compliance_editor(comp_type, item)
            else:
                self._build_compliance_editor(_qprop(self.compliance_type_combo, 'currentText'), item)
            fluid_values = getattr(item, 'fluid_values', {})
            self.apply_global_fluid_combo.setCurrentText("True" if fluid_values.get('applyGlobalFluid', True) else "False")
            self.fluid_my_edit.setText('' if fluid_values.get('my', None) is None else str(fluid_values.get('my')))
            self.fluid_rho_edit.setText('' if fluid_values.get('rho', None) is None else str(fluid_values.get('rho')))
            self.fluid_gamma_edit.setText('' if fluid_values.get('gamma', None) is None else str(fluid_values.get('gamma')))
            self.refresh_boundary_conditions_view()
        elif isinstance(item, JunctionNode):
            self.set_enabled_fields(True, is_edge=False)
            self.set_boundary_condition_fields_enabled(True)
            self.type_combo.setCurrentIndex(-1)
            self.left_daughter_edit.clear()
            self.right_daughter_edit.clear()
            self.angle_y_edit.clear()
            self.length_m_edit.setValue(0.0)
            self.radius_prox_edit.setValue(0.0)
            self.radius_dist_edit.setValue(0.0)
            self.grid_points_edit.setValue(2)
            self.compliance_type_combo.setCurrentIndex(-1)
            self._build_compliance_editor(None)
            self.apply_global_fluid_combo.setCurrentIndex(0)
            self.fluid_my_edit.clear()
            self.fluid_rho_edit.clear()
            self.fluid_gamma_edit.clear()
            self.refresh_boundary_conditions_view()

        self.name_edit.blockSignals(False)
        self.type_combo.blockSignals(False)
        self.left_daughter_edit.blockSignals(False)
        self.right_daughter_edit.blockSignals(False)
        self.angle_y_edit.blockSignals(False)
        self.length_m_edit.blockSignals(False)
        self.radius_prox_edit.blockSignals(False)
        self.radius_dist_edit.blockSignals(False)
        self.grid_points_edit.blockSignals(False)
        self.compliance_type_combo.blockSignals(False)
        self.apply_global_fluid_combo.blockSignals(False)
        self.blockSignals(False)

    def update_name(self, text):
        if self.current_item:
            self.current_item.name = text
            self.current_item.update_visuals()

    def update_type(self, text):
        if isinstance(self.current_item, VesselEdge):
            self.current_item.vessel_type = text
            self.current_item.geometry_type = text

    def _area_mm2_to_radius_m(self, area_mm2):
        try:
            return math.sqrt(max(0.0, float(area_mm2)) * 1e-6 / math.pi)
        except Exception:
            return 0.0

    def _radius_m_to_area_mm2(self, radius_m):
        try:
            return math.pi * (float(radius_m) ** 2) * 1e6
        except Exception:
            return 0.0

    def update_length_m(self, val):
        if self._suspend_geometry_sync:
            return
        if isinstance(self.current_item, VesselEdge):
            self.current_item.length_mm = val * 1000.0
            self.scene.enforce_fixed_lengths()

    def update_radius_prox(self, val):
        if self._suspend_geometry_sync:
            return
        if isinstance(self.current_item, VesselEdge):
            self.current_item.area_start_mm2 = self._radius_m_to_area_mm2(val)
            self.current_item.update_visuals()

    def update_radius_dist(self, val):
        if self._suspend_geometry_sync:
            return
        if isinstance(self.current_item, VesselEdge):
            self.current_item.area_end_mm2 = self._radius_m_to_area_mm2(val)
            self.current_item.update_visuals()

    def update_grid_points(self, val):
        if isinstance(self.current_item, VesselEdge):
            self.current_item.grid_points = int(val)

    def update_angle_y(self):
        if not isinstance(self.current_item, VesselEdge):
            return
        text = _qprop(self.angle_y_edit, 'text').strip()
        if text == '' or text.lower() == 'none':
            self.current_item.angle_y_mother = 0.0
            return
        try:
            self.current_item.angle_y_mother = float(text)
        except ValueError:
            pass

    def update_apply_global_fluid(self, text):
        if not isinstance(self.current_item, VesselEdge):
            return
        self.current_item.fluid_values['applyGlobalFluid'] = text.lower() == 'true'

    def update_fluid_field(self, field_name):
        if not isinstance(self.current_item, VesselEdge):
            return
        widget = {
            'my': self.fluid_my_edit,
            'rho': self.fluid_rho_edit,
            'gamma': self.fluid_gamma_edit,
        }.get(field_name)
        if widget is None:
            return
        text = _qprop(widget, 'text').strip()
        if text == '' or text.lower() == 'none':
            self.current_item.fluid_values[field_name] = None
            return
        try:
            self.current_item.fluid_values[field_name] = float(text)
        except ValueError:
            pass

    def available_bc_types(self):
        return sorted([key for key in nxml.bcTagsClassReferences.keys() if not key.startswith('_')])

    def _get_daughter_edges(self, edge):
        if not isinstance(edge, VesselEdge):
            return None, None
        children = list(edge.dest_node.outgoing_edges) if edge.dest_node else []
        if not children:
            return None, None
        children.sort(key=lambda e: e.dest_node.scenePos().x() if e.dest_node else 0.0)
        left_edge = children[0] if len(children) >= 1 else None
        right_edge = children[1] if len(children) >= 2 else None
        return left_edge, right_edge

    def _clear_layout(self, layout):
        while _qprop(layout, 'count'):
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def _selected_boundary_node(self):
        if isinstance(self.current_item, JunctionNode):
            return self.current_item
        selected = self.scene.selectedItems()
        for item in selected:
            if isinstance(item, JunctionNode):
                return item
        return None

    def _boundary_vessel_id_for_node(self, node):
        if node is None:
            return None
        if node.outgoing_edges:
            return id(node.outgoing_edges[0])
        if node.incoming_edges:
            return id(node.incoming_edges[0])
        return None

    def _ensure_boundary_conditions_list(self, node):
        if not hasattr(node, 'boundary_conditions') or node.boundary_conditions is None:
            node.boundary_conditions = []
        return node.boundary_conditions

    def _parse_bc_value(self, template_value, text_value):
        if text_value is None:
            return None
        text_value = str(text_value).strip()
        if text_value == '' or text_value.lower() == 'none':
            return None
        if isinstance(template_value, bool):
            return text_value.lower() in ('1', 'true', 'yes', 'y', 't')
        if isinstance(template_value, (int, float)):
            try:
                number = float(text_value)
                if isinstance(template_value, int) and number.is_integer():
                    return int(number)
                return number
            except ValueError:
                return None
        return text_value

    def _parse_vessel_value(self, field_name, text_value):
        if text_value is None:
            return None
        text_value = str(text_value).strip()
        if text_value == '' or text_value.lower() == 'none':
            return None
        type_info = variablesDict.get(field_name, {}).get('type', '')
        if 'bool' in type_info:
            return text_value.lower() in ('1', 'true', 'yes', 'y', 't')
        if 'int' in type_info and 'float' not in type_info:
            try:
                return int(float(text_value))
            except ValueError:
                return None
        if 'float' in type_info:
            try:
                return float(text_value)
            except ValueError:
                return None
        return text_value

    def _create_compliance_widget(self, field_name):
        type_info = variablesDict.get(field_name, {}).get('type', '')
        if 'bool' in type_info:
            widget = NoWheelComboBox()
            widget.addItems(["False", "True"])
            return widget
        widget = QtWidgets.QLineEdit()
        widget.setPlaceholderText(field_name)
        return widget

    def _set_compliance_widget_value(self, widget, field_name, value):
        if isinstance(widget, QtWidgets.QComboBox):
            widget.setCurrentText("True" if value else "False")
        else:
            widget.setText('' if value is None else str(value))

    def _get_compliance_widget_value(self, widget, field_name):
        if isinstance(widget, QtWidgets.QComboBox):
            return _qprop(widget, 'currentText').lower() == 'true'
        return self._parse_vessel_value(field_name, _qprop(widget, 'text'))

    def _cache_compliance_values(self):
        if not isinstance(self.current_item, VesselEdge):
            return
        comp_type = self.current_item.compliance_type
        if not comp_type:
            return
        values = {}
        for field_name, widget in self.compliance_field_edits.items():
            values[field_name] = self._get_compliance_widget_value(widget, field_name)
        self.current_item.compliance_values_by_type[comp_type] = values

    def _build_compliance_editor(self, compliance_type, edge=None):
        self._clear_layout(self.compliance_form_layout)
        self.compliance_field_edits = {}
        if not compliance_type:
            return
        field_names = list(nxml.vesselComplianceElements.get(compliance_type, []))
        field_names = [f for f in field_names if f != 'complianceType']
        values = {}
        if isinstance(edge, VesselEdge):
            values = edge.compliance_values_by_type.get(compliance_type, {})
        for field_name in field_names:
            widget = self._create_compliance_widget(field_name)
            self._set_compliance_widget_value(widget, field_name, values.get(field_name, None))
            # Use a helper object to avoid lambda closures (PythonQt incompatible)
            if isinstance(widget, QtWidgets.QComboBox):
                helper = _SignalHelper(self, field_name)
                widget.connect("currentTextChanged(QString)", helper.update_compliance)
            else:
                helper = _SignalHelper(self, field_name)
                widget.connect("editingFinished()", helper.update_compliance_no_arg)
            self.compliance_form_layout.addRow(f"{field_name}:", widget)
            self.compliance_field_edits[field_name] = widget

    def on_compliance_type_changed(self, compliance_type):
        if isinstance(self.current_item, VesselEdge):
            self._cache_compliance_values()
            self.current_item.compliance_type = compliance_type
        self._build_compliance_editor(compliance_type, self.current_item)

    def update_compliance_field(self, field_name):
        if not isinstance(self.current_item, VesselEdge):
            return
        comp_type = self.current_item.compliance_type
        if not comp_type:
            return
        widget = self.compliance_field_edits.get(field_name)
        if widget is None:
            return
        value = self._get_compliance_widget_value(widget, field_name)
        if comp_type not in self.current_item.compliance_values_by_type:
            self.current_item.compliance_values_by_type[comp_type] = {}
        self.current_item.compliance_values_by_type[comp_type][field_name] = value

    def _bc_name_for_position(self, bc_type, position_index):
        return bc_type if position_index == 0 else f'_{bc_type}'

    def _build_bc_editor(self, bc_type, bc_instance=None):
        self._clear_layout(self.bc_form_layout)
        self.bc_field_edits = {}
        self.bc_metadata_fields = set()
        if not bc_type:
            return

        field_names = list(nxml.boundaryConditionElements.get(bc_type, []))
        if bc_type == "Netlist":
            field_names = [
                field_name for field_name in field_names
                if field_name not in ("surfaceId", "flowSign", "Rtilde", "S")
            ]
        for field_name in field_names:
            template_value = getattr(bc_instance, field_name, None) if bc_instance is not None else None
            if template_value is None:
                try:
                    template_value = getattr(eval(nxml.bcTagsClassReferences[bc_type])(), field_name)
                except Exception:
                    template_value = None

            if field_name == 'prescribe':
                editor = QtWidgets.QComboBox()
                editor.addItems(['total', 'influx'])
                if template_value is not None:
                    editor.setCurrentText(str(template_value))
                self.bc_form_layout.addRow(f"{field_name}:", editor)
                self.bc_field_edits[field_name] = editor
            elif field_name == 'filePathName':
                editor = QtWidgets.QLineEdit()
                if template_value is not None:
                    editor.setText(str(template_value))
                editor.setPlaceholderText(str(field_name))
                browse_button = QtWidgets.QPushButton("Browse")
                browse_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
                helper = _BrowseFileHelper(self, editor)
                browse_button.connect("clicked()", helper.browse)
                row = QtWidgets.QHBoxLayout()
                row.setSpacing(6)
                row.addWidget(editor)
                row.addWidget(browse_button)
                self.bc_form_layout.addRow(f"{field_name}:", row)
                self.bc_field_edits[field_name] = editor
            else:
                editor = QtWidgets.QLineEdit()
                if template_value is not None:
                    editor.setText(str(template_value))
                editor.setPlaceholderText(str(field_name))
                self.bc_form_layout.addRow(f"{field_name}:", editor)
                self.bc_field_edits[field_name] = editor

        if bc_type == "Netlist":
            self._add_netlist_metadata_fields(bc_instance)

    def _add_netlist_metadata_fields(self, bc_instance=None):
        """
        Add GUI-only fields needed to build netlist_map.csv.

        These fields are intentionally not part of STARFiSh input.xml. The
        surfaceId and flowSign are assigned automatically during export. The
        DAT file and heart flag describe how the case directory should build
        netlist_surfaces.xml.
        """
        dat_edit = QtWidgets.QLineEdit()
        dat_edit.setPlaceholderText("CRIMSON branch .dat file")
        dat_value = getattr(bc_instance, "branchDat", "") if bc_instance is not None else ""
        dat_edit.setText("" if dat_value is None else str(dat_value))

        browse_button = QtWidgets.QPushButton("Browse")
        browse_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        helper = _BrowseNetlistHelper(self, dat_edit)
        browse_button.connect("clicked()", helper.browse)

        dat_row = QtWidgets.QHBoxLayout()
        dat_row.setSpacing(6)
        dat_row.addWidget(dat_edit)
        dat_row.addWidget(browse_button)
        self.bc_form_layout.addRow("branchDat:", dat_row)
        self.bc_field_edits["branchDat"] = dat_edit
        self.bc_metadata_fields.add("branchDat")

        heart_check = QtWidgets.QCheckBox("Heart model")
        heart_value = getattr(bc_instance, "isHeartModel", False) if bc_instance is not None else False
        heart_check.setChecked(str(heart_value).lower() in ("1", "true", "yes", "y", "t"))
        self.bc_form_layout.addRow("isHeartModel:", heart_check)
        self.bc_field_edits["isHeartModel"] = heart_check
        self.bc_metadata_fields.add("isHeartModel")

    def _browse_netlist_branch_dat(self, target_edit):
        res = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select CRIMSON Netlist DAT",
            "",
            "CRIMSON Netlist DAT (*.dat);;All Files (*)",
        )
        fname = res[0] if isinstance(res, tuple) else res
        if fname:
            target_edit.setText(fname)

    def _browse_file(self, target_edit):
        res = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Data File",
            "",
            "Data Files (*.csv *.txt *.dat);;All Files (*)"
        )
        fname = res[0] if isinstance(res, tuple) else res
        if fname:
            target_edit.setText(fname)

    def _reset_boundary_condition_editor(self):
        self.bc_type.blockSignals(True)
        self.bc_position.blockSignals(True)
        self.bc_type.setCurrentIndex(-1)
        self.bc_position.setCurrentIndex(0)
        self.bc_type.blockSignals(False)
        self.bc_position.blockSignals(False)
        self._clear_layout(self.bc_form_layout)
        self.bc_field_edits = {}
        self.bc_metadata_fields = set()

    def _populate_bc_editor_from_instance(self, bc_instance):
        if bc_instance is None:
            return
        bc_type = bc_instance.getVariableValue('name') or bc_instance.name
        if bc_type.startswith('_'):
            self.bc_position.setCurrentIndex(1)
            bc_type = bc_type[1:]
        else:
            self.bc_position.setCurrentIndex(0)
        if bc_type in self.available_bc_types():
            self.bc_type.blockSignals(True)
            self.bc_type.setCurrentText(bc_type)
            self.bc_type.blockSignals(False)
            self._build_bc_editor(bc_type, bc_instance)
            for field_name, editor in self.bc_field_edits.items():
                value = getattr(bc_instance, field_name, None)
                if isinstance(editor, QtWidgets.QCheckBox):
                    editor.setChecked(str(value).lower() in ('1', 'true', 'yes', 'y', 't'))
                elif isinstance(editor, QtWidgets.QComboBox):
                    editor.setCurrentText(str(value))
                else:
                    editor.setText('' if value is None else str(value))

    def _get_current_bc_instance(self):
        node = self._selected_boundary_node()
        if node is None:
            return None
        conditions = self._ensure_boundary_conditions_list(node)
        for bc in conditions:
            name = bc.getVariableValue('name') if hasattr(bc, 'getVariableValue') else getattr(bc, 'name', None)
            if name == self._bc_name_for_position(_qprop(self.bc_type, 'currentText'), _qprop(self.bc_position, 'currentIndex')):
                return bc
        return None

    def refresh_boundary_conditions_view(self):
        node = self._selected_boundary_node()
        self._current_boundary_node = node
        if node is None:
            self._reset_boundary_condition_editor()
            return

        conditions = self._ensure_boundary_conditions_list(node)
        bc_instance = self._get_current_bc_instance()
        if bc_instance is not None:
            self._populate_bc_editor_from_instance(bc_instance)
            return

        node_bc = getattr(node, 'boundary_condition', None)
        if node_bc is not None and hasattr(node_bc, 'getVariableValue'):
            self._populate_bc_editor_from_instance(node_bc)
            return

        if conditions:
            self._populate_bc_editor_from_instance(conditions[0])
            return

        self._reset_boundary_condition_editor()

    def on_bc_type_changed(self, index):
        txt = self.bc_type.itemText(index)
        if txt:
            self._build_bc_editor(txt)
        self.bc_type.hidePopup()

    def _build_boundary_condition_instance(self):
        bc_type = _qprop(self.bc_type, 'currentText')
        if bc_type not in nxml.bcTagsClassReferences:
            return None

        cls_name = nxml.bcTagsClassReferences[bc_type]
        bc_instance = eval(cls_name)()
        position_index = _qprop(self.bc_position, 'currentIndex')
        bc_name = self._bc_name_for_position(bc_type, position_index)
        bc_instance.update({'name': bc_name})
        if hasattr(bc_instance, 'setPosition'):
            bc_instance.setPosition(0 if position_index == 0 else -1)

        for field_name, editor in self.bc_field_edits.items():
            if isinstance(editor, QtWidgets.QCheckBox):
                parsed_value = _qprop(editor, 'isChecked')
            elif isinstance(editor, QtWidgets.QComboBox):
                template_value = getattr(bc_instance, field_name, None)
                parsed_value = self._parse_bc_value(template_value, _qprop(editor, 'currentText'))
            else:
                template_value = getattr(bc_instance, field_name, None)
                parsed_value = self._parse_bc_value(template_value, _qprop(editor, 'text'))

            if field_name in self.bc_metadata_fields:
                setattr(bc_instance, field_name, parsed_value)
            else:
                bc_instance.update({field_name: parsed_value})

        return bc_instance

    def add_or_update_boundary_condition(self):
        node = self._selected_boundary_node()
        if node is None:
            QtWidgets.QMessageBox.warning(self, 'No node selected', 'Select a boundary node first.')
            return

        bc_instance = self._build_boundary_condition_instance()
        if bc_instance is None:
            QtWidgets.QMessageBox.warning(self, 'Invalid BC type', 'Choose a valid boundary condition type.')
            return

        conditions = self._ensure_boundary_conditions_list(node)
        for index, existing in enumerate(conditions):
            existing_name = existing.getVariableValue('name') if hasattr(existing, 'getVariableValue') else getattr(existing, 'name', None)
            if existing_name == bc_instance.getVariableValue('name'):
                conditions[index] = bc_instance
                break
        else:
            conditions.append(bc_instance)
        node.boundary_condition = bc_instance
        self.refresh_boundary_conditions_view()

    def delete_boundary_condition(self):
        node = self._selected_boundary_node()
        if node is None:
            return
        conditions = self._ensure_boundary_conditions_list(node)
        target_name = self._bc_name_for_position(_qprop(self.bc_type, 'currentText'), _qprop(self.bc_position, 'currentIndex'))
        for index, existing in enumerate(list(conditions)):
            existing_name = existing.getVariableValue('name') if hasattr(existing, 'getVariableValue') else getattr(existing, 'name', None)
            if existing_name == target_name:
                del conditions[index]
                break
        if conditions:
            node.boundary_condition = conditions[0]
        elif hasattr(node, 'boundary_condition'):
            node.boundary_condition = None
        self.refresh_boundary_conditions_view()

    def show_boundary_conditions(self):
        node = self._selected_boundary_node()
        if node is None:
            QtWidgets.QMessageBox.information(self, 'Boundary conditions', 'No boundary node selected.')
            return
        conditions = self._ensure_boundary_conditions_list(node)
        if not conditions:
            QtWidgets.QMessageBox.information(self, 'Boundary conditions', 'No boundary conditions defined.')
            return
        lines = []
        for bc in conditions:
            name = bc.getVariableValue('name') if hasattr(bc, 'getVariableValue') else getattr(bc, 'name', 'BC')
            lines.append(name)
            for field_name in nxml.boundaryConditionElements.get(name, nxml.boundaryConditionElements.get(name.lstrip('_'), [])):
                if hasattr(bc, 'getVariableValue'):
                    lines.append(f'  {field_name}: {bc.getVariableValue(field_name)}')
                else:
                    lines.append(f'  {field_name}: {getattr(bc, field_name, None)}')
            if str(name).lstrip('_') == 'Netlist':
                lines.append(f'  branchDat: {getattr(bc, "branchDat", "")}')
                lines.append(f'  isHeartModel: {getattr(bc, "isHeartModel", False)}')
        QtWidgets.QMessageBox.information(self, 'Boundary conditions', '\n'.join(lines))

    def open_netlist_editor(self):
        import platform
        import subprocess
        import os

        system = platform.system()
        extension_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

        if system == "Windows":
            binary_path = os.path.join(extension_root, "bin", "windows", "CRIMSONBCT.exe")
            instructions_file = os.path.join(extension_root, "bin", "windows", "BUILD_INSTRUCTIONS.md")
        elif system == "Darwin":
            binary_path = os.path.join(extension_root, "bin", "macos", "CRIMSON Boundary Condition Toolbox.app", "Contents", "MacOS", "CRIMSONBCT")
            instructions_file = os.path.join(extension_root, "bin", "macos", "BUILD_INSTRUCTIONS.md")
        else:
            binary_path = os.path.join(extension_root, "bin", "linux", "CRIMSONBCT")
            instructions_file = os.path.join(extension_root, "bin", "linux", "BUILD_INSTRUCTIONS.md")

        binary_path = os.path.normpath(binary_path)
        instructions_file = os.path.normpath(instructions_file)

        if not os.path.exists(binary_path):
            QtWidgets.QMessageBox.warning(
                self,
                "NetlistEditor Not Found",
                "Could not find the pre-compiled NetlistEditor binary for your OS at:\n{}\n\n"
                "If you want to build it from scratch, please follow the instructions in:\n{}".format(binary_path, instructions_file)
            )
            return

        try:
            env = os.environ.copy()
            # Suppress WSL GUI warnings and force software rendering if on WSL
            is_wsl = False
            try:
                with open('/proc/version', 'r') as f:
                    if 'microsoft' in f.read().lower():
                        is_wsl = True
            except Exception:
                pass

            if is_wsl:
                env["XDG_RUNTIME_DIR"] = "/run/user/{}".format(os.getuid())
                env["LIBGL_ALWAYS_SOFTWARE"] = "1"
                env["GALLIUM_DRIVER"] = "llvmpipe"
                env["QT_QPA_PLATFORM"] = "xcb"

            subprocess.Popen([binary_path], env=env)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, 'Failed to Launch', str(exc))

    def save_project(self):
        # wrapper to save project XML using the full network exporter
        self.export_network_xml()

    def load_project(self):
        res = QtWidgets.QFileDialog.getOpenFileName(self, "Open Project XML", "", "XML Files (*.xml)")
        fname = res[0] if isinstance(res, tuple) else res
        if not fname:
            return
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(fname)
            root = tree.getroot()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to parse XML: {e}')
            return

        # Build map of scene vessels by normalized name
        scene_vessels = [it for it in self.scene.items() if isinstance(it, VesselEdge)]
        scene_vessel_map = {v.name.replace(' ', ''): v for v in scene_vessels}

        # Load vessels (if present)
        vessels_el = root.find('vessels')
        if vessels_el is not None:
            for ve in vessels_el.findall('vessel'):
                name = ve.get('name')
                if not name:
                    continue
                v = scene_vessel_map.get(name)
                if v is None:
                    # no matching vessel in scene; skip
                    continue
                geom = ve.find('geometry')
                if geom is not None:
                    length_el = geom.find('length')
                    rprox = geom.find('radiusProximal')
                    rdist = geom.find('radiusDistal')
                    n_el = geom.find('N')
                    try:
                        if length_el is not None:
                            # length in meters -> convert to mm
                            v.length_mm = float(length_el.text) * 1000.0
                        if rprox is not None and rdist is not None:
                            r0 = float(rprox.text)
                            r1 = float(rdist.text)
                            # areas in m^2 -> convert to mm^2
                            v.area_start_mm2 = math.pi * (r0 ** 2) * 1e6
                            v.area_end_mm2 = math.pi * (r1 ** 2) * 1e6
                    except Exception:
                        pass

        # Load boundary conditions
        bcs_el = root.find('boundaryConditions')
        if bcs_el is not None:
            for bc in bcs_el.findall('boundaryCondition'):
                vid = bc.get('vesselId')
                # find vessel element with matching Id to get its name
                vessel_name = None
                if vessels_el is not None:
                    for ve in vessels_el.findall('vessel'):
                        if ve.get('Id') == vid:
                            vessel_name = ve.get('name')
                            break
                if not vessel_name:
                    continue
                v = scene_vessel_map.get(vessel_name)
                if not v:
                    continue
                # attach BC to the node that is the source of this vessel (consistent with save logic)
                node = v.source_node
                # determine BC type from children
                if node is None:
                    continue
                # prefer Flow-Sinus2 or ReflectionCoefficient
                if bc.find('Flow-Sinus2') is not None:
                    el = bc.find('Flow-Sinus2')
                    amp = 0.0
                    freq = 0.0
                    ael = el.find('amp')
                    fel = el.find('freq')
                    try:
                        if ael is not None: amp = float(ael.text)
                        if fel is not None: freq = float(fel.text)
                    except Exception:
                        pass
                    node.boundary_condition = {'type': 'Flow-Sinus2', 'amp': amp, 'freq': freq}
                elif bc.find('ReflectionCoefficient') is not None:
                    el = bc.find('ReflectionCoefficient')
                    rt = 0.0
                    rel = el.find('Rt')
                    try:
                        if rel is not None: rt = float(rel.text)
                    except Exception:
                        pass
                    node.boundary_condition = {'type': 'ReflectionCoefficient', 'Rt': rt}

        # Refresh visuals
        for sv in scene_vessels:
            sv.update_visuals()
        QtWidgets.QMessageBox.information(self, 'Loaded', f'Loaded project from {fname}')

class SolverSetupGroup(QtWidgets.QGroupBox):
    def __init__(self, scene, parent=None):
        QtWidgets.QGroupBox.__init__(self, "Setup Solver", parent)
        self.scene = scene
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(8)
        
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)
        
        # 1. Simulation Context
        sim_tab = QtWidgets.QWidget()
        sim_layout = QtWidgets.QFormLayout(sim_tab)
        self.totalTime = NoWheelDoubleSpinBox()
        self.totalTime.setRange(0.001, 1000.0)
        self.totalTime.setDecimals(3)
        self.totalTime.setValue(self.scene.global_solver_params['totalTime'])
        
        self.CFL = NoWheelDoubleSpinBox()
        self.CFL.setRange(0.01, 1.0)
        self.CFL.setSingleStep(0.1)
        self.CFL.setValue(self.scene.global_solver_params['CFL'])
        
        self.timeSaveBegin = NoWheelDoubleSpinBox()
        self.timeSaveBegin.setRange(0.0, 1000.0)
        self.timeSaveBegin.setValue(self.scene.global_solver_params['timeSaveBegin'])
        
        self.minSaveDt = NoWheelDoubleSpinBox()
        self.minSaveDt.setRange(-1.0, 1000.0)
        self.minSaveDt.setValue(self.scene.global_solver_params['minSaveDt'])
        
        self.maxMemory = NoWheelDoubleSpinBox()
        self.maxMemory.setRange(1.0, 100000.0)
        self.maxMemory.setValue(self.scene.global_solver_params['maxMemory'])
        
        self.gravitationalField = QtWidgets.QCheckBox()
        self.gravitationalField.setChecked(self.scene.global_solver_params['gravitationalField'])
        
        self.gravityConstant = NoWheelDoubleSpinBox()
        self.gravityConstant.setRange(-100.0, 100.0)
        self.gravityConstant.setValue(self.scene.global_solver_params['gravityConstant'])
        
        sim_layout.addRow("Total Time (s):", self.totalTime)
        sim_layout.addRow("CFL:", self.CFL)
        sim_layout.addRow("Time Save Begin (s):", self.timeSaveBegin)
        sim_layout.addRow("Min Save Dt (s):", self.minSaveDt)
        sim_layout.addRow("Max Memory (MB):", self.maxMemory)
        sim_layout.addRow("Gravitational Field:", self.gravitationalField)
        sim_layout.addRow("Gravity Constant (m s-2):", self.gravityConstant)
        
        self.tabs.addTab(sim_tab, "Context")
        
        # 2. Solver Calibration
        solv_tab = QtWidgets.QWidget()
        solv_layout = QtWidgets.QFormLayout(solv_tab)
        
        self.solvingSchemeField = NoWheelComboBox()
        self.solvingSchemeField.addItems(["MacCormack_Flux", "MacCormack", "Upwind"])
        self.solvingSchemeField.setCurrentText(self.scene.global_solver_params['solvingSchemeField'])
        
        self.rigidAreas = QtWidgets.QCheckBox()
        self.rigidAreas.setChecked(self.scene.global_solver_params['rigidAreas'])
        
        self.simplifyEigenvalues = QtWidgets.QCheckBox()
        self.simplifyEigenvalues.setChecked(self.scene.global_solver_params['simplifyEigenvalues'])
        
        self.riemannInvariantUnitBase = NoWheelComboBox()
        self.riemannInvariantUnitBase.addItems(["Pressure", "Velocity", "Flow"])
        self.riemannInvariantUnitBase.setCurrentText(self.scene.global_solver_params['riemannInvariantUnitBase'])
        
        self.automaticGridAdaptation = QtWidgets.QCheckBox()
        self.automaticGridAdaptation.setChecked(self.scene.global_solver_params['automaticGridAdaptation'])
        
        solv_layout.addRow("Solving Scheme:", self.solvingSchemeField)
        solv_layout.addRow("Rigid Areas:", self.rigidAreas)
        solv_layout.addRow("Simplify Eigenvalues:", self.simplifyEigenvalues)
        solv_layout.addRow("Riemann Invariant Unit:", self.riemannInvariantUnitBase)
        solv_layout.addRow("Auto Grid Adaptation:", self.automaticGridAdaptation)
        
        self.tabs.addTab(solv_tab, "Calibration")
        
        # 3. Initialization
        init_tab = QtWidgets.QWidget()
        init_layout = QtWidgets.QFormLayout(init_tab)
        
        self.initialsationMethod = NoWheelComboBox()
        self.initialsationMethod.addItems(["ConstantPressure", "Auto", "MeanFlow", "MeanPressure", "AutoLinearSystem"])
        self.initialsationMethod.setCurrentText(self.scene.global_solver_params['initialsationMethod'])
        
        self.initMeanFlow = NoWheelDoubleSpinBox()
        self.initMeanFlow.setRange(0.0, 100.0)
        self.initMeanFlow.setValue(self.scene.global_solver_params['initMeanFlow'])
        
        self.initMeanPressure = NoWheelDoubleSpinBox()
        self.initMeanPressure.setRange(0.0, 100000.0)
        self.initMeanPressure.setValue(self.scene.global_solver_params['initMeanPressure'])
        
        self.estimateWindkesselCompliance = NoWheelComboBox()
        self.estimateWindkesselCompliance.addItems(["No", "Yes"])
        self.estimateWindkesselCompliance.setCurrentText(self.scene.global_solver_params['estimateWindkesselCompliance'])
        
        self.compPercentageWK3 = NoWheelDoubleSpinBox()
        self.compPercentageWK3.setRange(0.0, 1.0)
        self.compPercentageWK3.setSingleStep(0.1)
        self.compPercentageWK3.setValue(self.scene.global_solver_params['compPercentageWK3'])
        
        self.compPercentageTree = NoWheelDoubleSpinBox()
        self.compPercentageTree.setRange(0.0, 1.0)
        self.compPercentageTree.setSingleStep(0.1)
        self.compPercentageTree.setValue(self.scene.global_solver_params['compPercentageTree'])
        
        self.compTotalSys = NoWheelDoubleSpinBox()
        self.compTotalSys.setRange(0.0, 1.0)
        self.compTotalSys.setDecimals(12)
        self.compTotalSys.setValue(self.scene.global_solver_params['compTotalSys'])
        
        init_layout.addRow("Method:", self.initialsationMethod)
        init_layout.addRow("Mean Flow:", self.initMeanFlow)
        init_layout.addRow("Mean Pressure:", self.initMeanPressure)
        init_layout.addRow("Est. WK Compliance:", self.estimateWindkesselCompliance)
        init_layout.addRow("Comp % WK3:", self.compPercentageWK3)
        init_layout.addRow("Comp % Tree:", self.compPercentageTree)
        init_layout.addRow("Comp Total Sys:", self.compTotalSys)
        
        self.tabs.addTab(init_tab, "Initialization")
        
        # 4. Global Fluid
        fluid_tab = QtWidgets.QWidget()
        fluid_layout = QtWidgets.QFormLayout(fluid_tab)
        
        self.my = NoWheelDoubleSpinBox()
        self.my.setRange(0.0001, 1.0)
        self.my.setDecimals(6)
        self.my.setValue(self.scene.global_solver_params['my'])
        
        self.rho = NoWheelDoubleSpinBox()
        self.rho.setRange(1.0, 10000.0)
        self.rho.setValue(self.scene.global_solver_params['rho'])
        
        self.gamma = NoWheelDoubleSpinBox()
        self.gamma.setRange(1.0, 10.0)
        self.gamma.setValue(self.scene.global_solver_params['gamma'])
        
        fluid_layout.addRow("Viscosity (my):", self.my)
        fluid_layout.addRow("Density (rho):", self.rho)
        fluid_layout.addRow("Profile (gamma):", self.gamma)
        
        self.tabs.addTab(fluid_tab, "Fluid")
        
        # Connect signals — PythonQt requires no lambdas; use helper objects
        def _wire(widget, signal, key):
            helper = _SolverParamHelper(self, key)
            widget.connect(signal, helper.update)
        _wire(self.totalTime,           "valueChanged(double)",       "totalTime")
        _wire(self.CFL,                 "valueChanged(double)",       "CFL")
        _wire(self.timeSaveBegin,       "valueChanged(double)",       "timeSaveBegin")
        _wire(self.minSaveDt,           "valueChanged(double)",       "minSaveDt")
        _wire(self.maxMemory,           "valueChanged(double)",       "maxMemory")
        _wire(self.gravitationalField,  "toggled(bool)",              "gravitationalField")
        _wire(self.gravityConstant,     "valueChanged(double)",       "gravityConstant")
        _wire(self.solvingSchemeField,  "currentTextChanged(QString)", "solvingSchemeField")
        _wire(self.rigidAreas,          "toggled(bool)",              "rigidAreas")
        _wire(self.simplifyEigenvalues, "toggled(bool)",              "simplifyEigenvalues")
        _wire(self.riemannInvariantUnitBase, "currentTextChanged(QString)", "riemannInvariantUnitBase")
        _wire(self.automaticGridAdaptation, "toggled(bool)",          "automaticGridAdaptation")
        _wire(self.initialsationMethod, "currentTextChanged(QString)", "initialsationMethod")
        _wire(self.initMeanFlow,        "valueChanged(double)",       "initMeanFlow")
        _wire(self.initMeanPressure,    "valueChanged(double)",       "initMeanPressure")
        _wire(self.estimateWindkesselCompliance, "currentTextChanged(QString)", "estimateWindkesselCompliance")
        _wire(self.compPercentageWK3,   "valueChanged(double)",       "compPercentageWK3")
        _wire(self.compPercentageTree,  "valueChanged(double)",       "compPercentageTree")
        _wire(self.compTotalSys,        "valueChanged(double)",       "compTotalSys")
        _wire(self.my,                  "valueChanged(double)",       "my")
        _wire(self.rho,                 "valueChanged(double)",       "rho")
        _wire(self.gamma,               "valueChanged(double)",       "gamma")

    def update_param(self, key, value):
        self.scene.global_solver_params[key] = value
