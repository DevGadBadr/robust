from ui.uinewjob import Ui_NewJobDialog
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
import json
import uuid

class NewJobConstruct(Ui_NewJobDialog):
    def __init__(self):
        super().__init__()
        self.resetStatusTimer = QtCore.QTimer()
        self.resetStatusTimer.timeout.connect(self.clearStatus)

    def setupUi(self, NewJobDialog):
        super().setupUi(NewJobDialog)
        NewJobDialog.setWindowFlags(NewJobDialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        NewJobDialog.setWindowFlags(NewJobDialog.windowFlags() | Qt.WindowMinimizeButtonHint)
        NewJobDialog.setWindowTitle(f"Add New Job")
        self.initaleConfigs()
        self.initiateExistingJobs()
        self.connectActions()

    def initaleConfigs(self):
        self.urlField.setEnabled(False)
        self.urlLabel.setEnabled(False)

    def initiateExistingJobs(self):
        with open("./resources/jobs.json", "r") as f:
            self.existingJobs = json.load(f)
        self.existingJobsList = []
        for job in self.existingJobs['jobs'].keys():
            self.existingJobsList.append(job)
        for job in self.existingJobsList:
            self.existJobsArea.append(job)

    def connectActions(self):
        self.initialJobCheckBox.stateChanged.connect(self.handleInitialJobCheckboxChange)
        self.cancelButton.clicked.connect(self.handleCancelButton)
        self.addButotn.clicked.connect(self.handleSaveButton)

    def handleInitialJobCheckboxChange(self, state):
        print(f"Initial Job Checkbox State Changed: {state}")
        isChecked = state == Qt.Checked
        if isChecked:
            self.urlField.setEnabled(True)
            self.urlLabel.setEnabled(True)
        else:
            self.urlField.setEnabled(False)
            self.urlLabel.setEnabled(False)

    def clearStatus(self):
        self.newJobStatusLabel.setText("Add New Job")
        self.resetStatusTimer.stop()

    def setStatus(self, message):
        self.newJobStatusLabel.setText(message)
        self.resetStatusTimer.start(3000)

    def handleCancelButton(self):
        self.parent().close()

    def handleSaveButton(self):
        jobName = self.jobNameField.text().strip()
        if not jobName:
            self.setStatus("Please enter a job name.")
            return
        if jobName in self.existingJobsList:
            self.setStatus("Job name already exists. Please choose a different name.")
            return
        isInitialJob = self.initialJobCheckBox.isChecked()
        initialjobs = []
        if isInitialJob:
            url = self.urlField.text().strip()
            if not url.startswith(("http://", "https://")):
                self.setStatus("Please enter a valid URL starting with http or https.")
                return
            job = ["GetUrl", {"url": url, "position":0, "uuid": str(uuid.uuid4()), "jobType":"GetUrl"}]
            initialjobs.append(job)
        with open("./resources/jobs.json", "r") as f:
            jobsData = json.load(f)
        jobsData['jobs'][jobName] = initialjobs
        with open("./resources/jobs.json", "w") as f:
            json.dump(jobsData, f)
        self.setStatus("Job saved successfully!")
        self.existingJobsList.append(jobName)
        self.existJobsArea.append(jobName)