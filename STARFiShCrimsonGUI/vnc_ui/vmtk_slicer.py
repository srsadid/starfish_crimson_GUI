import qt
import slicer
from pathlib import Path

from vnc_ui.qt_compat import QtCore, QtWidgets

class STARFiShCenterlinePanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.setObjectName("STARFiShCenterlinePanel")
        
        self.export_callback = None
        self.surfaceNode = None
        self.endpointsNode = None
        self.branchNodes = []
        self.branchReportRows = []
        
        # Get the ExtractCenterline widget without switching Slicer's active module.
        # widgetRepresentation() instantiates the widget on demand without needing selectModule().
        # We then immediately restore the active module to STARFiShCrimsonGUI.
        self.vmtk_widget = slicer.modules.extractcenterline.widgetRepresentation()
        try:
            slicer.util.selectModule("STARFiShCrimsonGUI")
        except Exception:
            pass
        
        self._build_ui()
        self._apply_style()
        self._setup_vmtk_outputs()

    def hideEvent(self, event):
        self._set_view_interaction_mode()
        QtWidgets.QWidget.hideEvent(self, event)

    def _build_ui(self):
        root = qt.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────
        header = qt.QFrame()
        header.setObjectName("vmtkHeader")
        headerLayout = qt.QVBoxLayout(header)
        headerLayout.setContentsMargins(20, 16, 20, 14)
        headerLayout.setSpacing(4)
        title = qt.QLabel("Centerline Extraction")
        title.setObjectName("vmtkTitle")
        subtitle = qt.QLabel("Step-by-step workflow to extract vessel centerlines using VMTK")
        subtitle.setObjectName("vmtkSubtitle")
        subtitle.setWordWrap(True)
        headerLayout.addWidget(title)
        headerLayout.addWidget(subtitle)
        root.addWidget(header)

        # ── Scroll area for steps ───────────────────────────────────────
        scroll = qt.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(qt.QFrame.NoFrame)
        scroll.setObjectName("vmtkScroll")
        body = qt.QWidget()
        body.setObjectName("vmtkBody")
        bodyLayout = qt.QVBoxLayout(body)
        bodyLayout.setContentsMargins(16, 14, 16, 14)
        bodyLayout.setSpacing(12)
        scroll.setWidget(body)
        root.addWidget(scroll)

        # ── Step helper ─────────────────────────────────────────────────
        def make_step_card(number, label, icon=""):
            card = qt.QFrame()
            card.setObjectName("vmtkCard")
            cardLayout = qt.QVBoxLayout(card)
            cardLayout.setContentsMargins(14, 10, 14, 12)
            cardLayout.setSpacing(8)
            # Step header row
            stepRow = qt.QHBoxLayout()
            badge = qt.QLabel(f" {number} ")
            badge.setObjectName("vmtkBadge")
            stepLabel = qt.QLabel(f"{icon}  {label}" if icon else label)
            stepLabel.setObjectName("vmtkStepLabel")
            stepRow.addWidget(badge)
            stepRow.addWidget(stepLabel)
            stepRow.addStretch()
            cardLayout.addLayout(stepRow)
            return card, cardLayout

        # ── STEP 1: Geometry ─────────────────────────────────────────────
        card1, c1l = make_step_card("1", "Load Geometry", "⬡")
        form1 = qt.QFormLayout()
        form1.setSpacing(7)
        form1.setContentsMargins(0, 4, 0, 0)

        self.sceneModelSelector = slicer.qMRMLNodeComboBox()
        self.sceneModelSelector.nodeTypes = ["vtkMRMLModelNode"]
        self.sceneModelSelector.selectNodeUponCreation = False
        self.sceneModelSelector.addEnabled = False
        self.sceneModelSelector.removeEnabled = False
        self.sceneModelSelector.noneEnabled = True
        self.sceneModelSelector.showHidden = False
        self.sceneModelSelector.setMRMLScene(slicer.mrmlScene)
        self.sceneModelSelector.setToolTip("Pick a model already loaded in the scene")
        self.sceneModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self._on_scene_model_selected)

        lbl_scene = qt.QLabel("From scene:")
        lbl_scene.setObjectName("vmtkFieldLabel")
        form1.addRow(lbl_scene, self.sceneModelSelector)

        geomRow = qt.QHBoxLayout()
        geomRow.setSpacing(6)
        self.txtGeom = qt.QLineEdit()
        self.txtGeom.setReadOnly(True)
        self.txtGeom.setObjectName("vmtkFileInput")
        self.txtGeom.setPlaceholderText("Or load from file (.vtp / .stl / .obj)")
        btnBrowse = qt.QPushButton("Browse…")
        btnBrowse.setObjectName("vmtkSecondaryBtn")
        btnBrowse.setFixedWidth(84)
        btnBrowse.clicked.connect(self.browse_geom)
        geomRow.addWidget(self.txtGeom)
        geomRow.addWidget(btnBrowse)
        lbl_file = qt.QLabel("From file:")
        lbl_file.setObjectName("vmtkFieldLabel")
        form1.addRow(lbl_file, geomRow)
        c1l.addLayout(form1)
        bodyLayout.addWidget(card1)

        # ── STEP 2: Endpoints ────────────────────────────────────────────
        card2, c2l = make_step_card("2", "Define Endpoints", "◉")

        epBtnRow = qt.QHBoxLayout()
        epBtnRow.setSpacing(6)
        self.btnAutoDetect = qt.QPushButton("Auto-detect")
        self.btnAutoDetect.setObjectName("vmtkActionBtn")
        self.btnAutoDetect.clicked.connect(self.auto_detect)
        self.btnPlace = qt.QPushButton("Place")
        self.btnPlace.setObjectName("vmtkActionBtn")
        self.btnPlace.clicked.connect(self.place_endpoints)
        self.btnStop = qt.QPushButton("Select / Move")
        self.btnStop.setObjectName("vmtkActionBtn")
        self.btnStop.clicked.connect(self.stop_placing)
        self.btnClear = qt.QPushButton("Clear All")
        self.btnClear.setObjectName("vmtkDangerBtn")
        self.btnClear.clicked.connect(self.clear_endpoints)
        epBtnRow.addWidget(self.btnAutoDetect)
        epBtnRow.addWidget(self.btnPlace)
        epBtnRow.addWidget(self.btnStop)
        epBtnRow.addWidget(self.btnClear)
        c2l.addLayout(epBtnRow)

        self.lblEpCount = qt.QLabel("No endpoints placed")
        self.lblEpCount.setObjectName("vmtkCountLabel")
        c2l.addWidget(self.lblEpCount)

        self.epList = qt.QListWidget()
        self.epList.setObjectName("vmtkList")
        self.epList.setFixedHeight(90)
        self.epList.currentRowChanged.connect(self.select_endpoint_from_list)
        c2l.addWidget(self.epList)

        self.btnDeleteEp = qt.QPushButton("Remove Selected Endpoint")
        self.btnDeleteEp.setObjectName("vmtkDangerBtn")
        self.btnDeleteEp.clicked.connect(self.delete_selected_endpoint)
        c2l.addWidget(self.btnDeleteEp)
        bodyLayout.addWidget(card2)

        # ── STEP 3: Extract ──────────────────────────────────────────────
        self.btnGenerate = qt.QPushButton("▶   Extract Centerline")
        self.btnGenerate.setObjectName("vmtkPrimaryBtn")
        self.btnGenerate.clicked.connect(self.generate_curve)
        bodyLayout.addWidget(self.btnGenerate)

        # ── STEP 4: Results ──────────────────────────────────────────────
        card4, c4l = make_step_card("4", "Branch Results", "⬡")

        self.branchTable = qt.QTableWidget()
        self.branchTable.setObjectName("vmtkTable")
        self.branchTable.setColumnCount(6)
        self.branchTable.setHorizontalHeaderLabels(["", "Branch", "Length", "Radius", "Area", "Groups"])
        self.branchTable.verticalHeader().setVisible(False)
        self.branchTable.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self.branchTable.setSelectionMode(qt.QAbstractItemView.SingleSelection)
        self.branchTable.setEditTriggers(qt.QAbstractItemView.NoEditTriggers)
        self.branchTable.setAlternatingRowColors(True)
        self.branchTable.setMinimumHeight(150)
        self.branchTable.horizontalHeader().setStretchLastSection(True)
        self.branchTable.setColumnWidth(0, 28)
        self.branchTable.setColumnWidth(1, 100)
        self.branchTable.setColumnWidth(2, 80)
        self.branchTable.setColumnWidth(3, 80)
        self.branchTable.itemSelectionChanged.connect(self.select_branch_from_table)
        c4l.addWidget(self.branchTable)

        self.txtResults = qt.QTextEdit()
        self.txtResults.setObjectName("vmtkLog")
        self.txtResults.setReadOnly(True)
        self.txtResults.setFixedHeight(64)
        c4l.addWidget(self.txtResults)

        resultBtnRow = qt.QHBoxLayout()
        resultBtnRow.setSpacing(8)
        self.btnSaveReport = qt.QPushButton("💾  Save Report (JSON)")
        self.btnSaveReport.setObjectName("vmtkSecondaryBtn")
        self.btnSaveReport.clicked.connect(self.save_branch_report)
        self.btnExportToCanvas = qt.QPushButton("→  Export to Model Builder")
        self.btnExportToCanvas.setObjectName("vmtkSuccessBtn")
        self.btnExportToCanvas.clicked.connect(self.export_to_canvas)
        resultBtnRow.addWidget(self.btnSaveReport)
        resultBtnRow.addWidget(self.btnExportToCanvas)
        c4l.addLayout(resultBtnRow)

        bodyLayout.addWidget(card4)
        bodyLayout.addStretch()


    def _apply_style(self):
        """
        The shared STARFiSh stylesheet (applied by VascularEditorWidget) handles
        all visual styling. This method only assigns semantic sfRole properties on
        buttons so the stylesheet's property-based colour rules apply correctly.
        """
        # Primary action
        for btn in [self.btnGenerate]:
            btn.setProperty("sfRole", "primary")

        # Destructive actions
        for btn in [self.btnClear, self.btnDeleteEp]:
            btn.setProperty("sfRole", "danger")

        # Success/completion
        for btn in [self.btnExportToCanvas]:
            btn.setProperty("sfRole", "success")

        # Secondary
        for btn in [self.btnSaveReport, self.txtGeom.parent() if hasattr(self, 'txtGeom') else None]:
            if btn is not None:
                btn.setProperty("sfRole", "secondary")


    def _setup_vmtk_outputs(self):
        # We explicitly set VMTK outputs to NOT generate models or text properties
        # by accessing the node selectors in the VMTK widget.
        selectors_to_disable = [
            "outputNetworkModelSelector",
            "outputNetworkPropertiesTableSelector",
            "outputCenterlinePropertiesTableSelector",
            "outputPreprocessedSurfaceModelSelector",
            "outputMeshErrorsMarkupsSelector",
            "outputVoronoiDiagramModelSelector"
        ]
        
        for sel_name in selectors_to_disable:
            selector = self.vmtk_widget.findChild("qMRMLNodeComboBox", sel_name)
            if selector:
                selector.noneEnabled = True
                if hasattr(selector, 'setCurrentNodeID'):
                    selector.setCurrentNodeID("")
                else:
                    selector.currentNodeID = ""

        # Make sure Curve and Model output generates new nodes
        curve_sel = self.vmtk_widget.findChild("qMRMLNodeComboBox", "outputCenterlineCurveSelector")
        if curve_sel:
            curve_sel.renameEnabled = True
            
        model_sel = self.vmtk_widget.findChild("qMRMLNodeComboBox", "outputCenterlineModelSelector")
        if model_sel:
            model_sel.renameEnabled = True

    def browse_geom(self):
        path = qt.QFileDialog.getOpenFileName(self, "Select 3D Geometry", "", "3D Models (*.vtp *.stl *.obj)")
        if path:
            self.txtGeom.setText(path)
            if self.surfaceNode:
                slicer.mrmlScene.RemoveNode(self.surfaceNode)
            self.surfaceNode = slicer.util.loadModel(path)
            
            # Make the vessel translucent so centerlines are visible inside
            if self.surfaceNode and self.surfaceNode.GetDisplayNode():
                self.surfaceNode.GetDisplayNode().SetOpacity(0.4)
            
            # Clear the scene combobox to avoid ambiguity
            self.sceneModelSelector.setCurrentNode(None)
            
            # Hook the surface into VMTK widget
            surface_sel = self.vmtk_widget.findChild("qMRMLNodeComboBox", "inputSurfaceSelector")
            if surface_sel:
                surface_sel.setCurrentNode(self.surfaceNode)
                
            # Reset camera
            layout_manager = slicer.app.layoutManager()
            if layout_manager and layout_manager.threeDWidget(0):
                layout_manager.threeDWidget(0).threeDView().resetFocalPoint()

    def _on_scene_model_selected(self, node):
        """Called when the user picks a model from the scene combobox."""
        if node is None:
            return
        self.surfaceNode = node
        self.txtGeom.clear()

        # Make the vessel translucent so centerlines are visible inside
        if self.surfaceNode.GetDisplayNode():
            self.surfaceNode.GetDisplayNode().SetOpacity(0.4)

        # Hook the surface into the VMTK widget
        surface_sel = self.vmtk_widget.findChild("qMRMLNodeComboBox", "inputSurfaceSelector")
        if surface_sel:
            surface_sel.setCurrentNode(self.surfaceNode)

        # Reset camera
        layout_manager = slicer.app.layoutManager()
        if layout_manager and layout_manager.threeDWidget(0):
            layout_manager.threeDWidget(0).threeDView().resetFocalPoint()

    def _ensure_endpoints(self):
        if not self.endpointsNode or slicer.mrmlScene.GetNodeByID(self.endpointsNode.GetID()) is None:
            self.endpointsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "CenterlineEndpoints")
            # Observers to keep the list updated when points are placed or auto-detected
            self.endpointsNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointPositionDefinedEvent, self.refresh_ep_list)
            self.endpointsNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.refresh_ep_list)
            self.endpointsNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.refresh_ep_list)
            self._configure_endpoint_display()
            
        # Hook into VMTK widget
        ep_sel = self.vmtk_widget.findChild("qMRMLNodeComboBox", "endPointsMarkupsSelector")
        if ep_sel:
            ep_sel.setCurrentNode(self.endpointsNode)
            
        return self.endpointsNode

    def _configure_endpoint_display(self):
        if not self.endpointsNode:
            return

        display_node = self.endpointsNode.GetDisplayNode()
        if not display_node:
            self.endpointsNode.CreateDefaultDisplayNodes()
            display_node = self.endpointsNode.GetDisplayNode()

        if display_node:
            display_node.SetVisibility(True)
            if hasattr(display_node, "SetSelectedColor"):
                display_node.SetSelectedColor(1.0, 0.2, 0.1)
            if hasattr(display_node, "SetColor"):
                display_node.SetColor(0.1, 0.8, 1.0)
            if hasattr(display_node, "SetGlyphScale"):
                display_node.SetGlyphScale(3.0)
            if hasattr(display_node, "SetTextScale"):
                display_node.SetTextScale(2.0)
            if hasattr(display_node, "SetPropertiesLabelVisibility"):
                display_node.SetPropertiesLabelVisibility(True)

    def _configure_curve_display(self, curve_node):
        display_node = curve_node.GetDisplayNode()
        if not display_node:
            curve_node.CreateDefaultDisplayNodes()
            display_node = curve_node.GetDisplayNode()

        if not display_node:
            return

        display_node.SetVisibility(True)
        if hasattr(display_node, "SetVisibility3D"):
            display_node.SetVisibility3D(True)
        if hasattr(display_node, "SetPropertiesLabelVisibility"):
            display_node.SetPropertiesLabelVisibility(False)
        if hasattr(display_node, "SetPointLabelsVisibility"):
            display_node.SetPointLabelsVisibility(False)
        if hasattr(display_node, "SetNameVisibility"):
            display_node.SetNameVisibility(False)
        if hasattr(display_node, "SetTextScale"):
            display_node.SetTextScale(2.2)
        if hasattr(display_node, "SetLineThickness"):
            display_node.SetLineThickness(1.0)

    def _branch_color(self, index):
        colors = [
            (0.90, 0.20, 0.18),
            (0.12, 0.48, 0.85),
            (0.90, 0.38, 0.12),
            (0.20, 0.70, 0.35),
            (0.75, 0.25, 0.85),
            (0.95, 0.78, 0.20),
            (0.10, 0.72, 0.72),
            (0.95, 0.45, 0.65),
            (0.62, 0.46, 0.28),
            (0.70, 0.70, 0.70),
        ]
        return colors[index % len(colors)]

    def _set_curve_color(self, curve_node, color):
        display_node = curve_node.GetDisplayNode()
        if display_node and hasattr(display_node, "SetColor"):
            display_node.SetColor(*color)

    def _populate_branch_table(self, branch_rows):
        self.branchTable.setRowCount(len(branch_rows))
        for row, branch in enumerate(branch_rows):
            color = branch["color"]
            swatch = qt.QLabel()
            swatch.setFixedSize(18, 18)
            swatch.setStyleSheet(
                "background: rgb(%d, %d, %d); border: 1px solid #111; border-radius: 3px;"
                % (int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))
            )
            self.branchTable.setCellWidget(row, 0, swatch)

            name_item = qt.QTableWidgetItem(branch["name"])
            length_item = qt.QTableWidgetItem(f"{branch['length']:.1f} mm")
            radius_item = qt.QTableWidgetItem(f"{branch['radius']:.2f} mm")
            area_item = qt.QTableWidgetItem(f"{branch['area']:.2f} mm²")
            groups = f"In: {branch['inlet_group']} | Out: {branch['outlet_group']}"
            groups_item = qt.QTableWidgetItem(groups)
            self.branchTable.setItem(row, 1, name_item)
            self.branchTable.setItem(row, 2, length_item)
            self.branchTable.setItem(row, 3, radius_item)
            self.branchTable.setItem(row, 4, area_item)
            self.branchTable.setItem(row, 5, groups_item)
        self.branchTable.resizeRowsToContents()

    def select_branch_from_table(self):
        row = self.branchTable.currentRow()
        if row < 0 or row >= len(self.branchNodes):
            return

        for i, node in enumerate(self.branchNodes):
            display_node = node.GetDisplayNode()
            if not display_node:
                continue
            if hasattr(display_node, "SetSelected"):
                display_node.SetSelected(i == row)
            if hasattr(display_node, "SetLineThickness"):
                display_node.SetLineThickness(1.5 if i == row else 1.0)
            if hasattr(display_node, "SetPropertiesLabelVisibility"):
                display_node.SetPropertiesLabelVisibility(False)
            if hasattr(display_node, "SetPointLabelsVisibility"):
                display_node.SetPointLabelsVisibility(False)
            if hasattr(display_node, "SetNameVisibility"):
                display_node.SetNameVisibility(False)

    def _set_view_interaction_mode(self):
        interaction_node = slicer.app.applicationLogic().GetInteractionNode()
        interaction_node.SetPlaceModePersistence(0)
        interaction_node.SetCurrentInteractionMode(interaction_node.ViewTransform)

    def _remove_legacy_branch_label_nodes(self):
        for node in list(slicer.util.getNodesByClass("vtkMRMLMarkupsFiducialNode")):
            if node.GetName().startswith("CenterlineBranchLabels"):
                slicer.mrmlScene.RemoveNode(node)

    def _curve_endpoint_positions(self, curve_node):
        n = curve_node.GetNumberOfControlPoints()
        if n <= 0:
            return None

        start = [0.0, 0.0, 0.0]
        end = [0.0, 0.0, 0.0]
        curve_node.GetNthControlPointPositionWorld(0, start)
        curve_node.GetNthControlPointPositionWorld(n - 1, end)
        return start, end

    def _distance(self, a, b):
        return sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5

    def _endpoint_group_name(self, connected_branches):
        if not connected_branches:
            return "Terminal"
        return ", ".join(connected_branches)

    def _branch_sort_key(self, name):
        try:
            return int(name.split()[-1])
        except Exception:
            return name

    def _add_branch_connectivity(self, branch_rows, tolerance_mm=2.0):
        for branch in branch_rows:
            branch["connected_to"] = []
            branch["inlet_group"] = "Terminal"
            branch["outlet_group"] = "Terminal"

        endpoints = []
        for branch in branch_rows:
            branch_endpoints = branch.get("endpoints")
            if not branch_endpoints:
                continue
            endpoints.append({"branch": branch, "side": "inlet", "position": branch_endpoints[0]})
            endpoints.append({"branch": branch, "side": "outlet", "position": branch_endpoints[1]})

        for endpoint in endpoints:
            connected_names = []
            for other in endpoints:
                if endpoint is other:
                    continue
                if endpoint["branch"] is other["branch"]:
                    continue
                if self._distance(endpoint["position"], other["position"]) <= tolerance_mm:
                    connected_names.append(other["branch"]["name"])

            unique_names = sorted(set(connected_names), key=self._branch_sort_key)
            if endpoint["side"] == "inlet":
                endpoint["branch"]["inlet_group"] = self._endpoint_group_name(unique_names)
            else:
                endpoint["branch"]["outlet_group"] = self._endpoint_group_name(unique_names)

        for branch in branch_rows:
            connected = []
            for group in (branch["inlet_group"], branch["outlet_group"]):
                if group == "Terminal":
                    continue
                connected.extend([name.strip() for name in group.split(",")])
            branch["connected_to"] = sorted(set(connected), key=self._branch_sort_key)

    def save_branch_report(self):
        if not self.branchReportRows:
            slicer.util.errorDisplay("Generate centerlines before saving a branch report.")
            return

        default_path = "starfish_centerline_report.starfish_slicer"
        path = qt.QFileDialog.getSaveFileName(
            self,
            "Save Branch Report",
            default_path,
            "STARFiSh Slicer Export (*.starfish_slicer)"
        )
        if not path:
            return

        report_rows = []
        for branch in self.branchReportRows:
            report_rows.append({
                "branch": branch["name"],
                "length_mm": branch["length"],
                "mean_radius_mm": branch["radius"],
                "mean_area_mm2": branch["area"],
                "inlet_connected_to": branch["inlet_group"],
                "outlet_connected_to": branch["outlet_group"],
                "connected_to": branch["connected_to"],
            })
        try:
            import json
            report_data = {
                "version": "1.0",
                "branches": report_rows
            }
            with open(path, "w") as f:
                json.dump(report_data, f, indent=4)
            
            self.txtResults.append(f"\nReport saved successfully to:\n{path}")
        except Exception as e:
            slicer.util.errorDisplay(f"Failed to save report: {str(e)}")

    def export_to_canvas(self):
        if not self.branchReportRows:
            slicer.util.errorDisplay("Generate centerlines before exporting.")
            return

        def get_canonical_id(branch_name, group_str, side):
            if not group_str or group_str == "Terminal":
                return f"{branch_name} ({side})"
            members = [branch_name] + [m.strip() for m in group_str.split(",") if m.strip()]
            def sort_key(s):
                try: return int(s.split()[-1])
                except: return s
            members = sorted(list(set(members)), key=sort_key)
            return ", ".join(members)

        nodes = set()
        edges = []
        raw_3d_points = {}

        for index, branch in enumerate(self.branchReportRows):
            name = branch["name"]
            in_group = branch["inlet_group"]
            out_group = branch["outlet_group"]
            
            start_id = get_canonical_id(name, in_group, "Inlet")
            end_id = get_canonical_id(name, out_group, "Outlet")
            
            nodes.add(start_id)
            nodes.add(end_id)
            
            if "endpoints" in branch and branch["endpoints"]:
                if start_id not in raw_3d_points:
                    raw_3d_points[start_id] = branch["endpoints"][0]
                if end_id not in raw_3d_points:
                    raw_3d_points[end_id] = branch["endpoints"][1]

            edges.append({
                "branch_name": name,
                "start": start_id,
                "end": end_id,
                "index": index,
                "length_mm": branch["length"],
                "area_mm2": branch["area"]
            })

        # --- Tree-Traversal 3D-to-2D Unfolding ---
        # Simply projecting 3D to 2D squishes vessels (e.g., if they run along the Y axis).
        # When VascularEditorWidget calls `enforce_fixed_lengths()`, it preserves the 2D angle 
        # but forces the length to be the true 3D length. If a vessel was squished to 0 length in 2D, 
        # its angle is undefined, causing the network to explode into a mess.
        # Solution: Traverse the graph, find the 3D direction vector for each branch, project THAT 
        # to 2D, normalize it, and place the child at EXACTLY the correct physical distance in 2D.

        SCALE = 4.0  # PIXELS_PER_MM roughly

        # 1. Build adjacency list for traversal
        adj = {n: [] for n in nodes}
        in_degree = {n: 0 for n in nodes}
        
        # We also need the true 3D positions to compute direction vectors
        node_3d = {}
        for branch in self.branchReportRows:
            start_id = get_canonical_id(branch["name"], branch["inlet_group"], "Inlet")
            end_id = get_canonical_id(branch["name"], branch["outlet_group"], "Outlet")
            adj[start_id].append({
                "target": end_id,
                "length_mm": branch["length"]
            })
            in_degree[end_id] += 1
            
            if "endpoints" in branch and branch["endpoints"]:
                if start_id not in node_3d: node_3d[start_id] = branch["endpoints"][0]
                if end_id not in node_3d:   node_3d[end_id] = branch["endpoints"][1]

        # 2. Traverse and place nodes
        positions = {}
        roots = [n for n in nodes if in_degree[n] == 0]
        if not roots and nodes:
            roots = [list(nodes)[0]] # Fallback if cyclic
            
        import math
        
        def place_node(node_id, current_pos):
            if node_id in positions:
                return
            positions[node_id] = current_pos
            
            for edge in adj[node_id]:
                child_id = edge["target"]
                length_px = edge["length_mm"] * SCALE
                
                # Compute 3D direction vector from parent to child
                if node_id in node_3d and child_id in node_3d:
                    p1 = node_3d[node_id]
                    p2 = node_3d[child_id]
                    dx = p2[0] - p1[0]
                    dy = p2[1] - p1[1]
                    dz = p2[2] - p1[2]
                else:
                    dx, dy, dz = 1.0, 0.0, 0.0
                    
                # Project 3D vector to 2D canvas (Canvas X = Right, Canvas Y = Inferior)
                vec_x = dx
                vec_y = -dz
                
                # If the branch was purely in the Y (Anterior/Posterior) direction, the 2D projection is zero.
                # We must give it an artificial direction in 2D so it doesn't collapse.
                vec_len_2d = math.sqrt(vec_x**2 + vec_y**2)
                if vec_len_2d < 1e-3:
                    # Map the Y depth to a diagonal 2D direction
                    vec_x = dy
                    vec_y = dy
                    vec_len_2d = math.sqrt(vec_x**2 + vec_y**2)
                    if vec_len_2d < 1e-3:
                        vec_x, vec_y = 0.0, 1.0 # Absolute fallback (straight down)
                        vec_len_2d = 1.0
                        
                # Normalize the 2D direction and multiply by the TRUE physical length!
                norm_x = vec_x / vec_len_2d
                norm_y = vec_y / vec_len_2d
                
                child_pos = {
                    "x": current_pos["x"] + (norm_x * length_px),
                    "y": current_pos["y"] + (norm_y * length_px)
                }
                place_node(child_id, child_pos)

        # Start placement from roots
        start_x, start_y = 0.0, 0.0
        for r in roots:
            place_node(r, {"x": start_x, "y": start_y})
            start_x += 200.0 # Offset multiple roots horizontally

        if self.export_callback:
            self.export_callback(positions, edges)
            slicer.util.infoDisplay("Successfully sent to Model Builder Canvas.")
        else:
            slicer.util.errorDisplay("Export callback not set.")

    def refresh_ep_list(self, caller=None, event=None):
        blocked = self.epList.blockSignals(True)
        self.epList.clear()
        if not self.endpointsNode:
            self.lblEpCount.setText("Endpoints selected: 0")
            self.epList.blockSignals(blocked)
            return
            
        n = self.endpointsNode.GetNumberOfControlPoints()
        self.lblEpCount.setText(f"Endpoints selected: {n}")
        for i in range(n):
            label = self.endpointsNode.GetNthControlPointLabel(i)
            self.epList.addItem(f"Endpoint {i}: {label}")
        self.epList.blockSignals(blocked)

    def select_endpoint_from_list(self, row):
        if not self.endpointsNode or row < 0:
            return

        n = self.endpointsNode.GetNumberOfControlPoints()
        for i in range(n):
            self.endpointsNode.SetNthControlPointSelected(i, i == row)
        self._set_view_interaction_mode()

    def delete_selected_endpoint(self):
        if not self.endpointsNode: return
        row = self.epList.currentRow()
        if row < 0:
            for i in range(self.endpointsNode.GetNumberOfControlPoints()):
                if self.endpointsNode.GetNthControlPointSelected(i):
                    row = i
                    break
        if row >= 0:
            self.endpointsNode.RemoveNthControlPoint(row)
            self.refresh_ep_list()
            self._set_view_interaction_mode()

    def auto_detect(self):
        if not self.surfaceNode:
            slicer.util.errorDisplay("Load a 3D file first.")
            return
            
        self._ensure_endpoints()
        auto_btn = self.vmtk_widget.findChild(qt.QPushButton, "autoDetectEndPointsPushButton")
        if auto_btn:
            self.txtResults.append("Auto-detecting endpoints...")
            slicer.app.processEvents()
            auto_btn.click()
            self.refresh_ep_list()
            self._force_transparency()
            self._configure_endpoint_display()
            self._set_view_interaction_mode()
        else:
            slicer.util.errorDisplay("Could not find VMTK Auto-Detect button.")

    def _force_transparency(self):
        # Force all models in the scene to be translucent (useful if VMTK generates preprocessed surfaces)
        model_nodes = slicer.util.getNodesByClass("vtkMRMLModelNode")
        for m_node in model_nodes:
            display_node = m_node.GetDisplayNode()
            if display_node:
                display_node.SetOpacity(0.4)

    def place_endpoints(self):
        self._ensure_endpoints()
        interaction_node = slicer.app.applicationLogic().GetInteractionNode()
        selection_node = slicer.app.applicationLogic().GetSelectionNode()
        
        selection_node.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        selection_node.SetReferenceActivePlaceNodeID(self.endpointsNode.GetID())
        interaction_node.SetPlaceModePersistence(1)
        interaction_node.SetCurrentInteractionMode(interaction_node.Place)
        self.show()
        self.raise_()

    def stop_placing(self):
        self._set_view_interaction_mode()
        self.refresh_ep_list()
        self.show()
        self.raise_()

    def clear_endpoints(self):
        if self.endpointsNode:
            self.endpointsNode.RemoveAllControlPoints()
        self.refresh_ep_list()

    def generate_curve(self):
        if not self.surfaceNode:
            slicer.util.errorDisplay("Load a 3D file first.")
            return
            
        self._ensure_endpoints()
        if self.endpointsNode.GetNumberOfControlPoints() < 2:
            slicer.util.errorDisplay("Need at least 2 endpoints.")
            return

        self._remove_legacy_branch_label_nodes()
            
        # Ensure we are generating new curve and model nodes
        curve_sel = self.vmtk_widget.findChild("qMRMLNodeComboBox", "outputCenterlineCurveSelector")
        if curve_sel:
            curve_sel.addNode() # Trigger 'Create new node'
            
        model_sel = self.vmtk_widget.findChild("qMRMLNodeComboBox", "outputCenterlineModelSelector")
        if model_sel:
            model_sel.addNode() # Trigger 'Create new node'
            
        apply_btn = self.vmtk_widget.findChild(qt.QPushButton, "applyButton")
        if apply_btn:
            self.txtResults.append("Computing centerlines... please wait.")
            slicer.app.processEvents()
            
            # Click VMTK's apply button
            apply_btn.click()
            
            # Find the generated curve node(s) and compute lengths
            self.txtResults.clear()
            self.txtResults.append("Extracted branches. Select a row to highlight a branch in the 3D view.")
            self.branchNodes = []
            self.branchReportRows = []
            branch_rows = []
            
            # 1. First, find the generated Centerline Model and build a point locator to find Radius
            import vtk
            radius_locator = None
            radius_array = None
            
            # SlicerVMTK typically names it "Centerline model"
            model_nodes = slicer.util.getNodesByClass("vtkMRMLModelNode")
            centerline_model = None
            for m in model_nodes:
                if m.GetDisplayNode() and "Centerline model" in m.GetName():
                    centerline_model = m
                    break
                    
            if centerline_model:
                # Hide the model so it doesn't clutter the view
                centerline_model.GetDisplayNode().SetVisibility(False)
                polyData = centerline_model.GetPolyData()
                if polyData:
                    radius_array = polyData.GetPointData().GetArray("Radius")
                    if radius_array:
                        radius_locator = vtk.vtkKdTreePointLocator()
                        radius_locator.SetDataSet(polyData)
                        radius_locator.BuildLocator()

            # 2. Iterate through curves, calculate length and lookup start/end areas
            curve_nodes = slicer.util.getNodesByClass("vtkMRMLMarkupsCurveNode")
            found = False
            branch_idx = 1
            for node in curve_nodes:
                if node == self.endpointsNode:
                    continue
                length = node.GetCurveLengthWorld()
                if length > 0:
                    found = True
                    
                    # Look up average radius along the branch
                    mean_radius = 0.0
                    mean_area = 0.0
                    if radius_locator and radius_array:
                        num_points = node.GetNumberOfControlPoints()
                        if num_points > 0:
                            sum_r = 0.0
                            for i in range(num_points):
                                pos = [0.0, 0.0, 0.0]
                                node.GetNthControlPointPositionWorld(i, pos)
                                idx = radius_locator.FindClosestPoint(pos)
                                sum_r += radius_array.GetTuple1(idx)
                            mean_radius = sum_r / num_points
                            mean_area = 3.1415926535 * (mean_radius ** 2)

                    # Rename the node so the length appears in the 3D view text label
                    new_name = f"Branch {branch_idx} ({length:.1f} mm)"
                    node.SetName(new_name)

                    self._configure_curve_display(node)
                    color = self._branch_color(branch_idx - 1)
                    self._set_curve_color(node, color)
                        
                    self.txtResults.append(f"{new_name} | R: {mean_radius:.2f} mm | A: {mean_area:.1f} mm²")
                    self.branchNodes.append(node)
                    branch_rows.append({
                        "name": f"Branch {branch_idx}",
                        "length": length,
                        "radius": mean_radius,
                        "area": mean_area,
                        "color": color,
                        "endpoints": self._curve_endpoint_positions(node),
                    })
                    branch_idx += 1
                    
            # Just in case VMTK generated a temporary preprocessed model, make it translucent too
            self._force_transparency()
                    
            if not found:
                self.txtResults.append("Failed to generate curves.")
            else:
                self._add_branch_connectivity(branch_rows)
                self.branchReportRows = branch_rows
                self._populate_branch_table(branch_rows)
        else:
            slicer.util.errorDisplay("Could not find VMTK Apply button.")


# Removed standalone execution block
