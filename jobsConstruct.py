from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt
from uijobs import Ui_JobsDialog
from PyQt5.QtWidgets import QDialog
from scrapeJobsHelpers import JOP_TYPES, IDENTIFIER_VALUES
import json
import uuid

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
        self.oneJob.deleteLater()
        self.initiateVariables()
        self.connectActions()
        self.initiateJobTypeOptions(self.jobTypeSelector)
        self.initiateIdentifierTypeOptions(self.identifierTypeSelector)
        self.initiateSavedJobs(self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].actions)

    def initiateSavedJobs(self, actions=None):
        if actions is None:
            return
        for job in actions:
            kwargs = job[1]
            if kwargs.get("jobtype") == "GetUrl":
                url = kwargs.get("url")
                uuid = kwargs.get("uuid")
                isexecuted = kwargs.get("isexecuted", False)
                self.addJobHandle()
                print("Initiating saved job with url: " + url)
                lastJobWidget = self.groupBox.findChild(QtWidgets.QWidget, "oneJob"+str(self.nextJobNumber-1))
                lastJobWidget.setProperty("uuid", uuid)
                print(lastJobWidget.objectName())
                jobTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "jobTypeSelector"+str(self.nextJobNumber-1))
                jobTypeSelector.setCurrentText("Get URL")
                valueBox = lastJobWidget.findChild(QtWidgets.QLineEdit, "valueBox"+str(self.nextJobNumber-1))
                valueBox.setText(url)
                doneCheckBox = lastJobWidget.findChild(QtWidgets.QCheckBox, "doneCheckBox"+str(self.nextJobNumber-1))
                doneCheckBox.setChecked(isexecuted)
                doneCheckBox.setObjectName("doneCheckBox"+str(uuid))

    def updateJobExecutionStatus(self, jobuuid, direction):
        checkBox = self.groupBox.findChild(QtWidgets.QCheckBox, "doneCheckBox"+str(jobuuid))
        if checkBox:
            if direction == "forward":
                checkBox.setChecked(True)
            elif direction == "backward":
                checkBox.setChecked(False)  

    def initiateJobTypeOptions(self, comboBox):
        for jobType in JOP_TYPES.values():
            comboBox.addItem(jobType)

    def initiateIdentifierTypeOptions(self, comboBox):
        for identifierType in IDENTIFIER_VALUES.keys():
            comboBox.addItem(identifierType)

    def initiateVariables(self):
        self.nextJobNumber = 1

    def connectActions(self):
        self.addJobButton.clicked.connect(self.addJobHandle)
        self.jobTypeSelector.currentTextChanged.connect(self.jobTypeChangedHandle)
        self.saveAllButton.clicked.connect(self.saveAllHandle)
        self.deleteJobButton.clicked.connect(self.deleteJobHandle)

    def saveAllHandle(self):
        print("Saving all jobs...")

    def deleteJobHandle(self): 
        button = self.groupBox.sender()
        jobWidget = button.parent()
        jobWidget.deleteLater()
        jobuuid = jobWidget.property("uuid")
        self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].deleteJob(uuid=jobuuid, owner=self.jobsFor)

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
                    jobuuid = str(uuid.uuid4())
                    oneJob.setProperty("uuid", jobuuid)
                    doneCheckBox.setObjectName("doneCheckBox"+str(jobuuid))
                    self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].addGetUrlJob(url=value, owner=self.jobsFor, uuid=jobuuid)
        saveJobButton.clicked.connect(saveJobHandle)
        oneJobLayout.addWidget(saveJobButton)
        deleteJobButton = QtWidgets.QPushButton(oneJob)
        deleteJobButton.setMaximumSize(QtCore.QSize(50, 16777215))
        deleteJobButton.setObjectName("deleteJobButton"+str(self.nextJobNumber)) 
        deleteJobButton.setText("Delete")
        deleteJobButton.clicked.connect(self.deleteJobHandle)
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