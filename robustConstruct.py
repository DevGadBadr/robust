import json

from PyQt5 import QtWidgets
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QDialog
from scrapeJobsHelpers import clickButtonJob, getUrlJob, inputFieldJob
from ui.uirobust import Ui_RobustDialog
from newJobConstruct import NewJobConstruct
from jobsConstruct import JobsConstruct
from PyQt5.QtCore import QTimer, Qt
from workerThread import QWorker
from collections import deque
from scrapeJobs import abstractScrapeJob
from elementSetup import setUpMiddleLine
import win32gui
import win32con

class RobustConstruct(Ui_RobustDialog):

    def __init__(self):
        super().__init__()
        self.uiUpdateQueue = deque()
        self.uiUpdateTimer = QTimer()
        self.uiUpdateTimer.setInterval(50)
        self.uiUpdateTimer.timeout.connect(self.processNextUiUpdate)

    def setupUi(self, RobustDialog:QDialog):
        super().setupUi(RobustDialog)
        RobustDialog.setWindowFlags(RobustDialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        RobustDialog.setWindowFlags(RobustDialog.windowFlags() | Qt.WindowMinimizeButtonHint)
        RobustDialog.closeEvent = self.closeEvent
        self.driverInstancePlaceHolder.deleteLater()
        self.initiateVariables()
        self.connectActions()
        self.initiateWorker()
        self.loadExistingJobs()
        self.modifyMainDefaultBox()
        self.loadSettings()
        setUpMiddleLine(self.middleLine1, self)
        self.startButton.click()

    def loadExistingJobs(self):
        with open("./resources/jobs.json", "r") as f:
            existingJobs = json.load(f)
        self.existJobs = []
        for job in existingJobs['jobs'].keys():
            self.existJobs.append(job)

    def loadSettings(self):
        with open("./resources/settings.json","r") as f:
            settingsFile = json.load(f)
        if settingsFile.get("isHidden", False):
            self.headlessCheckbox.setChecked(True)
        if settingsFile.get("isVisible", False):
            self.hiddenCheckBox.setChecked(True)

    def modifyMainDefaultBox(self):
        self.mainDefaultBox.clear()
        for job in self.existJobs:
            self.mainDefaultBox.addItem(job)

    def initiateVariables(self):
        self.numberOfDrivers = 1
        self.nextDriverNumber = 1
        self.nextReadyDriverNumber = 1
        self.nextDriverCount = 1
        self.addNewJobDialog = None

    def connectActions(self):
        self.slider.valueChanged.connect(self.castSliderChange)
        self.startButton.clicked.connect(self.createDrivers)
        self.executeAllButton.clicked.connect(self.executeAllDrivers)
        self.headlessCheckbox.stateChanged.connect(self.handleHeadlessCheckboxChange)
        self.hiddenCheckBox.stateChanged.connect(self.handleHiddenCheckboxChange)
        self.addScrapeJobButton.clicked.connect(self.openAddJobDialog)

    def openAddJobDialog(self):
        self.addNewJobDialog = QDialog()
        self.newJobDialogClass = NewJobConstruct(self)
        self.newJobDialogClass.setupUi(self.addNewJobDialog)
        self.addNewJobDialog.show()

    def handleHiddenCheckboxChange(self, state):
        isVisible = state == Qt.Checked
        with open("./resources/settings.json","r") as f:
            settingsFile = json.load(f)
        settingsFile["isVisible"] = isVisible
        with open("./resources/settings.json","w") as f:
            json.dump(settingsFile, f)

    def handleHeadlessCheckboxChange(self, state):
        isHidden = state == Qt.Checked
        with open("./resources/settings.json","r") as f:
            settingsFile = json.load(f)
        settingsFile["isHidden"] = isHidden
        with open("./resources/settings.json","w") as f:
            json.dump(settingsFile, f)

    def castSliderChange(self, value):
        self.driverCountLabel.setText(str(value))
        self.numberOfDrivers = value

    def initiateWorker(self):
        self.worker = QWorker()
        self.worker.driverManager.finished.connect(self.QThreadFinished)
        self.worker.driverManager.status.connect(self.handleQThreadStatus)
        self.closeAllButton.clicked.connect(self.closeAllDrivers)

    def createDrivers(self):
        self.startButton.setDisabled(True)
        self.closeAllButton.setDisabled(True)
        self.executeAllButton.setDisabled(True)
        self.worker.run(self.numberOfDrivers, self.headlessCheckbox.isChecked(), self.hiddenCheckBox.isChecked())
        currentInstances = len([driver for driver in self.worker.driverManager.drivers.values() if not driver['dropped']])
        self.nextDriverCount = currentInstances + 1

    def getActionsForScrapeJob(self, defaultScrapeJob):
        with open("./resources/jobs.json","r") as f:
            jobsFile = json.load(f)
        jobsDict: dict =jobsFile['jobs']
        actions = []
        if defaultScrapeJob in jobsDict.keys():
            jobs:list = jobsDict[defaultScrapeJob]
            for job in jobs:
                jobType, kwargs = job
                kwargs["isexecuted"] = False
                jobPosition = kwargs['position']
                if jobType == "GetUrl":
                    actions.insert(jobPosition, (getUrlJob,kwargs))
                elif jobType == "InputField":
                    actions.insert(jobPosition, (inputFieldJob,kwargs))
                elif jobType == "ClickButton":
                    actions.insert(jobPosition, (clickButtonJob,kwargs))
        return actions

    def handleQThreadStatus(self, event):
        if event['type'] == "driverCreating":
            self.postToUI("status", {"msg": "Creating Driver " + str(self.nextDriverNumber)})
            self.nextDriverNumber += 1

        if event['type'] == "driverDied":
            driverNumber = self.worker.driverManager.drivers[event['uuid']]['number']
            self.postToUI("status", {"msg": "Driver " + str(driverNumber) + " Died"})
            self.worker.driverManager.drivers[event['uuid']]['dropped'] = True
            self.updateCounter()

        if event['type'] == "driverReady":
            self.worker.driverManager.drivers[event['uuid']]['number'] = self.nextReadyDriverNumber
            self.worker.driverManager.drivers[event['uuid']]['threadQueue'].put(("assignNumber", {"number": self.nextReadyDriverNumber}))
            driver = self.worker.driverManager.drivers[event['uuid']]['driver']
            scrapeJobClass = abstractScrapeJob(driver)
            actions = self.getActionsForScrapeJob(self.mainDefaultBox.currentText())
            scrapeJobClass.initiateActions(actions)
            self.worker.driverManager.drivers[event['uuid']]['scrapeJobClass'] = scrapeJobClass
            onDriverReadyInfo = {"number":self.nextReadyDriverNumber,"uuid":event['uuid']}
            self.postToUI("status", {"msg": "Driver Ready " + str(self.nextReadyDriverNumber)})
            self.postToUI("createInstance", onDriverReadyInfo)
            self.nextReadyDriverNumber += 1
            self.updateCounter()

        if event['type'] == "driverResult":
            jobuuid = event['jobuuid']
            direction = event['direction']
            result = event['result']
            executeClass = self.worker.driverManager.drivers[event['uuid']]['scrapeJobClass']
            actions = executeClass.actions
            for action in actions:
                if action[1].get("uuid") == jobuuid:
                    if direction == "forward":
                        action[1]['isexecuted'] = True
                    elif direction == "backward":
                        action[1]['isexecuted'] = False
                    break
            if "settingsWindowClass" in self.worker.driverManager.drivers[event['uuid']].keys():
                jobSettingsClass = self.worker.driverManager.drivers[event['uuid']]['settingsWindowClass']
                jobSettingsClass.updateJobExecutionStatus(jobuuid, direction, result)

    def QThreadFinished(self, event):
        self.startButton.setDisabled(False)
        self.closeAllButton.setDisabled(False)
        self.executeAllButton.setDisabled(False)
        
    def closeDriverInstance(self, uuid):
        driverNumber = self.worker.driverManager.drivers[uuid]['number']
        print("Closing Driver " + str(driverNumber))
        self.worker.driverManager.drivers[uuid]['threadQueue'].put("close")
        if 'settingsWindow' in self.worker.driverManager.drivers[uuid].keys():
            self.worker.driverManager.drivers[uuid]['settingsWindow'].close()   
        driverInstance = self.scrollAreaWidgetContents.findChild(QtWidgets.QWidget,"driverInstance"+str(uuid))
        driverInstance.deleteLater()
        self.postToUI("status", {"msg": "Driver " + str(driverNumber) + " Closed"})
        self.worker.driverManager.drivers[uuid]['dropped'] = True
        self.updateCounter()

    def closeAllDrivers(self):
        print("Closing All Drivers")
        for uuid, driver in self.worker.driverManager.drivers.items():
            if not driver['dropped']:
                self.closeDriverInstance(uuid)
                if 'settingsWindow' in self.worker.driverManager.drivers[uuid].keys():
                    self.worker.driverManager.drivers[uuid]['settingsWindow'].close()
        print("All Drivers Closed")
        self.postToUI("cleanStatus", self.statusArea.clear)
        print("UI Status Cleaned")
        self.startButton.setDisabled(False)

    def updateCounter(self):
        currentActiveDrivers = len(self.worker.driverManager.drivers) - sum(1 for driver in self.worker.driverManager.drivers.values() if driver['dropped'])
        self.countNumber.setText(str(currentActiveDrivers))

    def postToUI(self, taskType, data):
        self.uiUpdateQueue.append((taskType, data))
        if not self.uiUpdateTimer.isActive():
            self.uiUpdateTimer.start()

    def processNextUiUpdate(self):
        if self.uiUpdateQueue:
            updateType, event = self.uiUpdateQueue.popleft()
            if updateType == "status":
                self.statusArea.append(event['msg'])
            elif updateType == "createInstance":
                self.createDriverInstances(event)
            elif updateType == "focusDriver":
                hwnd = event['HWND']
                if hwnd:
                    win32gui.SetForegroundWindow(hwnd)
            elif updateType == "showDriver":
                hwnd = event['HWND']
                if hwnd:
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                    win32gui.SetForegroundWindow(hwnd)
            elif updateType == "hideDriver":
                hwnd = event['HWND']
                if hwnd:
                    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            elif updateType == "cleanStatus":
                event()
        else:
            self.uiUpdateTimer.stop()

    def executeAllDrivers(self):
        for uuid, driver in self.worker.driverManager.drivers.items():
            if not driver['dropped']:
                pass

    def closeEvent(self, event):
        self.worker.driverManager.appClosed = True
        print("App Closed. Closing Drivers.")
        self.uiUpdateTimer.stop()
        self.worker.driverManager.createTimer.stop()
        print("Closing Remaining Drivers.")
        self.closeAllDrivers()
        print("All Drivers Closed. Closing App.")
        if self.addNewJobDialog:
            self.addNewJobDialog.close()
        event.accept()

    def scrollToBottom(self):
        QTimer.singleShot(0, lambda: self.scrollArea.verticalScrollBar().setValue(
            self.scrollArea.verticalScrollBar().maximum()
        ))

    def createDriverInstances(self, driverInfo):
        number = driverInfo["number"]
        uuid = driverInfo["uuid"]
        driverInstance = QtWidgets.QWidget(self.scrollAreaWidgetContents)
        driverInstance.setMaximumSize(QtCore.QSize(16777215, 50))
        driverInstance.setObjectName("driverInstance"+str(uuid))
        instanceLayout = QtWidgets.QHBoxLayout(driverInstance)
        instanceLayout.setContentsMargins(5, 5, 5, 5)
        instanceLayout.setSpacing(5)
        instanceLayout.setObjectName("instanceLayout"+str(uuid))
        driverCount = QtWidgets.QLabel(driverInstance)
        driverCount.setMaximumSize(QtCore.QSize(15, 16777215))
        driverCount.setObjectName("driverCount"+str(uuid))
        driverCount.setText(str(self.nextDriverCount))
        instanceLayout.addWidget(driverCount)
        driverName = QtWidgets.QLabel(driverInstance)
        driverName.setObjectName("driverName"+str(uuid))
        driverName.setText("Driver " + str(number))
        driverName.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        driverName.mousePressEvent = lambda event: self.postToUI("focusDriver", {"HWND": self.worker.driverManager.drivers[uuid]['HWND']})
        instanceLayout.addWidget(driverName)
        driverDefaultUrl = QtWidgets.QComboBox(driverInstance)
        driverDefaultUrl.setMaximumSize(QtCore.QSize(150, 30))
        driverDefaultUrl.setObjectName("driverDefaultUrl"+str(uuid))
        for job in self.existJobs:
            driverDefaultUrl.addItem(job)
        def handleDriverScrapeJobChange(event):
            print(event)
            scrapeJobClass = abstractScrapeJob(self.worker.driverManager.drivers[uuid]['driver'])
            actions = self.getActionsForScrapeJob(driverDefaultUrl.currentText())
            print(actions)
            scrapeJobClass.initiateActions(actions)
            self.worker.driverManager.drivers[uuid]['scrapeJobClass'] = scrapeJobClass
        def controlButtonHandle():
            jobsDialog = QDialog()
            jobsDialogClass = JobsConstruct(self, driverDefaultUrl.currentText(), uuid)
            jobsDialogClass.setupUi(jobsDialog, self.worker.driverManager.drivers[uuid]['number'])
            self.worker.driverManager.drivers[uuid]['settingsWindow'] = jobsDialog
            self.worker.driverManager.drivers[uuid]['settingsWindowClass'] = jobsDialogClass  
            self.worker.driverManager.drivers[uuid]['settingsWindow'].show()
        def nextButtonHandle():
            executeClass = self.worker.driverManager.drivers[uuid]['scrapeJobClass']
            func = executeClass.executeNextAction
            self.worker.driverManager.drivers[uuid]['threadQueue'].put((func,{}))
        def previousButtonHandle():
            executeClass = self.worker.driverManager.drivers[uuid]['scrapeJobClass']
            func = executeClass.executePreviousAction
            self.worker.driverManager.drivers[uuid]['threadQueue'].put((func,{}))
        showFlag = not self.hiddenCheckBox.isChecked()
        def eyeButtonHandle():
            nonlocal showFlag
            if showFlag:
                self.postToUI("hideDriver", {"HWND": self.worker.driverManager.drivers[uuid]['HWND']})
                showFlag = False
            else:
                self.postToUI("showDriver", {"HWND": self.worker.driverManager.drivers[uuid]['HWND']})
                showFlag = True
        driverDefaultUrl.currentTextChanged.connect(handleDriverScrapeJobChange)
        driverDefaultUrl.setCurrentText(self.mainDefaultBox.currentText())
        instanceLayout.addWidget(driverDefaultUrl)
        spacerItem4 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        instanceLayout.addItem(spacerItem4)
        driverControl = QtWidgets.QPushButton(driverInstance)
        driverControl.setMaximumSize(QtCore.QSize(70, 30))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("resources/settings.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        driverControl.setIcon(icon)
        driverControl.setObjectName("driverControl"+str(uuid))
        driverControl.clicked.connect(controlButtonHandle)
        instanceLayout.addWidget(driverControl)
        previousButton = QtWidgets.QPushButton(driverInstance)
        previousButton.setMaximumSize(QtCore.QSize(50, 16777215))
        previousButton.setObjectName("previousButton"+str(uuid))
        previousButton.clicked.connect(previousButtonHandle)
        previcon = QtGui.QIcon()
        previcon.addPixmap(QtGui.QPixmap("resources/previous.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        previousButton.setIcon(previcon)
        instanceLayout.addWidget(previousButton)
        nextButton = QtWidgets.QPushButton(driverInstance)
        nextButton.setMaximumSize(QtCore.QSize(50, 16777215))
        nextButton.setObjectName("nextButton"+str(uuid))
        nextButton.clicked.connect(nextButtonHandle)
        nexticon = QtGui.QIcon()
        nexticon.addPixmap(QtGui.QPixmap("resources/next.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        nextButton.setIcon(nexticon)
        instanceLayout.addWidget(nextButton)
        eyeButton = QtWidgets.QPushButton(driverInstance)
        eyeButton.setMinimumSize(QtCore.QSize(0, 0))
        eyeButton.setMaximumSize(QtCore.QSize(50, 16777215))
        eyeButton.setText("")
        eyeicon = QtGui.QIcon()
        eyeicon.addPixmap(QtGui.QPixmap("resources/eye.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        eyeButton.setIcon(eyeicon)
        eyeButton.setObjectName("eyeButton"+str(uuid))
        eyeButton.clicked.connect(eyeButtonHandle)
        instanceLayout.addWidget(eyeButton)
        spacerItem1 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        instanceLayout.addItem(spacerItem1)
        closeDriver = QtWidgets.QPushButton(driverInstance)
        closeDriver.setMaximumSize(QtCore.QSize(100, 30))
        closeDriver.setObjectName("closeDriver"+str(uuid))
        closeDriver.setText("Close")
        closeDriver.clicked.connect(lambda:self.closeDriverInstance(uuid))
        instanceLayout.addWidget(closeDriver)
        self.instancesContainerLayout.addWidget(driverInstance)
        self.nextDriverCount += 1
        self.scrollAreaLayout.activate()
        self.scrollToBottom()