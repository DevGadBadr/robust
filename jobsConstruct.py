from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt
from ui.uijobs import Ui_JobsDialog
from PyQt5.QtWidgets import QDialog, QGraphicsOpacityEffect
from scrapeJobsHelpers import JOB_TYPES, IDENTIFIER_VALUES
from jobContentConstruct import JobContentConstruct
import uuid
import json

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

    def setupUi(self, JobsDialog:QDialog, driverNumber):
        super().setupUi(JobsDialog)
        JobsDialog.setWindowFlags(JobsDialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        JobsDialog.setWindowFlags(JobsDialog.windowFlags() | Qt.WindowMinimizeButtonHint)
        JobsDialog.setWindowTitle(f"Driver {driverNumber} Jobs")
        self.statusLabel.setText(self.jobsFor)
        self.oneJob.deleteLater()
        self.initiateVariables()
        self.connectActions()
        self.initiateSavedJobs(self.scrapeJobClass.actions)
        # self.jobsContainer.setStyleSheet("QWidget#jobsContainer {border: 1px solid red;}")
        self.saveOrderButton.setGraphicsEffect(self.opaceEffect)
        
    def resetStatusLabel(self):
        if self.statusLabel:
            self.statusLabel.setText(self.jobsFor)
            self.resetLabelTimer.stop()
    
    def setStatusMessage(self, message):
        self.statusLabel.setText(message)
        if not self.resetLabelTimer.isActive():
            self.resetLabelTimer.start()

    def initiateSavedJobs(self, actions=None):
        if actions is None:
            return
        self.newjobflag = False
        for job in actions:
            kwargs = job[1]
            uuid = kwargs.get("uuid")
            self.nextsavedjobuuid = uuid
            self.initialActions.append(job)
            if kwargs.get("jobtype") == "GetUrl":
                url = kwargs.get("url")
                isexecuted = kwargs.get("isexecuted", False)
                self.addJobHandle()
                lastJobWidget = self.jobsGroupBox.findChild(QtWidgets.QWidget, "oneJob"+str(uuid))
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
                lastJobWidget = self.jobsGroupBox.findChild(QtWidgets.QWidget, "oneJob"+str(uuid))
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
                lastJobWidget = self.jobsGroupBox.findChild(QtWidgets.QWidget, "oneJob"+str(uuid))
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
            elif kwargs.get("jobtype") == "ExtractText":
                identifierType = kwargs.get("text_identifier")
                identifierValue = kwargs.get("identifier_value")
                isexecuted = kwargs.get("isexecuted", False)
                self.addJobHandle()
                lastJobWidget = self.jobsGroupBox.findChild(QtWidgets.QWidget, "oneJob"+str(uuid))
                lastJobWidget.setProperty("uuid", uuid)
                jobTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "jobTypeSelector"+str(uuid))
                jobTypeSelector.setCurrentText("Extract Text")
                identifierTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "identifierTypeSelector"+str(uuid))
                identifierTypeSelector.setCurrentIndex(identifierTypeSelector.findData(identifierType))
                identifierValueBox = lastJobWidget.findChild(QtWidgets.QLineEdit, "identifierValueBox"+str(uuid))
                identifierValueBox.setText(identifierValue)
                doneCheckBox = lastJobWidget.findChild(QtWidgets.QCheckBox, "doneCheckBox"+str(uuid))
                doneCheckBox.setChecked(isexecuted)
            elif kwargs.get("jobtype") == "ExtractLinks":
                identifierType = kwargs.get("link_identifier")
                identifierValue = kwargs.get("identifier_value")
                isexecuted = kwargs.get("isexecuted", False)
                self.addJobHandle()
                lastJobWidget = self.jobsGroupBox.findChild(QtWidgets.QWidget, "oneJob"+str(uuid))
                lastJobWidget.setProperty("uuid", uuid)
                jobTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "jobTypeSelector"+str(uuid))
                jobTypeSelector.setCurrentText("Extract Links")
                identifierTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "identifierTypeSelector"+str(uuid))
                identifierTypeSelector.setCurrentIndex(identifierTypeSelector.findData(identifierType))
                identifierValueBox = lastJobWidget.findChild(QtWidgets.QLineEdit, "identifierValueBox"+str(uuid))
                identifierValueBox.setText(identifierValue)
                doneCheckBox = lastJobWidget.findChild(QtWidgets.QCheckBox, "doneCheckBox"+str(uuid))
                doneCheckBox.setChecked(isexecuted)
        self.newjobflag = True

    def updateJobExecutionStatus(self, jobuuid, direction, result):
        if result == "End of actions":
            self.setStatusMessage("No more actions to execute.")
            return
        if result == "Previous Done":
            self.setStatusMessage("No more previous actions to execute.")
            return
        checkBox = self.jobsGroupBox.findChild(QtWidgets.QCheckBox, "doneCheckBox"+str(jobuuid))
        if checkBox:
            if direction == "forward":
                checkBox.setChecked(True)
            elif direction == "backward":
                checkBox.setChecked(False)  
        jobWidget = self.jobsGroupBox.findChild(QtWidgets.QWidget, "oneJob"+str(jobuuid))
        jobName = jobWidget.findChild(QtWidgets.QLabel)
        self.setStatusMessage(f"{jobName.text()} executed with result: {result}")

    def initiateJobTypeOptions(self, comboBox):
        for jobType in JOB_TYPES.values():
            comboBox.addItem(jobType)

    def initiateIdentifierTypeOptions(self, comboBox):
        for identifierType in IDENTIFIER_VALUES.keys():
            comboBox.addItem(identifierType, IDENTIFIER_VALUES[identifierType])

    def initiateVariables(self):
        self.nextJobNumber = 1
        self.newjobflag = True
        self.nextsavedjobuuid = None
        self.draggedJob = None
        self.previousDragPoint = 0
        self.currentJobs = []
        self.dragNextJob = None
        self.dragPreviousJob = None
        self.nextJobYLine = 0
        self.previousJobYLine = 0
        self.currentActions = []
        self.draggedAction = None
        self.dragUUID = None
        self.initialActions = []
        self.opaceEffect = QGraphicsOpacityEffect()     
        self.opaceEffect.setOpacity(0)
        self.jobContentDialog = None
        self.jobContentDialogClass = None

    def connectActions(self):
        self.addJobButton.clicked.connect(self.addJobHandle)
        self.saveOrderButton.clicked.connect(self.saveOrderHandle)
        self.deleteJobButton.clicked.connect(self.deleteJobHandle)
        self.nextButton.clicked.connect(self.executeNextAction)
        self.previousButton.clicked.connect(self.executePreviousAction)
        self.jobsContainer.mousePressEvent = self.handleJobPress
        self.jobsContainer.mouseMoveEvent = self.handleJobMove
        self.jobsContainer.mouseReleaseEvent = self.handleJobRelease

    def executeNextAction(self):
        func = self.scrapeJobClass.executeNextAction
        self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['threadQueue'].put((func, {}))

    def executePreviousAction(self):
        func = self.scrapeJobClass.executePreviousAction
        self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['threadQueue'].put((func, {}))

    def saveOrderHandle(self):
        self.setStatusMessage("Saving Order...")
        self.saveOrderButton.setEnabled(False)
        with open("./resources/jobs.json","r") as f:
            jobsFile = json.load(f)
        jobsDict:dict = jobsFile['jobs']
        jobs = jobsDict[self.jobsFor]
        for job in jobs:
            for action in self.currentActions:
                if job[1]['uuid'] == action[1]['uuid']:
                    job[1]['position'] = self.currentActions.index(action)
                    break
        with open("./resources/jobs.json",'w') as f:
            json.dump({"jobs": jobsDict} , f)
        jobsWidgets = [self.jobsContainerLayout.itemAt(i).widget() for i in range(self.jobsContainerLayout.count())]
        for index,jobWidget in enumerate(jobsWidgets):
            jobName = jobWidget.findChild(QtWidgets.QLabel)
            jobName.setText(f"Job {index+1}")
        self.initialActions = []
        for action in self.currentActions:
            self.initialActions.append(action)
        self.setStatusMessage("Current Order Saved")
        self.opaceEffect.setOpacity(0)
            
    def deleteJobHandle(self): 
        button = self.jobsGroupBox.sender()
        jobWidget = button.parent()
        jobWidget.deleteLater()
        jobuuid = jobWidget.property("uuid")
        self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].deleteJob(uuid=jobuuid, owner=self.jobsFor)

    def ensureArtifactButton(self, oneJob, oneJobLayout, jobUUID):
        existing = oneJob.findChild(QtWidgets.QPushButton, "artifactButton"+str(jobUUID))
        if existing:
            return
        artifactButton = QtWidgets.QPushButton(oneJob)
        artifactButton.setMaximumSize(QtCore.QSize(30, 16777215))
        artifactButton.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("./resources/document.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        artifactButton.setIcon(icon)
        artifactButton.setObjectName("artifactButton"+str(jobUUID))
        artifactButton.clicked.connect(self.openJobContentHandle)
        oneJobLayout.addWidget(artifactButton)

    def removeArtifactButton(self, oneJob, jobUUID):
        artifactButton = oneJob.findChild(QtWidgets.QPushButton, "artifactButton"+str(jobUUID))
        if artifactButton:
            artifactButton.deleteLater()

    def openJobContentHandle(self):
        button = self.jobsGroupBox.sender()
        jobWidget = button.parent()
        jobuuid = jobWidget.property("uuid")
        content = ""
        if jobuuid:
            for action in self.scrapeJobClass.actions:
                if action[1].get("uuid") == jobuuid:
                    artifact = action[1].get("artifact")
                    if isinstance(artifact, list):
                        content = "\n".join(artifact)
                    elif artifact:
                        content = artifact
                    else:
                        content = ""
                    break
        self.jobContentDialog = QDialog()
        self.jobContentDialogClass = JobContentConstruct(content)
        self.jobContentDialogClass.setupUi(self.jobContentDialog)
        self.jobContentDialog.show()

    def evaluateJobsOrderChange(self):
        if not self.currentActions == self.initialActions:
            self.opaceEffect.setOpacity(1)
            self.saveOrderButton.setEnabled(True)
        else:
            self.opaceEffect.setOpacity(0)
            self.saveOrderButton.setEnabled(False)

    def updateDragNextJob(self):
        draggedJobIndex = self.currentJobs.index(self.draggedJob)
        self.dragNextJob = self.currentJobs[draggedJobIndex+1] if (draggedJobIndex+1) < len(self.currentJobs) else None
        self.nextJobYLine = self.dragNextJob.pos().y() + self.dragNextJob.size().height() / 2 if self.dragNextJob else 0
    
    def updateDragPreviousJob(self):
        draggedJobIndex = self.currentJobs.index(self.draggedJob)
        self.dragPreviousJob = self.currentJobs[draggedJobIndex-1] if (draggedJobIndex-1) > -1 else None
        self.previousJobYLine = self.dragPreviousJob.pos().y() + self.dragPreviousJob.size().height() / 2 if self.dragPreviousJob else 0
    
    def handleJobPress(self, event):
        button = event.button()
        if button != Qt.LeftButton:
            return
        click_y = event.pos().y()
        self.currentJobs = [self.jobsContainerLayout.itemAt(i).widget() for i in range(self.jobsContainerLayout.count())]
        self.currentActions = self.scrapeJobClass.actions
        for job in self.currentJobs:
            job_y = job.pos().y()
            job_height = job.size().height()
            if job_y <= click_y <= job_y + job_height:
                jobName = job.findChild(QtWidgets.QLabel)
                jobName.setCursor(Qt.ClosedHandCursor)
                self.draggedJob = job
                self.dragUUID = job.property("uuid")
                for action in self.currentActions:
                    if action[1]['uuid'] == self.dragUUID:
                        self.draggedAction = action
                self.updateDragNextJob()
                self.updateDragPreviousJob()
                self.draggedJob.raise_()
                self.originalPos = self.draggedJob.pos()
                break

    def handleJobMove(self, event):
        if len(self.currentActions) < len(self.currentJobs):
            self.setStatusMessage("Save New Jobs First To Reorder")
            return
        drag_y = event.pos().y()
        direction = (drag_y - self.previousDragPoint) > 0 # True for down move
        current_pos = self.draggedJob.pos()
        self.draggedJob.move(current_pos.x(), drag_y - self.draggedJob.height() // 2)
        if direction:
            if not self.dragNextJob:
                self.previousDragPoint = drag_y
                return
            if drag_y > self.nextJobYLine:
                newIndex = self.currentJobs.index(self.dragNextJob)
                self.jobsContainerLayout.insertWidget(newIndex, self.draggedJob)
                self.currentActions.pop(self.currentActions.index(self.draggedAction))
                self.currentActions.insert(newIndex, self.draggedAction)
                self.currentJobs = [self.jobsContainerLayout.itemAt(i).widget() for i in range(self.jobsContainerLayout.count())]
                self.jobsContainerLayout.activate()
                self.updateDragNextJob()
                self.updateDragPreviousJob()
                self.evaluateJobsOrderChange()
        else:
            if not self.dragPreviousJob:
                self.previousDragPoint = drag_y
                return
            if drag_y < self.previousJobYLine:
                newIndex = self.currentJobs.index(self.dragPreviousJob)
                self.jobsContainerLayout.insertWidget(newIndex, self.draggedJob)
                self.currentActions.pop(self.currentActions.index(self.draggedAction))
                self.currentActions.insert(newIndex, self.draggedAction)
                self.currentJobs = [self.jobsContainerLayout.itemAt(i).widget() for i in range(self.jobsContainerLayout.count())]
                self.jobsContainerLayout.activate()
                self.updateDragNextJob()
                self.updateDragPreviousJob()
                self.evaluateJobsOrderChange()
        self.previousDragPoint = drag_y
            
    def handleJobRelease(self, event):
        button = event.button()
        if button != Qt.LeftButton:
            return
        jobs = self.jobsGroupBox.findChildren(QtWidgets.QWidget, QtCore.QRegExp("oneJob.*"))
        for job in jobs:
            jobName = job.findChild(QtWidgets.QLabel)
            jobName.setCursor(Qt.OpenHandCursor)
        idx = self.currentJobs.index(self.draggedJob)
        self.jobsContainerLayout.insertWidget(idx, self.draggedJob)

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
        # jobName.setStyleSheet("border:1px solid red;")
        jobName.setObjectName("jobName"+str(newJobUUID))
        jobName.setMinimumSize(QtCore.QSize(40, 30))
        jobName.setCursor(Qt.OpenHandCursor)
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
            elif jobType == "Extract Text":
                if not identifierType or not identifierValue:
                    self.setStatusMessage("Please fill in all required fields for Extract Text job.")
                    return
                else:
                    oneJob.setProperty("uuid", newJobUUID)
                    doneCheckBox.setObjectName("doneCheckBox"+str(newJobUUID))
                    saveMsg = self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].addExtractTextJob(text_identifier=identifierType, identifier_value=identifierValue, owner=self.jobsFor, uuid=newJobUUID)
                    self.setStatusMessage(saveMsg)
            elif jobType == "Extract Links":
                if not identifierType or not identifierValue:
                    self.setStatusMessage("Please fill in all required fields for Extract Links job.")
                    return
                else:
                    oneJob.setProperty("uuid", newJobUUID)
                    doneCheckBox.setObjectName("doneCheckBox"+str(newJobUUID))
                    saveMsg = self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].addExtractLinksJob(link_identifier=identifierType, identifier_value=identifierValue, owner=self.jobsFor, uuid=newJobUUID)
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
                self.removeArtifactButton(oneJob, newJobUUID)
            elif text == "Click Button":
                valueBox.setDisabled(True)
                identifierTypeSelector.setDisabled(False)
                identifierValueBox.setDisabled(False)
                self.removeArtifactButton(oneJob, newJobUUID)
            elif text == "Extract Text" or text == "Extract Links":
                valueBox.setDisabled(True)
                identifierTypeSelector.setDisabled(False)
                identifierValueBox.setDisabled(False)
                self.ensureArtifactButton(oneJob, oneJobLayout, newJobUUID)
            else:
                valueBox.setDisabled(False)
                identifierValueBox.setDisabled(False)
                identifierTypeSelector.setDisabled(False)
                self.removeArtifactButton(oneJob, newJobUUID)
        jobTypeSelector.currentTextChanged.connect(jobTypeChangedHandle)
