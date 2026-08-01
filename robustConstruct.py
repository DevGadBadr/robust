import json
from PyQt5 import QtWidgets
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QDialog, QGraphicsOpacityEffect
from scrapeJobsHelpers import clickButtonJob, getUrlJob, inputFieldJob, extractTextJob, extractLinksJob
from ui.uimain import Ui_RobustMain
from newJobConstruct import NewJobConstruct
from jobsAreaConstruct import JobsAreaConstruct
from PyQt5.QtCore import QTimer, Qt
from workerThread import QWorker
from collections import deque
from scrapeJobs import abstractScrapeJob
from elementSetup import setUpSplitters
import win32gui
import win32con
from chromeEmbed import embedChrome, resizeChrome, detachChrome
from ui.manageTheme import DarkPalette, LightPalette, enableLightTitlebar, isWindowsDarkMode, enableDarkTitlebar


class DriverHostWidget(QtWidgets.QWidget):
    """Host that keeps an embedded Chrome HWND sized to itself."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chromeHwnd = None
        self.driverUuid = None

    def setChromeHwnd(self, hwnd):
        self.chromeHwnd = hwnd

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.chromeHwnd:
            resizeChrome(self.chromeHwnd, self)

class RobustConstruct(Ui_RobustMain):

    def __init__(self):
        super().__init__()
        self.uiUpdateQueue = deque()
        self.uiUpdateTimer = QTimer()
        self.uiUpdateTimer.setInterval(50)
        self.uiUpdateTimer.timeout.connect(self.processNextUiUpdate)

    def setupUi(self, RobustDialog:QDialog):
        super().setupUi(RobustDialog)
        self.mainWindow = RobustDialog
        RobustDialog.setWindowFlags(RobustDialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        RobustDialog.setWindowFlags(RobustDialog.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        RobustDialog.closeEvent = self.closeEvent
        self.intitializing = True
        self.driverInstancePlaceHolder.deleteLater()
        self.initiateVariables()
        self.clearJobsAreaPanel()
        self.connectActions()
        self.initiateWorker()
        self.loadExistingJobs()
        self.loadSettings()
        self.modifyMainDefaultBox()
        setUpSplitters(self)
        self.intitializing = False
        self.startButton.click()

    def clearJobsAreaPanel(self):
        if getattr(self, 'oneJob', None) is not None:
            self.oneJob.deleteLater()
            self.oneJob = None
        self._jobsTemplateRemoved = True
        self.jobsGroupBox.setTitle("Jobs")
        self.statusLabel.setText("")
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(0)
        self.saveOrderButton.setGraphicsEffect(effect)
        self.saveOrderButton.setEnabled(False)
        self.activeJobsArea = None

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
        self.latestJob = settingsFile.get("latestJob","")
        self.controlPanelWidth = settingsFile.get("controlPanelWidth", 500)
        self.statusAreaHeight = settingsFile.get("statusAreaHeight", 200)
        self.jobsAreaHeight = settingsFile.get("jobsAreaHeight", 200)
        self.windowX = settingsFile.get("windowX", 0)
        self.windowY = settingsFile.get("windowY", 0)
        self.windowWidth = settingsFile.get("windowWidth", 1020)
        self.windowHeight = settingsFile.get("windowHeight", 821)
        self.windowMaximized = settingsFile.get("windowMaximized", False)
        self.initialTheme = isWindowsDarkMode()
        if settingsFile.get("theme") == "dark":
                self.applyDarkTheme(persist=False)
        elif settingsFile.get("theme") == "light":
            self.applyLightTheme(persist=False)
        else:
            if self.initialTheme:
                self.applyDarkTheme(persist=False)
            else:
                self.applyLightTheme(persist=False)

    def restoreWindowGeometry(self):
        self.mainWindow.setGeometry(self.windowX, self.windowY, self.windowWidth, self.windowHeight)
        if self.windowMaximized:
            self.mainWindow.showMaximized()
        else:
            self.mainWindow.show()
        # Re-apply after show so sizes aren't clamped against the pre-show height
        QTimer.singleShot(0, self.applyAllSplitterSizes)

    def modifyMainDefaultBox(self):
        self.mainDefaultBox.clear()
        for job in self.existJobs:
            self.mainDefaultBox.addItem(job)
        if self.latestJob in self.existJobs:
            self.mainDefaultBox.setCurrentText(self.latestJob)

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
        self.mainDefaultBox.currentTextChanged.connect(self.handleMainJobChange)
        self.exitAction.triggered.connect(self.mainWindow.close)
        self.actionDark.triggered.connect(lambda: self.applyDarkTheme())
        self.actionLight.triggered.connect(lambda: self.applyLightTheme())
        self.driversTabWidget.currentChanged.connect(self.handleDriverTabChange)

    def handleDriverTabChange(self, index):
        print("Driver Tab Changed to index:", index)
        if index < 0:
            return
        currentWidget = self.driversTabWidget.currentWidget()
        driverObjectName = currentWidget.objectName() if currentWidget else None
        if not driverObjectName or not driverObjectName.startswith("driverTab"):
            return
        scrapeUuidStr = driverObjectName.replace("driverTab", "", 1)
        # objectName stores str(uuid); drivers dict is keyed by uuid.UUID
        driver = next(
            (driver for uuid, driver in self.worker.driverManager.drivers.items() if str(uuid) == scrapeUuidStr),
            None,
        )
        if not driver:
            return
        driverControlButton = self.scrollAreaWidgetContents.findChild(QtWidgets.QPushButton, "driverControl" + scrapeUuidStr)
        if not driverControlButton:
            return
        driverControlButton.click()
        existing = driver.get('settingsWindowClass')
        if existing is not None:
            existing.activate()
        else:
            prev = getattr(self, 'activeJobsArea', None)
            if prev is not None:
                prev.deactivate()
                self.jobsGroupBox.setTitle("Jobs")
                self.statusLabel.setText("")
                self.saveOrderButton.setEnabled(False)
            

    def applyDarkTheme(self, persist=True):
        QApplication.setPalette(DarkPalette)
        enableDarkTitlebar(int(self.mainWindow.winId()))
        self.refreshThemedWidgets()
        if persist:
            self.saveTheme("dark")

    def applyLightTheme(self, persist=True):
        QApplication.setPalette(LightPalette)
        enableLightTitlebar(int(self.mainWindow.winId()))
        self.refreshThemedWidgets()
        if persist:
            self.saveTheme("light")

    def refreshThemedWidgets(self):
        # Re-polish so Fusion picks up the new Button palette on existing widgets
        app = QApplication.instance()
        for widget in app.allWidgets():
            app.style().unpolish(widget)
            app.style().polish(widget)
            widget.update()

    def saveTheme(self, theme):
        with open("./resources/settings.json") as file:
            settings = json.load(file)
        settings["theme"] = theme
        with open("./resources/settings.json", "w") as file:
            json.dump(settings, file)

    def handleMainJobChange(self):
        if not self.intitializing:
            with open("./resources/settings.json") as file:
                settings = json.load(file)
            settings["latestJob"] = self.mainDefaultBox.currentText()
            with open("./resources/settings.json","w") as file:
                json.dump(settings,file) 

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
                elif jobType == "ExtractText":
                    actions.insert(jobPosition, (extractTextJob,kwargs))
                elif jobType == "ExtractLinks":
                    actions.insert(jobPosition, (extractLinksJob,kwargs))
        return actions

    def handleQThreadStatus(self, event):
        if event['type'] == "driverCreating":
            self.postToUI("status", {"msg": "Creating Driver " + str(self.nextDriverNumber)})
            self.nextDriverNumber += 1

        if event['type'] == "driverDied":
            uuid = event['uuid']
            driverNumber = self.worker.driverManager.drivers[uuid]['number']
            self.postToUI("status", {"msg": "Driver " + str(driverNumber) + " Died"})
            driver = self.worker.driverManager.drivers[uuid]
            jobsArea = driver.get('settingsWindowClass')
            if jobsArea is not None:
                try:
                    jobsArea.cleanup()
                except Exception:
                    pass
                driver['settingsWindowClass'] = None
            if 'settingsWindow' in driver.keys():
                driver['settingsWindow'].close()
            driverInstance = self.scrollAreaWidgetContents.findChild(QtWidgets.QWidget, "driverInstance" + str(uuid))
            if driverInstance:
                driverInstance.deleteLater()
            self.removeDriverTab(uuid)
            driver['dropped'] = True
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
            artifact = event.get("artifact")
            executeClass = self.worker.driverManager.drivers[event['uuid']]['scrapeJobClass']
            actions = executeClass.actions
            for action in actions:
                if action[1].get("uuid") == jobuuid:
                    jobtype = action[1].get("jobtype")
                    is_extract = jobtype in ("ExtractText", "ExtractLinks")
                    if direction == "forward":
                        action[1]['isexecuted'] = True
                        if is_extract and not str(result).startswith("Error:"):
                            action[1]['artifact'] = artifact
                            result = "Extracted Successfully"
                    elif direction == "backward":
                        action[1]['isexecuted'] = False
                        if is_extract:
                            existing = action[1].pop('artifact', None)
                            if existing:
                                result = "Content removed"
                            else:
                                result = "No content to remove"
                    break
            if "settingsWindowClass" in self.worker.driverManager.drivers[event['uuid']].keys():
                jobSettingsClass = self.worker.driverManager.drivers[event['uuid']]['settingsWindowClass']
                jobSettingsClass.updateJobExecutionStatus(jobuuid, direction, result)
            screenshot = event.get("screenshot")
            if screenshot:
                self.postToUI("updateScreenshot", {"uuid": event['uuid'], "screenshot": screenshot})

        if event['type'] == "elementPicked":
            self.postToUI("elementPicked", event)

        if event['type'] == "elementPickCancelled":
            self.postToUI("elementPickCancelled", event)

    def QThreadFinished(self, event):
        self.startButton.setDisabled(False)
        self.closeAllButton.setDisabled(False)
        self.executeAllButton.setDisabled(False)
        
    def closeDriverInstance(self, uuid):
        driver = self.worker.driverManager.drivers[uuid]
        driverNumber = driver['number']
        print("Closing Driver " + str(driverNumber))
        jobsArea = driver.get('settingsWindowClass')
        if jobsArea is not None:
            try:
                jobsArea.cleanup()
            except Exception:
                pass
            driver['settingsWindowClass'] = None
        self.detachDriverChrome(uuid)
        driver['threadQueue'].put("close")
        if 'settingsWindow' in driver.keys():
            driver['settingsWindow'].close()
        driverInstance = self.scrollAreaWidgetContents.findChild(QtWidgets.QWidget, "driverInstance" + str(uuid))
        if driverInstance:
            driverInstance.deleteLater()
        self.removeDriverTab(uuid)
        self.postToUI("status", {"msg": "Driver " + str(driverNumber) + " Closed"})
        driver['dropped'] = True
        self.updateCounter()

    def detachDriverChrome(self, uuid):
        driver = self.worker.driverManager.drivers.get(uuid)
        if not driver:
            return
        host = self.driversTabWidget.findChild(DriverHostWidget, "driverHost" + str(uuid))
        hwnd = driver.get('HWND')
        orig = None
        if host is not None:
            orig = host.property("_chromeOrigStyle")
            host.setChromeHwnd(None)
        if hwnd and driver.get('embedded'):
            detachChrome(hwnd, orig)
            driver['embedded'] = False

    def embedDriverChrome(self, uuid):
        driver = self.worker.driverManager.drivers.get(uuid)
        if not driver or driver.get('headless'):
            return
        hwnd = driver.get('HWND')
        host = self.driversTabWidget.findChild(DriverHostWidget, "driverHost" + str(uuid))
        if not hwnd or host is None:
            return
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        except Exception:
            pass
        if embedChrome(hwnd, host):
            host.setChromeHwnd(hwnd)
            driver['embedded'] = True
            driver['visible'] = True

    def removeDriverTab(self, uuid):
        self.detachDriverChrome(uuid)
        tabContainer = self.driversTabWidget.findChild(QtWidgets.QWidget, "driverTab" + str(uuid))
        if not tabContainer:
            return
        index = self.driversTabWidget.indexOf(tabContainer)
        if index >= 0:
            self.driversTabWidget.removeTab(index)
        tabContainer.deleteLater()

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

    def updateDriverScreenshot(self, uuid, png_bytes):
        pngLabel = self.driversTabWidget.findChild(QtWidgets.QLabel, "driverScreenshot" + str(uuid))
        if not pngLabel or not png_bytes:
            return
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(png_bytes)
        pngLabel.setPixmap(pixmap)

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
            elif updateType == "updateScreenshot":
                self.updateDriverScreenshot(event['uuid'], event['screenshot'])
            elif updateType == "embedDriver":
                self.embedDriverChrome(event['uuid'])
            elif updateType == "focusDriver":
                hwnd = event['HWND']
                if hwnd:
                    try:
                        win32gui.SetForegroundWindow(hwnd)
                    except Exception:
                        pass
            elif updateType == "popOutDriver":
                self.popOutDriver(event['uuid'])
            elif updateType == "reEmbedDriver":
                self.embedDriverChrome(event['uuid'])
            elif updateType == "elementPicked":
                self.handleElementPicked(event)
            elif updateType == "elementPickCancelled":
                self.handleElementPickCancelled(event)
            elif updateType == "cleanStatus":
                event()
        else:
            self.uiUpdateTimer.stop()

    def popOutDriver(self, uuid):
        driver = self.worker.driverManager.drivers.get(uuid)
        if not driver or driver.get('headless'):
            return
        self.detachDriverChrome(uuid)
        hwnd = driver.get('HWND')
        if hwnd:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass
        driver['visible'] = True

    def handleElementPicked(self, event):
        uuid = event.get('uuid')
        driver = self.worker.driverManager.drivers.get(uuid)
        if not driver:
            return
        jobsArea = driver.get('settingsWindowClass')
        if jobsArea is not None:
            jobsArea.applyPickedLocator(
                event.get('jobuuid'),
                event.get('locatorType'),
                event.get('locatorValue'),
            )

    def handleElementPickCancelled(self, event):
        uuid = event.get('uuid')
        driver = self.worker.driverManager.drivers.get(uuid)
        if not driver:
            return
        jobsArea = driver.get('settingsWindowClass')
        if jobsArea is not None:
            jobsArea.onPickCancelled(event.get('jobuuid'))

    def executeAllDrivers(self):
        for uuid, driver in self.worker.driverManager.drivers.items():
            if not driver['dropped']:
                pass

    def closeEvent(self, event):
        with open("./resources/settings.json", "r") as f:
            settings = json.load(f)
        if self.mainWindow.isMaximized():
            settings["windowMaximized"] = True
            geo = self.mainWindow.normalGeometry()
        else:
            settings["windowMaximized"] = False
            geo = self.mainWindow.geometry()
        settings["windowX"] = geo.x()
        settings["windowY"] = geo.y()
        settings["windowWidth"] = geo.width()
        settings["windowHeight"] = geo.height()
        settings["controlPanelWidth"] = self.mainHorizontalSplitter.sizes()[1]
        settings["statusAreaHeight"] = self.controlVerticalSplitter.sizes()[0]
        settings["jobsAreaHeight"] = self.jobsVerticalSplitter.sizes()[1]
        with open("./resources/settings.json", "w") as f:
            json.dump(settings, f)
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
            scrapeJobClass = abstractScrapeJob(self.worker.driverManager.drivers[uuid]['driver'])
            actions = self.getActionsForScrapeJob(driverDefaultUrl.currentText())
            scrapeJobClass.initiateActions(actions)
            self.worker.driverManager.drivers[uuid]['scrapeJobClass'] = scrapeJobClass
        def controlButtonHandle():
            driver = self.worker.driverManager.drivers[uuid]
            existing = driver.get('settingsWindowClass')
            if existing is None:
                jobsAreaClass = JobsAreaConstruct(self, driverDefaultUrl.currentText(), uuid, driver['number'])
                jobsAreaClass.setupUi()
                driver['settingsWindowClass'] = jobsAreaClass
            else:
                existing.activate()
        def nextButtonHandle():
            executeClass = self.worker.driverManager.drivers[uuid]['scrapeJobClass']
            func = executeClass.executeNextAction
            self.worker.driverManager.drivers[uuid]['threadQueue'].put((func,{}))
        def previousButtonHandle():
            executeClass = self.worker.driverManager.drivers[uuid]['scrapeJobClass']
            func = executeClass.executePreviousAction
            self.worker.driverManager.drivers[uuid]['threadQueue'].put((func,{}))
        def eyeButtonHandle():
            driver = self.worker.driverManager.drivers[uuid]
            if driver.get('headless'):
                return
            if driver.get('embedded'):
                self.postToUI("popOutDriver", {"uuid": uuid})
            else:
                self.postToUI("reEmbedDriver", {"uuid": uuid})
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
        eyeButton.setEnabled(not self.worker.driverManager.drivers[uuid].get('headless', False))
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
        # Live Chrome host tab (or headless placeholder)
        tabContainer = QtWidgets.QWidget()
        tabContainer.setObjectName("driverTab" + str(uuid))
        tabLayout = QtWidgets.QHBoxLayout(tabContainer)
        tabLayout.setContentsMargins(0, 0, 0, 0)
        tabLayout.setSpacing(0)
        isHeadless = self.worker.driverManager.drivers[uuid].get('headless', False)
        if isHeadless:
            pngLabel = QtWidgets.QLabel("Headless — waiting for screenshot")
            pngLabel.setAlignment(Qt.AlignCenter)
            pngLabel.setObjectName("driverScreenshot" + str(uuid))
            pngLabel.setScaledContents(True)
            tabLayout.addWidget(pngLabel)
        else:
            host = DriverHostWidget(tabContainer)
            host.setObjectName("driverHost" + str(uuid))
            host.driverUuid = uuid
            tabLayout.addWidget(host)
            QTimer.singleShot(0, lambda u=uuid: self.postToUI("embedDriver", {"uuid": u}))
        self.driversTabWidget.addTab(tabContainer, f"Driver {number}")
