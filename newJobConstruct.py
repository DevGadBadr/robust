from ui.uinewjob import Ui_NewJobDialog
from ui.manageTheme import applyTitlebarToWidget
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
import json
import uuid

class NewJobConstruct(Ui_NewJobDialog):
    def __init__(self, robustClass):
        super().__init__()
        self.robustClass = robustClass
        self.resetStatusTimer = QtCore.QTimer()
        self.resetStatusTimer.timeout.connect(self.clearStatus)

    def setupUi(self, NewJobDialog):
        super().setupUi(NewJobDialog)
        NewJobDialog.setWindowFlags(NewJobDialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        NewJobDialog.setWindowFlags(NewJobDialog.windowFlags() | Qt.WindowMinimizeButtonHint)
        NewJobDialog.setWindowTitle(f"Add New Job")
        applyTitlebarToWidget(NewJobDialog)
        self.dialog = NewJobDialog
        self.initialConfigs()
        self.initiateVariables()
        self.initiateExistingJobs()
        self.connectActions()

    def initiateVariables(self):
        self.selectedJobName = None
        self.existingJobs = {}

    def initialConfigs(self):
        self.urlField.setEnabled(False)
        self.urlLabel.setEnabled(False)
        self.removeButton.setEnabled(False)

    def initiateExistingJobs(self):
        with open("./resources/jobs.json", "r") as f:
            self.existingJobs = json.load(f)
        for job in self.existingJobs['jobs'].keys():
            item = QtWidgets.QListWidgetItem(job)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.existJobsList.blockSignals(True)
            self.existJobsList.addItem(item)
            self.existJobsList.blockSignals(False)

    def connectActions(self):
        self.existJobsList.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self.initialJobCheckBox.stateChanged.connect(self.handleInitialJobCheckboxChange)
        self.cancelButton.clicked.connect(self.handleCancelButton)
        self.addButton.clicked.connect(self.handleSaveButton)
        self.existJobsList.itemClicked.connect(self.handleExistJobClicked)
        self.existJobsList.itemChanged.connect(self.handleExistJobChanged)
        self.removeButton.clicked.connect(self.handleRemoveButton)
        self.eraseJobName.clicked.connect(lambda: self.jobNameField.clear())
        self.eraseUrl.clicked.connect(lambda: self.urlField.clear())

    def handleExistJobChanged(self, item):
        newItemText = item.text().strip()
        if not newItemText:
            self.setStatus("Job name cannot be empty.")
            self.existJobsList.blockSignals(True)
            item.setText(self.selectedJobName)
            self.existJobsList.blockSignals(False)
            return
        if newItemText in [self.existJobsList.item(i).text() for i in range(self.existJobsList.count()) if self.existJobsList.item(i) != item]:
            self.setStatus(f"Job {newItemText} already exists. Please choose a different name.")
            return
        self.existingJobs['jobs'][newItemText] = self.existingJobs['jobs'].pop(self.selectedJobName)
        with open("./resources/jobs.json", "w") as f:
            json.dump(self.existingJobs, f)
        mainBoxItemIndex = self.robustClass.mainDefaultBox.findText(self.selectedJobName)
        if mainBoxItemIndex >= 0:
            self.robustClass.mainDefaultBox.setItemText(mainBoxItemIndex, newItemText)
        driverInstancesComboBoxes = [self.robustClass.instancesContainerLayout.itemAt(i).widget().findChild(QtWidgets.QComboBox) for i in range(self.robustClass.instancesContainerLayout.count())]
        for comboBox in driverInstancesComboBoxes:
            itemIndex = comboBox.findText(self.selectedJobName)
            if itemIndex >= 0:
                # A rename is not a job change, so it must not rebuild the driver's actions.
                comboBox.blockSignals(True)
                comboBox.setItemText(itemIndex, newItemText)
                comboBox.blockSignals(False)
        self.robustClass.handleScrapeJobRenamed(self.selectedJobName, newItemText)
        self.selectedJobName = newItemText
        self.setStatus(f"Job renamed to {newItemText} successfully.")
        
    def handleRemoveButton(self):
        if not self.selectedJobName:
            self.setStatus("No job selected to remove.")
            return
        scrapeJobActions = self.robustClass.getActionsForScrapeJob(self.selectedJobName)
        if scrapeJobActions:
            self.setStatus(f"Cannot remove {self.selectedJobName} because it has {len(scrapeJobActions)} jobs")
            return
        del self.existingJobs['jobs'][self.selectedJobName]
        with open("./resources/jobs.json", "w") as f:
            json.dump(self.existingJobs, f)
        for i in range(self.robustClass.mainDefaultBox.count()):
            if self.robustClass.mainDefaultBox.itemText(i) == self.selectedJobName:
                self.robustClass.mainDefaultBox.removeItem(i)
                break
        driverInstancesComboBoxes = [self.robustClass.instancesContainerLayout.itemAt(i).widget().findChild(QtWidgets.QComboBox) for i in range(self.robustClass.instancesContainerLayout.count())]
        for comboBox in driverInstancesComboBoxes:
            for i in range(comboBox.count()):
                if comboBox.itemText(i) == self.selectedJobName:
                    comboBox.blockSignals(True)
                    comboBox.removeItem(i)
                    comboBox.blockSignals(False)
                    break
        self.robustClass.handleScrapeJobRemoved(self.selectedJobName)
        self.existJobsList.takeItem(self.existJobsList.row(self.existJobsList.findItems(self.selectedJobName, Qt.MatchExactly)[0]))
        self.setStatus(f"Job {self.selectedJobName} removed successfully.")
        self.removeButton.setEnabled(False)

    def handleExistJobClicked(self, item):
        self.selectedJobName = item.text()
        print(f"Selected Job: {self.selectedJobName}")
        self.removeButton.setEnabled(True)

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
        self.dialog.close()

    def handleSaveButton(self):
        jobName = self.jobNameField.text().strip()
        if not jobName:
            self.setStatus("Please enter a job name.")
            return
        if jobName in [self.existJobsList.item(i).text() for i in range(self.existJobsList.count())]:
            self.setStatus("Job name already exists. Please choose a different name.")
            return
        isInitialJob = self.initialJobCheckBox.isChecked()
        initialjobs = []
        if isInitialJob:
            url = self.urlField.text().strip()
            if not url.startswith(("http://", "https://")):
                self.setStatus("Please enter a valid URL starting with http or https.")
                return
            job = ["GetUrl", {"url": url, "position":0, "uuid": str(uuid.uuid4()), "jobtype":"GetUrl"}]
            initialjobs.append(job)
        with open("./resources/jobs.json", "r") as f:
            jobsData = json.load(f)
        jobsData['jobs'][jobName] = initialjobs
        with open("./resources/jobs.json", "w") as f:
            json.dump(jobsData, f)
        self.setStatus("Job saved successfully!")
        item = QtWidgets.QListWidgetItem(jobName)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.existJobsList.blockSignals(True)
        self.existJobsList.addItem(item)
        self.existJobsList.blockSignals(False)
        self.existingJobs['jobs'][jobName] = initialjobs
        self.isAddingNewJob = False
        self.robustClass.mainDefaultBox.addItem(jobName)
        driverInstancesComboBoxes = [self.robustClass.instancesContainerLayout.itemAt(i).widget().findChild(QtWidgets.QComboBox) for i in range(self.robustClass.instancesContainerLayout.count())]
        for comboBox in driverInstancesComboBoxes:
            comboBox.addItem(jobName)
        self.robustClass.existJobs.append(jobName)