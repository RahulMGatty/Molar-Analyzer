import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import math

#
# MolarAnalyzer (Pro Version - Fixed Dropdown)
#

class MolarAnalyzer(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Molar WAR Lines (AI-Assisted)"
        self.parent.categories = ["Quantification"]
        self.parent.contributors = ["Rahul M"]
        self.parent.helpText = """
        Uses AI Segmentation to visualize Winter's WAR Lines.
        Input: Segmentation Node + 2 Manual Landmarks.
        """
        self.parent.acknowledgementText = ""

#
# MolarAnalyzerWidget
#

class MolarAnalyzerWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        # Layout Logic
        if self.parent.layout() is None:
            self.layout = qt.QVBoxLayout(self.parent)
        else:
            self.layout = self.parent.layout()

        # --- SECTION 1: AI SEGMENTATION INPUT ---
        segCollapsible = ctk.ctkCollapsibleButton()
        segCollapsible.text = "1. AI Segmentation Data"
        self.layout.addWidget(segCollapsible)
        segLayout = qt.QFormLayout(segCollapsible)

        # Selector for the Segmentation Node
        self.segmentationSelector = slicer.qMRMLNodeComboBox()
        self.segmentationSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
        self.segmentationSelector.selectNodeUponCreation = True
        self.segmentationSelector.addEnabled = False
        self.segmentationSelector.noneEnabled = False
        self.segmentationSelector.setMRMLScene(slicer.mrmlScene)
        self.segmentationSelector.setToolTip("Select the output from Dental Segmentator")
        segLayout.addRow("Segmentation Node:", self.segmentationSelector)

        # Segment Selector (Which tooth is the Wisdom Tooth?)
        # We use a standard ComboBox and manually fill it to prevent empty lists
        self.segmentSelector = qt.QComboBox()
        self.segmentSelector.setToolTip("Select the Wisdom Tooth (e.g., 38 or 48)")
        segLayout.addRow("Target Tooth:", self.segmentSelector)
        
        # Connect update trigger (Force update on load)
        self.segmentationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateSegmentList)
        
        # Initialize the list immediately
        self.updateSegmentList()

        # --- SECTION 2: MANUAL LANDMARKS ---
        pointsCollapsible = ctk.ctkCollapsibleButton()
        pointsCollapsible.text = "2. Key Surgical Levels"
        self.layout.addWidget(pointsCollapsible)
        pointsLayout = qt.QFormLayout(pointsCollapsible)

        # Bone Level (Amber Line)
        self.boneSelector = slicer.qMRMLNodeComboBox()
        self.boneSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
        self.boneSelector.selectNodeUponCreation = True
        self.boneSelector.addEnabled = True
        self.boneSelector.setMRMLScene(slicer.mrmlScene)
        self.boneSelector.setToolTip("Click on the Alveolar Bone Crest (Curve of Gum)")
        pointsLayout.addRow("Bone Point (Amber Line):", self.boneSelector)

        # Nerve Level (Red Line)
        self.nerveSelector = slicer.qMRMLNodeComboBox()
        self.nerveSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
        self.nerveSelector.selectNodeUponCreation = True
        self.nerveSelector.addEnabled = True
        self.nerveSelector.setMRMLScene(slicer.mrmlScene)
        self.nerveSelector.setToolTip("Click on the Inferior Alveolar Nerve")
        pointsLayout.addRow("Nerve Point (Red Line):", self.nerveSelector)

        # --- BUTTON ---
        self.applyButton = qt.QPushButton("Generate WAR Lines Visualization")
        self.applyButton.setStyleSheet("font-weight: bold; padding: 10px; font-size: 12pt;")
        self.layout.addWidget(self.applyButton)

        # --- RESULTS ---
        self.resultsLabel = qt.QLabel("Ready for Analysis")
        self.resultsLabel.alignment = qt.Qt.AlignCenter
        self.resultsLabel.setStyleSheet("border: 1px solid gray; padding: 10px; background-color: #f0f0f0;")
        self.layout.addWidget(self.resultsLabel)

        self.applyButton.connect('clicked(bool)', self.onApplyButton)
        self.layout.addStretch(1)

    def updateSegmentList(self):
        # MANUALLY FORCE options so it never fails
        self.segmentSelector.clear()
        
        # Add Standard Wisdom Tooth Options
        self.segmentSelector.addItem("Select Tooth...", "None")
        self.segmentSelector.addItem("Lower Left Wisdom (38)", "38")
        self.segmentSelector.addItem("Lower Right Wisdom (48)", "48")
        
        # Add Generic Options just in case
        self.segmentSelector.addItem("Mandible (Bone)", "mandible")
        self.segmentSelector.addItem("Inferior Alveolar Nerve", "nerve")

    def onApplyButton(self):
        # 1. Validation
        segNode = self.segmentationSelector.currentNode()
        boneNode = self.boneSelector.currentNode()
        nerveNode = self.nerveSelector.currentNode()

        if not segNode or not boneNode or not nerveNode:
            self.resultsLabel.text = "Error: Please select Segmentation, Bone Point, and Nerve Point!"
            self.resultsLabel.setStyleSheet("background-color: #ffcccc; color: red; font-weight: bold;")
            return

        # 2. Get Coordinates
        pos_bone = [0,0,0]
        pos_nerve = [0,0,0]
        
        # Check if points exist
        if boneNode.GetNumberOfControlPoints() < 1 or nerveNode.GetNumberOfControlPoints() < 1:
            self.resultsLabel.text = "Error: Place points on the image first!"
            return

        boneNode.GetNthControlPointPosition(0, pos_bone)
        nerveNode.GetNthControlPointPosition(0, pos_nerve)

        # 3. Create Visualization Planes
        self.createPlane("Amber_Line_Plane", pos_bone, [1, 0.6, 0]) # Orange
        self.createPlane("Red_Line_Plane", pos_nerve, [1, 0, 0])    # Red

        # 4. Calculation
        # Vertical Distance (Z-axis difference)
        diff = abs(pos_bone[2] - pos_nerve[2]) 
        
        # Classification Logic
        risk_class = ""
        color = ""
        
        if diff < 2.0: 
             risk_class = "HIGH COMPLEXITY (Red)"
             color = "#ffcccc" # Light Red
        elif diff < 5.0:
             risk_class = "MODERATE COMPLEXITY (Amber)" 
             color = "#fff4cc" # Light Orange
        else:
             risk_class = "LOW COMPLEXITY (White)"
             color = "#ccffcc" # Light Green

        self.resultsLabel.text = f"Surgical Depth: {diff:.2f} mm\nPrediction: {risk_class}"
        self.resultsLabel.setStyleSheet(f"background-color: {color}; font-weight: bold; padding: 10px; border: 2px solid black;")

    def createPlane(self, name, center, color):
        # Create a large flat plane at the specific height (Z-level)
        planeSource = vtk.vtkPlaneSource()
        planeSource.SetCenter(center[0], center[1], center[2])
        planeSource.SetNormal(0, 0, 1) # Facing up (Z-axis)
        planeSource.SetXResolution(1)
        planeSource.SetYResolution(1)
        
        # Make plane large enough to slice through the whole jaw
        size = 60.0 
        planeSource.SetOrigin(center[0]-size, center[1]-size, center[2])
        planeSource.SetPoint1(center[0]+size, center[1]-size, center[2])
        planeSource.SetPoint2(center[0]-size, center[1]+size, center[2])
        planeSource.Update()

        # Check if node exists, if not create it
        modelNode = slicer.mrmlScene.GetFirstNodeByName(name)
        if not modelNode:
            modelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", name)
            modelNode.CreateDefaultDisplayNodes()
        
        modelNode.SetAndObservePolyData(planeSource.GetOutput())
        
        # Visual Properties
        displayNode = modelNode.GetDisplayNode()
        displayNode.SetColor(color)
        displayNode.SetOpacity(0.3) # Semi-transparent
        displayNode.SetSliceIntersectionVisibility(True) # Show in 2D views too!
        displayNode.SetLineWidth(3)

#
# Logic and Test Classes (Boilerplate)
#
class MolarAnalyzerLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)

class MolarAnalyzerTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear()
    def runTest(self):
        self.setUp()