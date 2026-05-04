from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt
from uijobs import Ui_JobsDialog
from PyQt5.QtWidgets import QDialog

class JobsConstruct(Ui_JobsDialog):

    def __init__(self, robustClass):
        super().__init__()
        self.robustClass = robustClass

    def setupUi(self, JobsDialog:QDialog):
        super().setupUi(JobsDialog)
        JobsDialog.setWindowFlags(JobsDialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        JobsDialog.setWindowFlags(JobsDialog.windowFlags() | Qt.WindowMinimizeButtonHint)
        self.initiateVariables()
        self.connectActions()

    def initiateVariables(self):
        self.nextJobNumber = 1

    def connectActions(self):
        self.addJobButton.clicked.connect(self.addJobHandle)

    def addJobHandle(self):
        print("Add Job Clicked")
        oneJob = QtWidgets.QWidget(self.jobsContainer)
        oneJob.setMinimumSize(QtCore.QSize(0, 50))
        oneJob.setObjectName("oneJob")
        oneJobLayout = QtWidgets.QHBoxLayout(oneJob)
        oneJobLayout.setObjectName("oneJobLayout")
        jobName = QtWidgets.QLabel(oneJob)
        jobName.setObjectName("jobName")
        oneJobLayout.addWidget(jobName)
        jobTypeSelector = QtWidgets.QComboBox(oneJob)
        jobTypeSelector.setObjectName("jobTypeSelector")
        oneJobLayout.addWidget(jobTypeSelector)
        identifierTypeSelector = QtWidgets.QComboBox(oneJob)
        identifierTypeSelector.setObjectName("identifierTypeSelector")
        oneJobLayout.addWidget(identifierTypeSelector)
        identifierValueBox = QtWidgets.QLineEdit(oneJob)
        identifierValueBox.setObjectName("identifierValueBox")
        oneJobLayout.addWidget(identifierValueBox)
        valueBox = QtWidgets.QLineEdit(oneJob)
        valueBox.setObjectName("valueBox")
        oneJobLayout.addWidget(valueBox)
        doneCheckBox = QtWidgets.QCheckBox(oneJob)
        doneCheckBox.setObjectName("doneCheckBox")
        oneJobLayout.addWidget(doneCheckBox)
        self.jobsContainerLayout.addWidget(oneJob)
        jobName.setText("Job " + str(self.nextJobNumber))
        self.nextJobNumber += 1
