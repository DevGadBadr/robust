from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QGraphicsOpacityEffect
from scrapeJobsHelpers import JOB_TYPES, IDENTIFIER_VALUES
from artifactConstruct import JobArtifactConstruct
import uuid
import json


class JobsAreaConstruct:

    def __init__(self, robustClass, jobsFor, scrapeuuid, driverNumber):
        self.robustClass = robustClass
        self.jobsFor = jobsFor
        self.scrapeuuid = scrapeuuid
        self.driverNumber = driverNumber
        self.jobRowWidgets = []
        self._stash = QtWidgets.QWidget()
        self._chromeConnected = False
        self._rowsStale = False
        self.resetLabelTimer = QtCore.QTimer()
        self.resetLabelTimer.setInterval(1500)
        self.resetLabelTimer.timeout.connect(self.resetStatusLabel)
        self.armedPickButton = None
        self.armedJobUuid = None
        self.pickPollTimer = QtCore.QTimer()
        self.pickPollTimer.setInterval(150)
        self.pickPollTimer.timeout.connect(self.pollPickResult)

    @property
    def scrapeJobClass(self):
        # The driver's scrape job object is replaced whenever its scrape job changes,
        # so it must never be cached on this class.
        driver = self.robustClass.worker.driverManager.drivers.get(self.scrapeuuid)
        return driver.get('scrapeJobClass') if driver else None

    @property
    def scrapeActions(self):
        return getattr(self.scrapeJobClass, 'actions', [])

    def isDriverHeadless(self):
        driver = self.robustClass.worker.driverManager.drivers.get(self.scrapeuuid)
        return bool(driver and driver.get('headless'))

    def bindWidgets(self):
        self.jobsGroupBox = self.robustClass.jobsGroupBox
        self.statusLabel = self.robustClass.statusLabel
        self.addJobButton = self.robustClass.addJobButton
        self.saveOrderButton = self.robustClass.saveOrderButton
        self.jobsContainer = self.robustClass.jobsContainer
        self.jobsContainerLayout = self.robustClass.jobsContainerLayout
        self.oneJob = self.robustClass.oneJob

    def setupUi(self):
        self.bindWidgets()
        prev = getattr(self.robustClass, 'activeJobsArea', None)
        if prev is not None and prev is not self:
            prev.deactivate()
        if not getattr(self.robustClass, '_jobsTemplateRemoved', False):
            if self.oneJob is not None:
                self.oneJob.deleteLater()
            self.robustClass._jobsTemplateRemoved = True
            self.robustClass.oneJob = None
            self.oneJob = None
        self.initiateVariables()
        self.attachSaveOrderEffect()
        self.robustClass.activeJobsArea = self
        self._rowsStale = False
        self.initiateSavedJobs(self.scrapeActions)
        self.jobsGroupBox.setTitle(f"Driver {self.driverNumber} Jobs")
        self.statusLabel.setText(self.jobsFor)
        self.connectChrome()
        # The save-order button is shared, so its enabled state must be claimed, not inherited.
        self.currentActions = self.scrapeActions
        self.evaluateJobsOrderChange()

    def attachSaveOrderEffect(self):
        # Shared saveOrderButton deletes the previous effect on setGraphicsEffect.
        self.opaceEffect = QGraphicsOpacityEffect()
        self.opaceEffect.setOpacity(0)
        self.saveOrderButton.setGraphicsEffect(self.opaceEffect)

    def activate(self):
        if getattr(self.robustClass, 'activeJobsArea', None) is self:
            if self._rowsStale:
                self.rebuildRows()
            return
        prev = getattr(self.robustClass, 'activeJobsArea', None)
        if prev is not None:
            prev.deactivate()
        self.bindWidgets()
        self.robustClass.activeJobsArea = self
        self.attachSaveOrderEffect()
        self.jobsGroupBox.setTitle(f"Driver {self.driverNumber} Jobs")
        self.statusLabel.setText(self.jobsFor)
        self.connectChrome()
        if self._rowsStale:
            self.rebuildRows()
            return
        for jobWidget in self.jobRowWidgets:
            jobWidget.setParent(self.jobsContainer)
            self.jobsContainerLayout.addWidget(jobWidget)
        self.syncExecutionCheckboxes()
        self.currentActions = self.scrapeActions
        self.evaluateJobsOrderChange()

    def setScrapeJob(self, jobsFor):
        self.forceCancelPick()
        self.jobsFor = jobsFor or ""
        self.markRowsStale()

    def renameScrapeJob(self, jobsFor):
        self.jobsFor = jobsFor
        if self.isActive():
            self.statusLabel.setText(self.jobsFor)

    def markRowsStale(self):
        self._rowsStale = True
        if self.isActive():
            self.rebuildRows()

    def rebuildRows(self):
        # Rows are parented into the main window's shared jobsContainer, so they can only
        # be built while this area owns it; otherwise rebuild lazily on the next activate().
        if not self.isActive():
            self._rowsStale = True
            return
        self.forceCancelPick()
        self._rowsStale = False
        for jobWidget in self.jobRowWidgets:
            self.jobsContainerLayout.removeWidget(jobWidget)
            jobWidget.setParent(None)
            jobWidget.deleteLater()
        self.jobRowWidgets = []
        self.nextJobNumber = 1
        self.newjobflag = True
        self.nextsavedjobuuid = None
        self.initialActions = []
        self.currentActions = []
        self.currentJobs = []
        self.draggedJob = None
        self.draggedAction = None
        self.dragUUID = None
        self.dragNextJob = None
        self.dragPreviousJob = None
        self.initiateSavedJobs(self.scrapeActions)
        self.jobsGroupBox.setTitle(f"Driver {self.driverNumber} Jobs")
        self.statusLabel.setText(self.jobsFor)
        self.currentActions = self.scrapeActions
        self.evaluateJobsOrderChange()

    def deactivate(self):
        self.forceCancelPick()
        self.disconnectChrome()
        self.syncJobRowWidgetsFromLayout()
        for jobWidget in self.jobRowWidgets:
            self.jobsContainerLayout.removeWidget(jobWidget)
            jobWidget.setParent(self._stash)
        if getattr(self.robustClass, 'activeJobsArea', None) is self:
            self.robustClass.activeJobsArea = None

    def cleanup(self):
        wasActive = getattr(self.robustClass, 'activeJobsArea', None) is self
        self.forceCancelPick()
        if wasActive:
            self.deactivate()
            self.jobsGroupBox.setTitle("Jobs")
            self.statusLabel.setText("")
            if getattr(self, 'opaceEffect', None) is not None:
                self.opaceEffect.setOpacity(0)
            self.saveOrderButton.setEnabled(False)
        for jobWidget in self.jobRowWidgets:
            jobWidget.deleteLater()
        self.jobRowWidgets = []

    def syncJobRowWidgetsFromLayout(self):
        if getattr(self.robustClass, 'activeJobsArea', None) is not self:
            return
        rows = []
        for i in range(self.jobsContainerLayout.count()):
            widget = self.jobsContainerLayout.itemAt(i).widget()
            if widget is not None:
                rows.append(widget)
        self.jobRowWidgets = rows

    def syncExecutionCheckboxes(self):
        for action in self.scrapeActions:
            kwargs = action[1]
            jobuuid = kwargs.get("uuid")
            isexecuted = kwargs.get("isexecuted", False)
            jobWidget = self.findJobWidget(jobuuid)
            if not jobWidget:
                continue
            doneCheckBox = jobWidget.findChild(QtWidgets.QCheckBox, "doneCheckBox" + str(jobuuid))
            if doneCheckBox:
                doneCheckBox.setChecked(isexecuted)

    def findJobWidget(self, jobuuid):
        objectName = "oneJob" + str(jobuuid)
        for jobWidget in self.jobRowWidgets:
            if jobWidget.objectName() == objectName:
                return jobWidget
        return None

    def isActive(self):
        return getattr(self.robustClass, 'activeJobsArea', None) is self

    def setPickButtonArmed(self, button, armed):
        if self.armedPickButton is not None and self.armedPickButton is not button:
            try:
                self.armedPickButton.setStyleSheet("")
            except RuntimeError:
                pass
        if button is None:
            self.armedPickButton = None
            self.armedJobUuid = None
            return
        button.setStyleSheet("background-color: #ADD8E6;" if armed else "")
        if armed:
            self.armedPickButton = button
        else:
            if self.armedPickButton is button:
                self.armedPickButton = None
                self.armedJobUuid = None

    def pollPickResult(self):
        if not self.armedJobUuid:
            self.pickPollTimer.stop()
            return
        driver = self.robustClass.worker.driverManager.drivers.get(self.scrapeuuid)
        if not driver or driver.get('dropped'):
            self.forceCancelPick(sendCancel=False)
            return
        # A poll round trip can outlast the timer interval, so never stack a
        # second one behind a pending task; otherwise the queue grows unbounded
        # and the picker keeps answering long after the user moved on.
        if not driver['threadQueue'].empty():
            return
        driver['threadQueue'].put(("elementPickPoll", {"jobuuid": self.armedJobUuid}))

    def forceCancelPick(self, sendCancel=True):
        wasArmed = self.armedJobUuid is not None
        jobuuid = self.armedJobUuid
        if sendCancel and wasArmed:
            driver = self.robustClass.worker.driverManager.drivers.get(self.scrapeuuid)
            if driver and not driver.get('dropped'):
                driver['threadQueue'].put(("elementPickCancel", {"jobuuid": jobuuid}))
        self.pickPollTimer.stop()
        if self.armedPickButton is not None:
            self.setPickButtonArmed(self.armedPickButton, False)
        self.armedJobUuid = None

    def togglePickHandle(self, button=None):
        if button is None:
            button = self.jobsGroupBox.sender()
        if button is None:
            return
        jobWidget = button.parent()
        jobuuid = jobWidget.property("uuid")
        if not jobuuid:
            name = jobWidget.objectName() or ""
            if name.startswith("oneJob"):
                jobuuid = name.replace("oneJob", "", 1)
        if not jobuuid:
            self.setStatusMessage("Save or select a job row first")
            return
        if self.isDriverHeadless():
            self.setStatusMessage("Pick unavailable in headless mode")
            return
        rowUuid = str(jobuuid)
        jobTypeSelector = jobWidget.findChild(QtWidgets.QComboBox, "jobTypeSelector" + rowUuid)
        if jobTypeSelector and jobTypeSelector.currentText() == "Get URL":
            self.setStatusMessage("Pick not used for Get URL jobs")
            return
        driver = self.robustClass.worker.driverManager.drivers.get(self.scrapeuuid)
        if not driver or driver.get('dropped'):
            return

        if self.armedPickButton is button and self.armedJobUuid:
            self.forceCancelPick(sendCancel=True)
            self.setStatusMessage("Pick cancelled")
            return

        if self.armedJobUuid:
            self.forceCancelPick(sendCancel=True)

        self.armedJobUuid = rowUuid
        self.setPickButtonArmed(button, True)
        driver['threadQueue'].put(("elementPickStart", {"jobuuid": self.armedJobUuid}))
        if not self.pickPollTimer.isActive():
            self.pickPollTimer.start()
        self.setStatusMessage("Picking element… Esc or Cancel to stop")

    def applyPickedLocator(self, jobuuid, locatorType, locatorValue, locatorContext=None, verified=True, error=""):
        self.pickPollTimer.stop()
        if self.armedPickButton is not None:
            self.setPickButtonArmed(self.armedPickButton, False)
        self.armedJobUuid = None
        if not jobuuid:
            return
        jobWidget = self.findJobWidget(jobuuid)
        if not jobWidget:
            # also try property match
            for w in self.jobRowWidgets:
                if str(w.property("uuid")) == str(jobuuid) or w.objectName() == "oneJob" + str(jobuuid):
                    jobWidget = w
                    break
        if not jobWidget:
            self.setStatusMessage("Picked element but job row not found")
            return
        by_value = IDENTIFIER_VALUES.get(locatorType)
        typeSelector = jobWidget.findChild(QtWidgets.QComboBox, "identifierTypeSelector" + str(jobuuid))
        valueBox = jobWidget.findChild(QtWidgets.QLineEdit, "identifierValueBox" + str(jobuuid))
        # object names use the row uuid from creation
        if typeSelector is None or valueBox is None:
            rowUuid = jobWidget.objectName().replace("oneJob", "", 1) if jobWidget.objectName() else str(jobuuid)
            typeSelector = jobWidget.findChild(QtWidgets.QComboBox, "identifierTypeSelector" + rowUuid)
            valueBox = jobWidget.findChild(QtWidgets.QLineEdit, "identifierValueBox" + rowUuid)
        if typeSelector is not None and by_value is not None:
            idx = typeSelector.findData(by_value)
            if idx >= 0:
                typeSelector.setCurrentIndex(idx)
            else:
                typeSelector.setCurrentText(locatorType)
        self.setRowLocatorContext(jobWidget, locatorContext)
        if valueBox is not None:
            valueBox.setText(locatorValue or "")
        if not verified:
            self.setStatusMessage("Locator applied but did not resolve: " + (error or "unknown reason"))
            return
        scope = self.describeLocatorContext(locatorContext)
        self.setStatusMessage(
            ("Locator applied (" + scope + ") — Save the job to keep it")
            if scope else "Locator applied — Save the job to keep it"
        )

    def setRowLocatorContext(self, jobWidget, locatorContext):
        if jobWidget is None:
            return
        if locatorContext:
            jobWidget.setProperty("locatorContext", json.dumps(locatorContext))
        else:
            jobWidget.setProperty("locatorContext", None)

    def getRowLocatorContext(self, jobWidget):
        if jobWidget is None:
            return None
        raw = jobWidget.property("locatorContext")
        if not raw:
            return None
        try:
            context = json.loads(raw)
        except (TypeError, ValueError):
            return None
        return context if isinstance(context, dict) and context else None

    def describeLocatorContext(self, locatorContext):
        if not isinstance(locatorContext, dict):
            return ""
        parts = []
        frames = locatorContext.get("frames") or []
        if frames:
            names = [str(frame.get("selector") or ("frame[" + str(frame.get("index")) + "]")) for frame in frames]
            parts.append("in " + " > ".join(names))
        hosts = locatorContext.get("hosts") or []
        if hosts:
            parts.append("shadow " + " > ".join(str(host) for host in hosts))
        return ", ".join(parts)

    def onPickCancelled(self, jobuuid=None, error=""):
        if self.armedJobUuid is None and self.armedPickButton is None:
            return
        if jobuuid is not None and self.armedJobUuid is not None and str(jobuuid) != str(self.armedJobUuid):
            return
        self.pickPollTimer.stop()
        if self.armedPickButton is not None:
            self.setPickButtonArmed(self.armedPickButton, False)
        self.armedJobUuid = None
        if self.isActive():
            self.setStatusMessage(("Pick failed: " + error) if error else "Pick cancelled")

    def resetStatusLabel(self):
        if self.isActive() and self.statusLabel:
            self.statusLabel.setText(self.jobsFor)
            self.resetLabelTimer.stop()

    def setStatusMessage(self, message):
        if not self.isActive():
            return
        self.statusLabel.setText(message)
        if not self.resetLabelTimer.isActive():
            self.resetLabelTimer.start()

    def initiateSavedJobs(self, actions=None):
        if actions is None:
            return
        self.newjobflag = False
        for job in actions:
            kwargs = job[1]
            jobuuid = kwargs.get("uuid")
            self.nextsavedjobuuid = jobuuid
            self.initialActions.append(job)
            if kwargs.get("jobtype") == "GetUrl":
                url = kwargs.get("url")
                isexecuted = kwargs.get("isexecuted", False)
                self.addJobHandle()
                lastJobWidget = self.jobRowWidgets[-1]
                lastJobWidget.setProperty("uuid", jobuuid)
                jobTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "jobTypeSelector" + str(jobuuid))
                jobTypeSelector.setCurrentText("Get URL")
                valueBox = lastJobWidget.findChild(QtWidgets.QLineEdit, "valueBox" + str(jobuuid))
                valueBox.setText(url)
                doneCheckBox = lastJobWidget.findChild(QtWidgets.QCheckBox, "doneCheckBox" + str(jobuuid))
                doneCheckBox.setChecked(isexecuted)
            elif kwargs.get("jobtype") == "ClickButton":
                identifierType = kwargs.get("button_identifier")
                identifierValue = kwargs.get("identifier_value")
                isexecuted = kwargs.get("isexecuted", False)
                self.addJobHandle()
                lastJobWidget = self.jobRowWidgets[-1]
                lastJobWidget.setProperty("uuid", jobuuid)
                jobTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "jobTypeSelector" + str(jobuuid))
                jobTypeSelector.setCurrentText("Click Button")
                identifierTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "identifierTypeSelector" + str(jobuuid))
                identifierTypeSelector.setCurrentIndex(identifierTypeSelector.findData(identifierType))
                identifierValueBox = lastJobWidget.findChild(QtWidgets.QLineEdit, "identifierValueBox" + str(jobuuid))
                identifierValueBox.setText(identifierValue)
                self.setRowLocatorContext(lastJobWidget, kwargs.get("context"))
                doneCheckBox = lastJobWidget.findChild(QtWidgets.QCheckBox, "doneCheckBox" + str(jobuuid))
                doneCheckBox.setChecked(isexecuted)
            elif kwargs.get("jobtype") == "InputField":
                identifierType = kwargs.get("field_identifier")
                identifierValue = kwargs.get("identifier_value")
                value = kwargs.get("value")
                isexecuted = kwargs.get("isexecuted", False)
                self.addJobHandle()
                lastJobWidget = self.jobRowWidgets[-1]
                lastJobWidget.setProperty("uuid", jobuuid)
                jobTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "jobTypeSelector" + str(jobuuid))
                jobTypeSelector.setCurrentText("Input Field")
                identifierTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "identifierTypeSelector" + str(jobuuid))
                identifierTypeSelector.setCurrentIndex(identifierTypeSelector.findData(identifierType))
                identifierValueBox = lastJobWidget.findChild(QtWidgets.QLineEdit, "identifierValueBox" + str(jobuuid))
                identifierValueBox.setText(identifierValue)
                self.setRowLocatorContext(lastJobWidget, kwargs.get("context"))
                valueBox = lastJobWidget.findChild(QtWidgets.QLineEdit, "valueBox" + str(jobuuid))
                valueBox.setText(value)
                doneCheckBox = lastJobWidget.findChild(QtWidgets.QCheckBox, "doneCheckBox" + str(jobuuid))
                doneCheckBox.setChecked(isexecuted)
                doneCheckBox.setObjectName("doneCheckBox" + str(jobuuid))
            elif kwargs.get("jobtype") == "ExtractText":
                identifierType = kwargs.get("text_identifier")
                identifierValue = kwargs.get("identifier_value")
                isexecuted = kwargs.get("isexecuted", False)
                self.addJobHandle()
                lastJobWidget = self.jobRowWidgets[-1]
                lastJobWidget.setProperty("uuid", jobuuid)
                jobTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "jobTypeSelector" + str(jobuuid))
                jobTypeSelector.setCurrentText("Extract Text")
                identifierTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "identifierTypeSelector" + str(jobuuid))
                identifierTypeSelector.setCurrentIndex(identifierTypeSelector.findData(identifierType))
                identifierValueBox = lastJobWidget.findChild(QtWidgets.QLineEdit, "identifierValueBox" + str(jobuuid))
                identifierValueBox.setText(identifierValue)
                self.setRowLocatorContext(lastJobWidget, kwargs.get("context"))
                doneCheckBox = lastJobWidget.findChild(QtWidgets.QCheckBox, "doneCheckBox" + str(jobuuid))
                doneCheckBox.setChecked(isexecuted)
            elif kwargs.get("jobtype") == "ExtractLinks":
                identifierType = kwargs.get("link_identifier")
                identifierValue = kwargs.get("identifier_value")
                isexecuted = kwargs.get("isexecuted", False)
                self.addJobHandle()
                lastJobWidget = self.jobRowWidgets[-1]
                lastJobWidget.setProperty("uuid", jobuuid)
                jobTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "jobTypeSelector" + str(jobuuid))
                jobTypeSelector.setCurrentText("Extract Links")
                identifierTypeSelector = lastJobWidget.findChild(QtWidgets.QComboBox, "identifierTypeSelector" + str(jobuuid))
                identifierTypeSelector.setCurrentIndex(identifierTypeSelector.findData(identifierType))
                identifierValueBox = lastJobWidget.findChild(QtWidgets.QLineEdit, "identifierValueBox" + str(jobuuid))
                identifierValueBox.setText(identifierValue)
                self.setRowLocatorContext(lastJobWidget, kwargs.get("context"))
                doneCheckBox = lastJobWidget.findChild(QtWidgets.QCheckBox, "doneCheckBox" + str(jobuuid))
                doneCheckBox.setChecked(isexecuted)
        self.newjobflag = True

    def updateJobExecutionStatus(self, jobuuid, direction, result):
        if result == "End of actions":
            self.setStatusMessage("No more actions to execute.")
            return
        if result == "Previous Done":
            self.setStatusMessage("No more previous actions to execute.")
            return
        jobWidget = self.findJobWidget(jobuuid)
        if jobWidget:
            checkBox = jobWidget.findChild(QtWidgets.QCheckBox, "doneCheckBox" + str(jobuuid))
            if checkBox:
                if direction == "forward":
                    checkBox.setChecked(True)
                elif direction == "backward":
                    checkBox.setChecked(False)
            jobName = jobWidget.findChild(QtWidgets.QLabel)
            if jobName:
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

    def connectChrome(self):
        if self._chromeConnected:
            return
        self.addJobButton.clicked.connect(self.addJobHandle)
        self.saveOrderButton.clicked.connect(self.saveOrderHandle)
        self.jobsContainer.mousePressEvent = self.handleJobPress
        self.jobsContainer.mouseMoveEvent = self.handleJobMove
        self.jobsContainer.mouseReleaseEvent = self.handleJobRelease
        self._chromeConnected = True

    def disconnectChrome(self):
        if not self._chromeConnected:
            return
        try:
            self.addJobButton.clicked.disconnect(self.addJobHandle)
        except TypeError:
            pass
        try:
            self.saveOrderButton.clicked.disconnect(self.saveOrderHandle)
        except TypeError:
            pass
        # The container is shared, so leaving these bound would feed drag events to a stashed area.
        self.jobsContainer.mousePressEvent = lambda event: None
        self.jobsContainer.mouseMoveEvent = lambda event: None
        self.jobsContainer.mouseReleaseEvent = lambda event: None
        self._chromeConnected = False

    def saveOrderHandle(self):
        self.setStatusMessage("Saving Order...")
        self.saveOrderButton.setEnabled(False)
        with open("./resources/jobs.json", "r") as f:
            jobsFile = json.load(f)
        jobsDict: dict = jobsFile['jobs']
        jobs = jobsDict.get(self.jobsFor)
        if not jobs:
            self.setStatusMessage("No scrape job selected to save order for")
            return
        for job in jobs:
            for action in self.currentActions:
                if job[1]['uuid'] == action[1]['uuid']:
                    job[1]['position'] = self.currentActions.index(action)
                    break
        with open("./resources/jobs.json", 'w') as f:
            json.dump(jobsFile, f)
        self.syncJobRowWidgetsFromLayout()
        for index, jobWidget in enumerate(self.jobRowWidgets):
            jobName = jobWidget.findChild(QtWidgets.QLabel)
            jobName.setText(f"Job {index + 1}")
        self.initialActions = []
        for action in self.currentActions:
            self.initialActions.append(action)
        self.setStatusMessage("Current Order Saved")
        self.opaceEffect.setOpacity(0)
        self.robustClass.refreshSiblingDrivers(self.jobsFor, exceptUuid=self.scrapeuuid)

    def deleteJobHandle(self):
        button = self.jobsGroupBox.sender()
        jobWidget = button.parent()
        jobuuid = jobWidget.property("uuid")
        if not jobuuid:
            name = jobWidget.objectName() or ""
            if name.startswith("oneJob"):
                jobuuid = name.replace("oneJob", "", 1)
        if jobuuid and self.armedJobUuid and str(jobuuid) == str(self.armedJobUuid):
            self.forceCancelPick(sendCancel=True)
        if jobWidget in self.jobRowWidgets:
            self.jobRowWidgets.remove(jobWidget)
        jobWidget.deleteLater()
        jobuuid = jobWidget.property("uuid")
        scrapeJobClass = self.scrapeJobClass
        if scrapeJobClass is None:
            return
        scrapeJobClass.deleteJob(uuid=jobuuid, owner=self.jobsFor)
        self.robustClass.refreshSiblingDrivers(self.jobsFor, exceptUuid=self.scrapeuuid)

    def ensureArtifactButton(self, oneJob, oneJobLayout, jobUUID):
        existing = oneJob.findChild(QtWidgets.QPushButton, "artifactButton" + str(jobUUID))
        if existing:
            return
        artifactButton = QtWidgets.QPushButton(oneJob)
        artifactButton.setMaximumSize(QtCore.QSize(30, 16777215))
        artifactButton.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("./resources/document.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        artifactButton.setIcon(icon)
        artifactButton.setObjectName("artifactButton" + str(jobUUID))
        artifactButton.clicked.connect(self.openJobContentHandle)
        oneJobLayout.addWidget(artifactButton)

    def removeArtifactButton(self, oneJob, jobUUID):
        artifactButton = oneJob.findChild(QtWidgets.QPushButton, "artifactButton" + str(jobUUID))
        if artifactButton:
            artifactButton.deleteLater()

    def openJobContentHandle(self):
        button = self.jobsGroupBox.sender()
        jobWidget = button.parent()
        jobuuid = jobWidget.property("uuid")
        content = ""
        if jobuuid:
            for action in self.scrapeActions:
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
        self.jobContentDialogClass = JobArtifactConstruct(content)
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
        self.dragNextJob = self.currentJobs[draggedJobIndex + 1] if (draggedJobIndex + 1) < len(self.currentJobs) else None
        self.nextJobYLine = self.dragNextJob.pos().y() + self.dragNextJob.size().height() / 2 if self.dragNextJob else 0

    def updateDragPreviousJob(self):
        draggedJobIndex = self.currentJobs.index(self.draggedJob)
        self.dragPreviousJob = self.currentJobs[draggedJobIndex - 1] if (draggedJobIndex - 1) > -1 else None
        self.previousJobYLine = self.dragPreviousJob.pos().y() + self.dragPreviousJob.size().height() / 2 if self.dragPreviousJob else 0

    def handleJobPress(self, event):
        button = event.button()
        if button != Qt.LeftButton:
            return
        click_y = event.pos().y()
        self.currentJobs = [self.jobsContainerLayout.itemAt(i).widget() for i in range(self.jobsContainerLayout.count())]
        self.currentActions = self.scrapeActions
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
        if self.draggedJob is None:
            return
        if len(self.currentActions) < len(self.currentJobs):
            self.setStatusMessage("Save New Jobs First To Reorder")
            return
        drag_y = event.pos().y()
        direction = (drag_y - self.previousDragPoint) > 0
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
                self.jobRowWidgets = list(self.currentJobs)
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
                self.jobRowWidgets = list(self.currentJobs)
                self.jobsContainerLayout.activate()
                self.updateDragNextJob()
                self.updateDragPreviousJob()
                self.evaluateJobsOrderChange()
        self.previousDragPoint = drag_y

    def handleJobRelease(self, event):
        button = event.button()
        if button != Qt.LeftButton:
            return
        if self.draggedJob is None:
            return
        for job in self.jobRowWidgets:
            jobName = job.findChild(QtWidgets.QLabel)
            if jobName:
                jobName.setCursor(Qt.OpenHandCursor)
        if self.draggedJob in self.currentJobs:
            idx = self.currentJobs.index(self.draggedJob)
            self.jobsContainerLayout.insertWidget(idx, self.draggedJob)
            self.syncJobRowWidgetsFromLayout()
        self.draggedJob = None

    def addJobHandle(self):
        if self.newjobflag:
            newJobUUID = str(uuid.uuid4())
        else:
            newJobUUID = self.nextsavedjobuuid
        oneJob = QtWidgets.QWidget(self.jobsContainer)
        oneJob.setMinimumSize(QtCore.QSize(0, 0))
        oneJob.setObjectName("oneJob" + str(newJobUUID))
        oneJobLayout = QtWidgets.QHBoxLayout(oneJob)
        oneJobLayout.setObjectName("oneJobLayout" + newJobUUID)
        jobName = QtWidgets.QLabel(oneJob)
        jobName.setObjectName("jobName" + str(newJobUUID))
        jobName.setMinimumSize(QtCore.QSize(40, 30))
        jobName.setCursor(Qt.OpenHandCursor)
        oneJobLayout.addWidget(jobName)
        jobTypeSelector = QtWidgets.QComboBox(oneJob)
        jobTypeSelector.setObjectName("jobTypeSelector" + str(newJobUUID))
        self.initiateJobTypeOptions(jobTypeSelector)
        jobTypeSelector.setMinimumSize(QtCore.QSize(80, 0))
        jobTypeSelector.setMaximumSize(QtCore.QSize(80, 16777215))
        oneJobLayout.addWidget(jobTypeSelector)
        identifierTypeSelector = QtWidgets.QComboBox(oneJob)
        identifierTypeSelector.setObjectName("identifierTypeSelector" + str(newJobUUID))
        identifierTypeSelector.setDisabled(True)
        identifierTypeSelector.setMinimumSize(QtCore.QSize(80, 0))
        identifierTypeSelector.setMaximumSize(QtCore.QSize(80, 16777215))
        self.initiateIdentifierTypeOptions(identifierTypeSelector)
        oneJobLayout.addWidget(identifierTypeSelector)
        identifierValueBox = QtWidgets.QLineEdit(oneJob)
        identifierValueBox.setObjectName("identifierValueBox" + str(newJobUUID))
        identifierValueBox.setPlaceholderText("Identifier Value")
        identifierValueBox.setDisabled(True)
        # A hand written locator must not inherit the frame or shadow scope of a
        # previously picked one, or it would be looked up in the wrong document.
        identifierValueBox.textEdited.connect(lambda _text, w=oneJob: self.setRowLocatorContext(w, None))
        oneJobLayout.addWidget(identifierValueBox)
        valueBox = QtWidgets.QLineEdit(oneJob)
        valueBox.setObjectName("valueBox" + str(newJobUUID))
        valueBox.setPlaceholderText("Value")
        oneJobLayout.addWidget(valueBox)
        jobPickButton = QtWidgets.QPushButton(oneJob)
        jobPickButton.setText("")
        pickIcon = QtGui.QIcon()
        pickIcon.addPixmap(QtGui.QPixmap("./resources/mycursor.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        jobPickButton.setIcon(pickIcon)
        jobPickButton.setObjectName("jobPickButton" + str(newJobUUID))
        jobPickButton.setEnabled(False)
        jobPickButton.clicked.connect(lambda _checked=False, b=jobPickButton: self.togglePickHandle(b))
        oneJobLayout.addWidget(jobPickButton)
        doneCheckBox = QtWidgets.QCheckBox(oneJob)
        doneCheckBox.setObjectName("doneCheckBox" + str(newJobUUID))
        doneCheckBox.setEnabled(False)
        oneJobLayout.addWidget(doneCheckBox)
        saveJobButton = QtWidgets.QPushButton(oneJob)
        saveJobButton.setMaximumSize(QtCore.QSize(50, 16777215))
        saveJobButton.setObjectName("saveJobButton" + str(newJobUUID))
        saveJobButton.setText("Save")

        def saveJobHandle():
            jobType = jobTypeSelector.currentText()
            identifierType = identifierTypeSelector.currentData() if identifierTypeSelector.isEnabled() else None
            identifierValue = identifierValueBox.text() if identifierValueBox.isEnabled() else None
            value = valueBox.text() if valueBox.isEnabled() else None
            locatorContext = self.getRowLocatorContext(oneJob)
            if jobType == "Get URL":
                if not value.startswith(("http://", "https://")):
                    self.setStatusMessage("Invalid URL format. Please include http:// or https://")
                    return
                else:
                    oneJob.setProperty("uuid", newJobUUID)
                    doneCheckBox.setObjectName("doneCheckBox" + str(newJobUUID))
                    saveMsg = self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].addGetUrlJob(url=value, owner=self.jobsFor, uuid=newJobUUID)
                    self.setStatusMessage(saveMsg)
            elif jobType == "Click Button":
                if not identifierType or not identifierValue:
                    self.setStatusMessage("Please fill in all required fields for Click Button job.")
                    return
                else:
                    oneJob.setProperty("uuid", newJobUUID)
                    doneCheckBox.setObjectName("doneCheckBox" + str(newJobUUID))
                    saveMsg = self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].addClickButtonJob(button_identifier=identifierType, identifier_value=identifierValue, context=locatorContext, owner=self.jobsFor, uuid=newJobUUID)
                    self.setStatusMessage(saveMsg)
            elif jobType == "Input Field":
                if not identifierType or not identifierValue or not value:
                    self.setStatusMessage("Please fill in all required fields for Input Field job.")
                    return
                else:
                    oneJob.setProperty("uuid", newJobUUID)
                    doneCheckBox.setObjectName("doneCheckBox" + str(newJobUUID))
                    saveMsg = self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].addInputFieldJob(field_identifier=identifierType, identifier_value=identifierValue, value=value, context=locatorContext, owner=self.jobsFor, uuid=newJobUUID)
                    self.setStatusMessage(saveMsg)
            elif jobType == "Extract Text":
                if not identifierType or not identifierValue:
                    self.setStatusMessage("Please fill in all required fields for Extract Text job.")
                    return
                else:
                    oneJob.setProperty("uuid", newJobUUID)
                    doneCheckBox.setObjectName("doneCheckBox" + str(newJobUUID))
                    saveMsg = self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].addExtractTextJob(text_identifier=identifierType, identifier_value=identifierValue, context=locatorContext, owner=self.jobsFor, uuid=newJobUUID)
                    self.setStatusMessage(saveMsg)
            elif jobType == "Extract Links":
                if not identifierType or not identifierValue:
                    self.setStatusMessage("Please fill in all required fields for Extract Links job.")
                    return
                else:
                    oneJob.setProperty("uuid", newJobUUID)
                    doneCheckBox.setObjectName("doneCheckBox" + str(newJobUUID))
                    saveMsg = self.robustClass.worker.driverManager.drivers[self.scrapeuuid]['scrapeJobClass'].addExtractLinksJob(link_identifier=identifierType, identifier_value=identifierValue, context=locatorContext, owner=self.jobsFor, uuid=newJobUUID)
                    self.setStatusMessage(saveMsg)
            self.robustClass.refreshSiblingDrivers(self.jobsFor, exceptUuid=self.scrapeuuid)

        saveJobButton.clicked.connect(saveJobHandle)
        oneJobLayout.addWidget(saveJobButton)
        deleteJobButton = QtWidgets.QPushButton(oneJob)
        deleteJobButton.setMaximumSize(QtCore.QSize(50, 16777215))
        deleteJobButton.setObjectName("deleteJobButton" + str(newJobUUID))
        deleteJobButton.setText("Delete")
        deleteJobButton.clicked.connect(self.deleteJobHandle)
        oneJobLayout.addWidget(deleteJobButton)
        self.jobsContainerLayout.addWidget(oneJob)
        self.jobRowWidgets.append(oneJob)
        jobName.setText("Job " + str(self.nextJobNumber))
        self.nextJobNumber += 1

        def jobTypeChangedHandle(text):
            canPick = text != "Get URL" and not self.isDriverHeadless()
            jobPickButton.setEnabled(canPick)
            if text == "Get URL":
                identifierTypeSelector.setDisabled(True)
                identifierValueBox.setDisabled(True)
                valueBox.setDisabled(False)
                self.removeArtifactButton(oneJob, newJobUUID)
                if self.armedPickButton is jobPickButton:
                    self.forceCancelPick(sendCancel=True)
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
        # Apply initial enable state for default job type
        jobTypeChangedHandle(jobTypeSelector.currentText())
