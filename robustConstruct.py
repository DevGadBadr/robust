from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialog
from scrapeJobsHelpers import getUrlJob
from uirobust import Ui_RobustDialog
from PyQt5.QtCore import QTimer, Qt
from workerThread import QWorker
from collections import deque
from scrapeJobs import APP_URLS, abstractScrapeJob, zenHrAutomation

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
        self.driverInstancePlaceHolder.deleteLater()
        self.initiateVariables()
        self.connectActions()
        self.initiateWorker()
        self.modifyMainDefaultBox()

    def modifyMainDefaultBox(self):
        self.mainDefaultBox.clear()
        for key,value in APP_URLS.items():
            self.mainDefaultBox.addItem(key)
            self.mainDefaultBox.setItemData(self.mainDefaultBox.count()-1, value)

    def initiateVariables(self):
        self.numberOfDrivers = 1
        self.nextDriverNumber = 1
        self.nextReadyDriverNumber = 1

    def connectActions(self):
        self.slider.valueChanged.connect(self.castSliderChange)
        self.startButton.clicked.connect(self.createDrivers)
        self.executeAllButton.clicked.connect(self.executeAllDrivers)

    def castSliderChange(self,value):
        self.driverCountLabel.setText(str(value))
        self.numberOfDrivers = value

    def initiateWorker(self):
        self.worker = QWorker()
        self.worker.driverManager.finished.connect(self.QThreadFinished)
        self.worker.driverManager.status.connect(self.handleQThreadStatus)
        self.closeAllButton.clicked.connect(self.closeAllDrivers)

    def createDrivers(self):
        self.startButton.setDisabled(True)
        self.worker.run(self.numberOfDrivers)

    def handleQThreadStatus(self,event):
        if event['type'] == "driverCreating":
            self.postToUI("status", {"msg": "Creating Driver " + str(self.nextDriverNumber)})
            self.nextDriverNumber += 1

        if event['type'] == "driverReady":
            self.worker.driverManager.drivers[event['uuid']]['number'] = self.nextReadyDriverNumber
            currentDefaultUrl = APP_URLS[self.mainDefaultBox.currentText()]
            self.worker.driverManager.drivers[event['uuid']]['threadQueue'].put(("assignNumber", {"number": self.nextReadyDriverNumber}))
            if currentDefaultUrl == "ZenHR":
                scrapeJobClass = zenHrAutomation(self.worker.driverManager.drivers[event['uuid']]['driver'])
                scrapeJobClass.initiateActions([(getUrlJob, {"url": currentDefaultUrl})])
            else:
                scrapeJobClass = abstractScrapeJob(self.worker.driverManager.drivers[event['uuid']]['driver'])
                scrapeJobClass.initiateActions([(getUrlJob, {"url": currentDefaultUrl})])
            self.worker.driverManager.drivers[event['uuid']]['scrapeJobClass'] = scrapeJobClass
            onDriverReadyInfo = {"number":self.nextReadyDriverNumber,"uuid":event['uuid']}
            self.postToUI("status", {"msg": "Driver Ready " + str(self.nextReadyDriverNumber)})
            self.postToUI("createInstance", onDriverReadyInfo)
            self.nextReadyDriverNumber += 1
            self.updateCounter()

    def QThreadFinished(self,event):
        self.startButton.setDisabled(False)

    def closeDriverInstance(self,uuid):
        driverNumber = self.worker.driverManager.drivers[uuid]['number']
        print("Closing Driver " + str(driverNumber))
        self.worker.driverManager.drivers[uuid]['threadQueue'].put("close")
        driverInstance = self.scrollAreaWidgetContents.findChild(QtWidgets.QWidget,"driverInstance"+str(uuid))
        driverInstance.deleteLater()
        self.postToUI("status", {"msg": "Driver " + str(driverNumber) + " Closed"})
        self.worker.driverManager.drivers[uuid]['dropped'] = True
        self.updateCounter()

    def closeAllDrivers(self):
        for uuid,driver in self.worker.driverManager.drivers.items():
            if not driver['dropped']:
                self.closeDriverInstance(uuid)
        self.postToUI("cleanStatus", self.statusArea.clear)
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
            elif updateType == "cleanStatus":
                event()
        else:
            self.uiUpdateTimer.stop()

    def executeAllDrivers(self):
        for uuid,driver in self.worker.driverManager.drivers.items():
            if not driver['dropped']:
                pass
                # driver['threadQueue'].put((scrapeUrl,[],{"url":driver['currentDefaultUrl']}))

    def createDriverInstances(self,driverInfo):
        number = driverInfo["number"]
        uuid = driverInfo["uuid"]
        driverInstance = QtWidgets.QWidget(self.scrollAreaWidgetContents)
        driverInstance.setMaximumSize(QtCore.QSize(16777215, 50))
        driverInstance.setObjectName("driverInstance"+str(uuid))
        instanceLayout = QtWidgets.QHBoxLayout(driverInstance)
        instanceLayout.setContentsMargins(5, 5, 5, 5)
        instanceLayout.setSpacing(5)
        instanceLayout.setObjectName("instanceLayout"+str(uuid))
        driverName = QtWidgets.QLabel(driverInstance)
        driverName.setObjectName("driverName"+str(uuid))
        driverName.setText("Driver " + str(number))
        instanceLayout.addWidget(driverName)
        driverDefaultUrl = QtWidgets.QComboBox(driverInstance)
        driverDefaultUrl.setMaximumSize(QtCore.QSize(16777215, 30))
        driverDefaultUrl.setObjectName("driverDefaultUrl"+str(uuid))
        for key,value in APP_URLS.items():
            driverDefaultUrl.addItem(key)
            driverDefaultUrl.setItemData(driverDefaultUrl.count()-1, value)
        def handleDriverScrapeJobChange(event):
            print(event)
            if event == "ZenHR":
                scrapeJobClass = zenHrAutomation(self.worker.driverManager.drivers[uuid]['driver'])
                actions = [(getUrlJob, {"url": APP_URLS[event]})]
                scrapeJobClass.initiateActions(actions)
            else:
                scrapeJobClass = abstractScrapeJob(self.worker.driverManager.drivers[uuid]['driver'])
                actions = [(getUrlJob, {"url": APP_URLS[event]})]
                scrapeJobClass.initiateActions(actions)
            self.worker.driverManager.drivers[uuid]['scrapeJobClass'] = scrapeJobClass
        def getButtonHandle():
            executeClass = self.worker.driverManager.drivers[uuid]['scrapeJobClass']
            func = executeClass.getUrlAction
            self.worker.driverManager.drivers[uuid]['threadQueue'].put((func,{}))
        def nextButtonHandle():
            executeClass = self.worker.driverManager.drivers[uuid]['scrapeJobClass']
            func = executeClass.executeNextAction
            self.worker.driverManager.drivers[uuid]['threadQueue'].put((func,{}))
        def previousButtonHandle():
            executeClass = self.worker.driverManager.drivers[uuid]['scrapeJobClass']
            func = executeClass.executePreviousAction
            self.worker.driverManager.drivers[uuid]['threadQueue'].put((func,{}))
        driverDefaultUrl.currentTextChanged.connect(handleDriverScrapeJobChange)
        driverDefaultUrl.setCurrentText(self.mainDefaultBox.currentText())
        instanceLayout.addWidget(driverDefaultUrl)
        spacerItem4 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        instanceLayout.addItem(spacerItem4)
        driverControl = QtWidgets.QPushButton(driverInstance)
        driverControl.setMaximumSize(QtCore.QSize(70, 30))
        driverControl.setText("Get")
        driverControl.setObjectName("driverControl"+str(uuid))
        driverControl.clicked.connect(getButtonHandle)
        instanceLayout.addWidget(driverControl)
        previousButton = QtWidgets.QPushButton(driverInstance)
        previousButton.setMaximumSize(QtCore.QSize(60, 16777215))
        previousButton.setObjectName("previousButton"+str(uuid))
        previousButton.setText("<Action")
        previousButton.clicked.connect(previousButtonHandle)
        instanceLayout.addWidget(previousButton)
        nextButton = QtWidgets.QPushButton(driverInstance)
        nextButton.setMaximumSize(QtCore.QSize(60, 16777215))
        nextButton.setObjectName("nextButton"+str(uuid))
        nextButton.setText("Action>")
        nextButton.clicked.connect(nextButtonHandle)
        instanceLayout.addWidget(nextButton)
        spacerItem1 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        instanceLayout.addItem(spacerItem1)
        closeDriver = QtWidgets.QPushButton(driverInstance)
        closeDriver.setMaximumSize(QtCore.QSize(100, 30))
        closeDriver.setObjectName("closeDriver"+str(uuid))
        closeDriver.setText("Close")
        closeDriver.clicked.connect(lambda:self.closeDriverInstance(uuid))
        instanceLayout.addWidget(closeDriver)
        self.instancesContainerLayout.addWidget(driverInstance)