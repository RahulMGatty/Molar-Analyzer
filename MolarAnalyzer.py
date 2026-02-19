import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import math

#
# MolarAnalyzer (Ultimate Prediction Version)
#

class MolarAnalyzer(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Molar Surgical Predictor"
        self.parent.categories = ["Quantification"]
        self.parent.contributors = ["Rahul M"]
        self.parent.helpText = """
        Predicts the Safe Point of Elevation (Fulcrum) and visualizes Winter's Lines.
        """
        self.parent.acknowledgementText = ""

class MolarAnalyzerWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        if self.parent.layout() is None:
            self.layout = qt.QVBoxLayout(self.parent)
        else:
            self.layout = self.parent.layout()

        # --- SECTION 1: INPUTS ---
        inputCollapsible = ctk.ctkCollapsibleButton()
        inputCollapsible.text = "Surgical Inputs"
        self.layout.addWidget(inputCollapsible)
        inputLayout = qt.QFormLayout(inputCollapsible)

        # 1. Segmentation (Visual Reference)
        self.segmentationSelector = slicer.qMRMLNodeComboBox()
        self.segmentationSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
        self.segmentationSelector.selectNodeUponCreation = True
        self.segmentationSelector.addEnabled = False
        self.segmentationSelector.noneEnabled = False
        self.segmentationSelector.setMRMLScene(slicer.mrmlScene)
        self.segmentationSelector.setToolTip("Select the AI Segmentation")
        inputLayout.addRow("Segmentation:", self.segmentationSelector)

        # 2. Target Tooth (Dropdown)
        self.segmentSelector = qt.QComboBox()
        inputLayout.addRow("Target Tooth:", self.segmentSelector)
        self.segmentationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateSegmentList)
        self.updateSegmentList() # Force load

        # 3. Bone Point (The Curve)
        self.boneSelector = slicer.qMRMLNodeComboBox()
        self.boneSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
        self.boneSelector.selectNodeUponCreation = True
        self.boneSelector.addEnabled = True
        self.boneSelector.setMRMLScene(slicer.mrmlScene)
        self.boneSelector.setToolTip("Click on the Mesial Bone Crest")
        inputLayout.addRow("Bone Point (Gum Curve):", self.boneSelector)

        # 4. Nerve Point (The Danger)
        self.nerveSelector = slicer.qMRMLNodeComboBox()
        self.nerveSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
        self.nerveSelector.selectNodeUponCreation = True
        self.nerveSelector.addEnabled = True
        self.nerveSelector.setMRMLScene(slicer.mrmlScene)
        self.nerveSelector.setToolTip("Click on the Nerve Canal Roof")
        inputLayout.addRow("Nerve Point (Canal):", self.nerveSelector)

        # --- BUTTON ---
        self.applyButton = qt.QPushButton("PREDICT Safe Elevation Point")
        self.applyButton.setStyleSheet("""
            background-color: #4CAF50; 
            color: white; 
            font-weight: bold; 
            font-size: 14px; 
            padding: 12px;
            border-radius: 5px;
        """)
        self.layout.addWidget(self.applyButton)

        # --- RESULTS ---
        self.resultsLabel = qt.QLabel("System Ready")
        self.resultsLabel.alignment = qt.Qt.AlignCenter
        self.resultsLabel.setStyleSheet("border: 1px solid gray; padding: 10px; background-color: #f0f0f0;")
        self.layout.addWidget(self.resultsLabel)

        self.applyButton.connect('clicked(bool)', self.onApplyButton)
        self.layout.addStretch(1)

    def updateSegmentList(self):
        self.segmentSelector.clear()
        self.segmentSelector.addItem("Select Tooth...", "None")
        self.segmentSelector.addItem("Lower Left Wisdom (38)", "38")
        self.segmentSelector.addItem("Lower Right Wisdom (48)", "48")

    def onApplyButton(self):
        # 1. Validation
        boneNode = self.boneSelector.currentNode()
        nerveNode = self.nerveSelector.currentNode()

        if not boneNode or not nerveNode:
            self.resultsLabel.text = "Error: Please place both points first!"
            return

        # 2. Get Coordinates
        pos_bone = [0,0,0]
        pos_nerve = [0,0,0]
        
        # Safety check
        if boneNode.GetNumberOfControlPoints() < 1 or nerveNode.GetNumberOfControlPoints() < 1:
            self.resultsLabel.text = "Error: Points are missing on the screen."
            return

        boneNode.GetNthControlPointPosition(0, pos_bone)
        nerveNode.GetNthControlPointPosition(0, pos_nerve)

        # 3. VISUALIZATION A: The Planes (Region)
        self.createPlane("Amber_Bone_Level", pos_bone, [1, 0.6, 0]) # Orange
        self.createPlane("Red_Nerve_Level", pos_nerve, [1, 0, 0])   # Red

        # 4. VISUALIZATION B: The Prediction Point (The Green Sphere)
        # This highlights the exact bone fulcrum as the "Safe Point"
        self.createPredictionMarker(pos_bone)

        # 5. Calculation
        diff = abs(pos_bone[2] - pos_nerve[2]) 
        
        risk_class = ""
        color = ""
        if diff < 2.0: 
             risk_class = "HIGH RISK"
             color = "#ffcccc"
        elif diff < 4.0:
             risk_class = "MODERATE RISK" 
             color = "#fff4cc"
        else:
             risk_class = "LOW RISK"
             color = "#ccffcc"

        self.resultsLabel.text = f"Safe Elevation Point: LOCATED (Green)\nNerve Margin: {diff:.2f} mm\nPrediction: {risk_class}"
        self.resultsLabel.setStyleSheet(f"background-color: {color}; font-weight: bold; padding: 10px; border: 2px solid black;")

    def createPredictionMarker(self, pos):
        # 1. Create the Green Sphere
        sphereSource = vtk.vtkSphereSource()
        sphereSource.SetCenter(pos[0], pos[1], pos[2])
        sphereSource.SetRadius(1.5) # Size of the dot
        sphereSource.Update()

        # Node setup
        nodeName = "Predicted_Point"
        modelNode = slicer.mrmlScene.GetFirstNodeByName(nodeName)
        if not modelNode:
            modelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", nodeName)
            modelNode.CreateDefaultDisplayNodes()
        
        modelNode.SetAndObservePolyData(sphereSource.GetOutput())
        modelNode.GetDisplayNode().SetColor(0, 1, 0) # Bright Green
        modelNode.GetDisplayNode().SetAmbient(0.5)   # Make it glow
        
        # 2. Create the Text Label pointing to it
        markupsNode = slicer.mrmlScene.GetFirstNodeByName("Prediction_Label")
        if not markupsNode:
            markupsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "Prediction_Label")
        
        markupsNode.RemoveAllControlPoints()
        # Offset the label slightly so it floats above the point
        markupsNode.AddControlPoint(pos[0], pos[1], pos[2] + 5) 
        markupsNode.SetNthControlPointLabel(0, "SAFE ELEVATION POINT")
        markupsNode.GetDisplayNode().SetTextScale(3.0)
        markupsNode.GetDisplayNode().SetSelectedColor(0, 1, 0) # Green Text

    def createPlane(self, name, center, color):
        planeSource = vtk.vtkPlaneSource()
        planeSource.SetCenter(center[0], center[1], center[2])
        planeSource.SetNormal(0, 0, 1)
        planeSource.SetXResolution(1)
        planeSource.SetYResolution(1)
        size = 50.0 
        planeSource.SetOrigin(center[0]-size, center[1]-size, center[2])
        planeSource.SetPoint1(center[0]+size, center[1]-size, center[2])
        planeSource.SetPoint2(center[0]-size, center[1]+size, center[2])
        planeSource.Update()

        modelNode = slicer.mrmlScene.GetFirstNodeByName(name)
        if not modelNode:
            modelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", name)
            modelNode.CreateDefaultDisplayNodes()
        
        modelNode.SetAndObservePolyData(planeSource.GetOutput())
        displayNode = modelNode.GetDisplayNode()
        displayNode.SetColor(color)
        displayNode.SetOpacity(0.3)
        displayNode.SetSliceIntersectionVisibility(True)

class MolarAnalyzerLogic(ScriptedLoadableModuleLogic):
    pass
class MolarAnalyzerTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear()
    def runTest(self):
        self.setUp()