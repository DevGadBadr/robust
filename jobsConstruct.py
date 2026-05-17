from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt
from uijobs import Ui_JobsDialog
from PyQt5.QtWidgets import QDialog
from scrapeJobsHelpers import JOP_TYPES, IDENTIFIER_VALUES
import uuid

class JobsConstruct(Ui_JobsDialog):

    def __init__(self, robustClass, jobsFor, scrapeuuid):
        super().__init__()
        self.scrapeJobClass = robustClass.worker.driverManager.drivers[scrapeuuid]['scrapeJobClass']
        self.robustClass = robustClass
        self.jobsFor = jobsFor
        self.scrapeuuid = scrapeuuid
        self.resetLabelTimer = QtCore.QTimer()
        self.resetLabelTimer.setInterval(1500)  # Reset label after 3 seconds
        self.resetLabelTimer.timeout.connect(self.resetStatusLabel)

    def resetStatusLabel(self):
        self.statusLabel.setText(self.jobsFor)
        self.resetLabelTimer.stop()
    
    def setStatusMessage(self, message):
        self.statusLabel.setText(message)
        if not self.resetLabelTimer.isActive():
            self.resetLabelTimer.start()

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
        self.newjobflag = False
        for job in actions:
            kwargs = job[1]
            uuid = kwargs.get("uuid")
            self.nextsavedjobuuid = uuid
            if kwargs.get("jobtype") == "GetUrl":
                url = kwargs.get("url")
                isexecuted = kwargs.get("isexecuted", False)
                self.addJobHandle()
                lastJobWidget = self.groupBox.findChild(QtWidgets.QWidget, "oneJob"+str(uuid))
                lastJobWidget.setProperty("uuid", uuid)
                jobTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "jobTypeSelector"+str(uuid))
                jobTypeSelector.setCurrentText("Get URL")
                valueBox = lastJobWidget.findChild(QtWidgets.QLineEdit, "valueBox"+str(uuid))
                valueBox.setText(url)
                doneCheckBox = lastJobWidget.findChild(QtWidgets.QCheckBox, "doneCheckBox"+str(uuid))
                doneCheckBox.setChecked(isexecuted)
            elif kwargs.get("jobtype") == "ClickButton":
                identifierType = kwargs.get("button_identifier")
                identifierValue = kwargs.get("identifier_value")
                isexecuted = kwargs.get("isexecuted", False)
                self.addJobHandle()
                lastJobWidget = self.groupBox.findChild(QtWidgets.QWidget, "oneJob"+str(uuid))
                lastJobWidget.setProperty("uuid", uuid)
                jobTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "jobTypeSelector"+str(uuid))
                jobTypeSelector.setCurrentText("Click Button")
                identifierTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "identifierTypeSelector"+str(uuid))
                identifierTypeSelector.setCurrentIndex(identifierTypeSelector.findData(identifierType))
                identifierValueBox = lastJobWidget.findChild(QtWidgets.QLineEdit, "identifierValueBox"+str(uuid))
                identifierValueBox.setText(identifierValue)
                doneCheckBox = lastJobWidget.findChild(QtWidgets.QCheckBox, "doneCheckBox"+str(uuid))
                doneCheckBox.setChecked(isexecuted)
            elif kwargs.get("jobtype") == "InputField":
                identifierType = kwargs.get("field_identifier")
                identifierValue = kwargs.get("identifier_value")
                value = kwargs.get("value")
                isexecuted = kwargs.get("isexecuted", False)
                self.addJobHandle()
                lastJobWidget = self.groupBox.findChild(QtWidgets.QWidget, "oneJob"+str(uuid))
                lastJobWidget.setProperty("uuid", uuid)
                jobTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "jobTypeSelector"+str(uuid))
                jobTypeSelector.setCurrentText("Input Field")
                identifierTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "identifierTypeSelector"+str(uuid))
                identifierTypeSelector.setCurrentIndex(identifierTypeSelector.findData(identifierType))
                identifierValueBox = lastJobWidget.findChild(QtWidgets.QLineEdit, "identifierValueBox"+str(uuid))
                identifierValueBox.setText(identifierValue)
                valueBox = lastJobWidget.findChild(QtWidgets.QLineEdit, "valueBox"+str(uuid))
                valueBox.setText(value)
                doneCheckBox = lastJobWidget.findChild(QtWidgets.QCheckBox, "doneCheckBox"+str(uuid))
                doneCheckBox.setChecked(isexecuted)
                doneCheckBox.setObjectName("doneCheckBox"+str(uuid))
        self.newjobflag = True

    def updateJobExecutionStatus(self, jobuuid, direction, result):
        if result == "End of actions":
            self.setStatusMessage("No more actions to execute.")
            return
        checkBox = self.groupBox.findChild(QtWidgets.QCheckBox, "doneCheckBox"+str(jobuuid))
        if checkBox:
            if direction == "forward":
                checkBox.setChecked(True)
            elif direction == "backward":
                checkBox.setChecked(False)  
        jobWidget = self.groupBox.findChild(QtWidgets.QWidget, "oneJob"+str(jobuuid))
        jobName = jobWidget.findChild(QtWidgets.QLabel)
        self.setStatusMessage(f"{jobName.text()} executed with result: {result}")

    def initiateJobTypeOptions(self, comboBox):
        for jobType in JOP_TYPES.values():
            comboBox.addItem(jobType)

    def initiateIdentifierTypeOptions(self, comboBox):
        for identifierType in IDENTIFIER_VALUES.keys():
            comboBox.addItem(identifierType, IDENTIFIER_VALUES[identifierType])

    def initiateVariables(self):
        self.nextJobNumber = 1
        self.newjobflag = True
        self.nextsavedjobuuid = None

    def connectActions(self):
        self.addJobButton.clicked.connect(self.addJobHandle)
        self.jobTypeSelector.currentTextChanged.connect(self.jobTypeChangedHandle)
        self.saveAllButton.clicked.connect(self.saveAllHandle)
        self.deleteJobButton.clicked.connect(self.deleteJobHandle)
        self.nextButton.clicked.connect(self.executeNextAction)
        self.previousButton.clicked.connect(self.executePreviousAction)

    def executeNextAction(self):
        func = self.scrapeJobClass.executeNextAction
        self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['threadQueue'].put((func, {}))

    def executePreviousAction(self):
        func = self.scrapeJobClass.executePreviousAction
        self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['threadQueue'].put((func, {}))

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
        if self.newjobflag:
            newJobUUID = str(uuid.uuid4())
        else:
            newJobUUID = self.nextsavedjobuuid
        oneJob = QtWidgets.QWidget(self.jobsContainer)
        oneJob.setMinimumSize(QtCore.QSize(0, 0))
        oneJob.setObjectName("oneJob"+str(newJobUUID))
        oneJobLayout = QtWidgets.QHBoxLayout(oneJob)
        oneJobLayout.setObjectName("oneJobLayout"+newJobUUID)
        jobName = QtWidgets.QLabel(oneJob)
        jobName.setObjectName("jobName"+str(newJobUUID))
        jobName.setMinimumSize(QtCore.QSize(40, 0))
        oneJobLayout.addWidget(jobName)
        jobTypeSelector = QtWidgets.QComboBox(oneJob)
        jobTypeSelector.setObjectName("jobTypeSelector"+str(newJobUUID))
        self.initiateJobTypeOptions(jobTypeSelector)
        jobTypeSelector.setMinimumSize(QtCore.QSize(80, 0))
        jobTypeSelector.setMaximumSize(QtCore.QSize(80, 16777215))
        oneJobLayout.addWidget(jobTypeSelector)
        identifierTypeSelector = QtWidgets.QComboBox(oneJob)
        identifierTypeSelector.setObjectName("identifierTypeSelector"+str(newJobUUID))
        identifierTypeSelector.setDisabled(True)
        identifierTypeSelector.setMinimumSize(QtCore.QSize(80, 0))
        identifierTypeSelector.setMaximumSize(QtCore.QSize(80, 16777215))
        self.initiateIdentifierTypeOptions(identifierTypeSelector)
        oneJobLayout.addWidget(identifierTypeSelector)
        identifierValueBox = QtWidgets.QLineEdit(oneJob)
        identifierValueBox.setObjectName("identifierValueBox"+str(newJobUUID))
        identifierValueBox.setPlaceholderText("Identifier Value")
        identifierValueBox.setDisabled(True)
        oneJobLayout.addWidget(identifierValueBox)
        valueBox = QtWidgets.QLineEdit(oneJob)
        valueBox.setObjectName("valueBox"+str(newJobUUID))
        valueBox.setPlaceholderText("Value")
        oneJobLayout.addWidget(valueBox)
        doneCheckBox = QtWidgets.QCheckBox(oneJob)
        doneCheckBox.setObjectName("doneCheckBox"+str(newJobUUID))
        doneCheckBox.setEnabled(False)
        oneJobLayout.addWidget(doneCheckBox)
        saveJobButton = QtWidgets.QPushButton(oneJob)
        saveJobButton.setMaximumSize(QtCore.QSize(50, 16777215))
        saveJobButton.setObjectName("saveJobButton"+str(newJobUUID))
        saveJobButton.setText("Save")
        def saveJobHandle():
            jobType = jobTypeSelector.currentText()
            identifierType = identifierTypeSelector.currentData() if identifierTypeSelector.isEnabled() else None
            identifierValue = identifierValueBox.text() if identifierValueBox.isEnabled() else None
            value = valueBox.text() if valueBox.isEnabled() else None
            if jobType == "Get URL":
                if not value.startswith(("http://","https://")):
                    self.setStatusMessage("Invalid URL format. Please include http:// or https://")
                    return
                else:
                    oneJob.setProperty("uuid", newJobUUID)
                    doneCheckBox.setObjectName("doneCheckBox"+str(newJobUUID))
                    saveMsg = self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].addGetUrlJob(url=value, owner=self.jobsFor, uuid=newJobUUID)
                    self.setStatusMessage(saveMsg)
            elif jobType == "Click Button":
                if not identifierType or not identifierValue:
                    self.setStatusMessage("Please fill in all required fields for Click Button job.")
                    return
                else:
                    oneJob.setProperty("uuid", newJobUUID)
                    doneCheckBox.setObjectName("doneCheckBox"+str(newJobUUID))
                    saveMsg = self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].addClickButtonJob(button_identifier=identifierType, identifier_value=identifierValue, owner=self.jobsFor, uuid=newJobUUID)
                    self.setStatusMessage(saveMsg)
            elif jobType == "Input Field":
                if not identifierType or not identifierValue or not value:
                    self.setStatusMessage("Please fill in all required fields for Input Field job.")
                    return
                else:
                    oneJob.setProperty("uuid", newJobUUID)
                    doneCheckBox.setObjectName("doneCheckBox"+str(newJobUUID))
                    saveMsg = self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].addInputFieldJob(field_identifier=identifierType, identifier_value=identifierValue, value=value, owner=self.jobsFor, uuid=newJobUUID)
                    self.setStatusMessage(saveMsg)
        saveJobButton.clicked.connect(saveJobHandle)
        oneJobLayout.addWidget(saveJobButton)
        deleteJobButton = QtWidgets.QPushButton(oneJob)
        deleteJobButton.setMaximumSize(QtCore.QSize(50, 16777215))
        deleteJobButton.setObjectName("deleteJobButton"+str(newJobUUID)) 
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
                identifierTypeSelector.setDisabled(False)
                identifierValueBox.setDisabled(False)
            else:
                valueBox.setDisabled(False)
                identifierValueBox.setDisabled(False)
                identifierTypeSelector.setDisabled(False)
        jobTypeSelector.currentTextChanged.connect(jobTypeChangedHandle)