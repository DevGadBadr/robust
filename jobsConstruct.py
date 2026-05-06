from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt
from uijobs import Ui_JobsDialog
from PyQt5.QtWidgets import QDialog
from scrapeJobsHelpers import JOP_TYPES, IDENTIFIER_VALUES
import json

class JobsConstruct(Ui_JobsDialog):

    def __init__(self, robustClass, jobsFor, scrapeuuid):
        super().__init__()
        self.robustClass = robustClass
        self.jobsFor = jobsFor
        self.scrapeuuid = scrapeuuid

    def setupUi(self, JobsDialog:QDialog):
        super().setupUi(JobsDialog)
        JobsDialog.setWindowFlags(JobsDialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        JobsDialog.setWindowFlags(JobsDialog.windowFlags() | Qt.WindowMinimizeButtonHint)
        self.statusLabel.setText(self.jobsFor)
        self.initiateVariables()
        self.connectActions()
        self.initiateJobTypeOptions(self.jobTypeSelector)
        self.initiateIdentifierTypeOptions(self.identifierTypeSelector)
        self.initiateSavedJobs()

    def initiateSavedJobs(self):
        with open("./resources/jobs.json","r") as f:
            jobsFile = json.load(f)
        jobsDict: dict =jobsFile['jobs']
        if self.jobsFor in jobsDict.keys():
            jobs:list = jobsDict[self.jobsFor]
            for job in jobs:
                jobType, kwargs = job
                if jobType == "Get URL":
                    self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].addGetUrlJob(**kwargs)

    def initiateJobTypeOptions(self, selector):
        for key, value in JOP_TYPES.items():
            selector.addItem(value, key)

    def initiateIdentifierTypeOptions(self, selector):
        for key, value in IDENTIFIER_VALUES.items():
            selector.addItem(key, value)

    def initiateVariables(self):
        self.nextJobNumber = 2

    def connectActions(self):
        self.addJobButton.clicked.connect(self.addJobHandle)
        self.jobTypeSelector.currentTextChanged.connect(self.jobTypeChangedHandle)
        self.saveJobButton.clicked.connect(self.saveJobHandle)
        self.saveAllButton.clicked.connect(self.saveAllHandle)
        self.deleteJobButton.clicked.connect(self.deleteJobHandle)

    def saveAllHandle(self):
        print("Saving all jobs...")

    def saveJobHandle(self):       
        jobType = self.jobTypeSelector.currentText()
        identifierType = self.identifierTypeSelector.currentText() if self.identifierTypeSelector.isEnabled() else None
        identifierValue = self.identifierValueBox.text() if self.identifierValueBox.isEnabled() else None
        value = self.valueBox.text() if self.valueBox.isEnabled() else None
        if jobType == "Get URL":
            if not value.startswith(("http://","https://")):
                print("This is not a valid url")
            else:
                self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].addGetUrlJob(url=value, owner=self.jobsFor)

    def deleteJobHandle(self): 
        button = self.groupBox.sender()
        jobWidget = button.parent()
        jobWidget.deleteLater()

    def jobTypeChangedHandle(self, text):
        if text == "Get URL":
            self.identifierTypeSelector.setDisabled(True)
            self.identifierValueBox.setDisabled(True)
            self.valueBox.setDisabled(False)
        elif text == "Click Button":
            self.valueBox.setDisabled(True)
        else:
            self.valueBox.setDisabled(False)
            self.identifierValueBox.setDisabled(False)
            self.identifierTypeSelector.setDisabled(False)

    def addJobHandle(self):
        oneJob = QtWidgets.QWidget(self.jobsContainer)
        oneJob.setMinimumSize(QtCore.QSize(0, 0))
        oneJob.setObjectName("oneJob"+str(self.nextJobNumber))
        oneJobLayout = QtWidgets.QHBoxLayout(oneJob)
        oneJobLayout.setObjectName("oneJobLayout"+str(self.nextJobNumber))
        jobName = QtWidgets.QLabel(oneJob)
        jobName.setObjectName("jobName"+str(self.nextJobNumber))
        jobName.setMinimumSize(QtCore.QSize(40, 0))
        oneJobLayout.addWidget(jobName)
        jobTypeSelector = QtWidgets.QComboBox(oneJob)
        jobTypeSelector.setObjectName("jobTypeSelector"+str(self.nextJobNumber))
        self.initiateJobTypeOptions(jobTypeSelector)
        jobTypeSelector.setMinimumSize(QtCore.QSize(80, 0))
        jobTypeSelector.setMaximumSize(QtCore.QSize(80, 16777215))
        oneJobLayout.addWidget(jobTypeSelector)
        identifierTypeSelector = QtWidgets.QComboBox(oneJob)
        identifierTypeSelector.setObjectName("identifierTypeSelector"+str(self.nextJobNumber))
        identifierTypeSelector.setDisabled(True)
        identifierTypeSelector.setMinimumSize(QtCore.QSize(80, 0))
        identifierTypeSelector.setMaximumSize(QtCore.QSize(80, 16777215))
        self.initiateIdentifierTypeOptions(identifierTypeSelector)
        oneJobLayout.addWidget(identifierTypeSelector)
        identifierValueBox = QtWidgets.QLineEdit(oneJob)
        identifierValueBox.setObjectName("identifierValueBox"+str(self.nextJobNumber))
        identifierValueBox.setPlaceholderText("Identifier Value")
        identifierValueBox.setDisabled(True)
        oneJobLayout.addWidget(identifierValueBox)
        valueBox = QtWidgets.QLineEdit(oneJob)
        valueBox.setObjectName("valueBox"+str(self.nextJobNumber))
        valueBox.setPlaceholderText("Value")
        oneJobLayout.addWidget(valueBox)
        doneCheckBox = QtWidgets.QCheckBox(oneJob)
        doneCheckBox.setObjectName("doneCheckBox"+str(self.nextJobNumber))
        doneCheckBox.setEnabled(False)
        oneJobLayout.addWidget(doneCheckBox)
        saveJobButton = QtWidgets.QPushButton(oneJob)
        saveJobButton.setMaximumSize(QtCore.QSize(50, 16777215))
        saveJobButton.setObjectName("saveJobButton"+str(self.nextJobNumber))
        saveJobButton.setText("Save")
        def saveJobHandle():
            jobType = jobTypeSelector.currentText()
            identifierType = identifierTypeSelector.currentText() if identifierTypeSelector.isEnabled() else None
            identifierValue = identifierValueBox.text() if identifierValueBox.isEnabled() else None
            value = valueBox.text() if valueBox.isEnabled() else None
            if jobType == "Get URL":
                if not value.startswith(("http://","https://")):
                    print("This is not a valid url")
                else:
                    self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].addGetUrlJob(url=value, owner=self.jobsFor)
        saveJobButton.clicked.connect(saveJobHandle)
        oneJobLayout.addWidget(saveJobButton)
        deleteJobButton = QtWidgets.QPushButton(oneJob)
        deleteJobButton.setMaximumSize(QtCore.QSize(50, 16777215))
        deleteJobButton.setObjectName("deleteJobButton"+str(self.nextJobNumber)) 
        deleteJobButton.setText("Delete")
        def deleteJobHandle():
            self.jobsContainerLayout.removeWidget(oneJob)
            oneJob.deleteLater()
        deleteJobButton.clicked.connect(deleteJobHandle)
        oneJobLayout.addWidget(deleteJobButton)
        self.jobsContainerLayout.addWidget(oneJob)
        jobName.setText("Job " + str(self.nextJobNumber))
        self.nextJobNumber += 1
        def jobTypeChangedHandle(text):
            if text == "Get URL":
                identifierTypeSelector.setDisabled(True)
                identifierValueBox.setDisabled(True)
                valueBox.setDisabled(False)
            elif text == "Click Button":
                valueBox.setDisabled(True)
            else:
                valueBox.setDisabled(False)
                identifierValueBox.setDisabled(False)
                identifierTypeSelector.setDisabled(False)
        jobTypeSelector.currentTextChanged.connect(jobTypeChangedHandle)