from itertools import count
import threading

from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialog
from uirobust import Ui_RobustDialog
from PyQt5.QtCore import Qt
from workerThread import QWorker

class RobustConstruct(Ui_RobustDialog):

    def __init__(self):
        super().__init__()

    def setupUi(self, RobustDialog:QDialog):
        super().setupUi(RobustDialog)
        RobustDialog.setWindowFlags(RobustDialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        RobustDialog.setWindowFlags(RobustDialog.windowFlags() | Qt.WindowMinimizeButtonHint)
        self.initiateVariables()
        self.connectActions()
        self.initiateWorker()

    def initiateVariables(self):
        self.numberOfDrivers = 1
        self.nextDriverNumber = 1
        self.nextReadyDriverNumber = 1

    def connectActions(self):
        self.slider.valueChanged.connect(self.castSliderChange)
        self.startButton.clicked.connect(self.createDrivers)

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
            self.statusArea.append(event['msg'] + str(self.nextDriverNumber))
            self.nextDriverNumber += 1

        if event['type'] == "driverReady":
            self.worker.driverManager.drivers[event['uuid']]['number'] = self.nextReadyDriverNumber
            self.worker.driverManager.drivers[event['uuid']]['driver'].execute_script("document.title = 'Driver " + str(self.nextReadyDriverNumber) + "'")
            self.statusArea.append(event['msg'] + str(self.nextReadyDriverNumber) + " Ready")
            self.createDriverInstances(self.nextReadyDriverNumber,event['uuid'])
            self.nextReadyDriverNumber += 1

    def QThreadFinished(self,event):
        self.startButton.setDisabled(False)

    def closeDriverInstance(self,uuid):
        driverNumber = self.worker.driverManager.drivers[uuid]['number']
        print("Closing Driver " + str(driverNumber))
        self.worker.driverManager.drivers[uuid]['threadQueue'].put("close")
        driverInstance = self.scrollAreaWidgetContents.findChild(QtWidgets.QWidget,"driverInstance"+str(uuid))
        driverInstance.deleteLater()
        self.statusArea.append("Driver " + str(driverNumber) + " Closed")
        self.worker.driverManager.drivers[uuid]['dropped'] = True

    def closeAllDrivers(self):
        for uuid,driver in self.worker.driverManager.drivers.items():
            if not driver['dropped']:
                self.closeDriverInstance(uuid)

    def createDriverInstances(self,number,uuid):
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
        closeDriver = QtWidgets.QPushButton(driverInstance)
        closeDriver.setMaximumSize(QtCore.QSize(100, 16777215))
        closeDriver.setObjectName("closeDriver"+str(uuid))
        closeDriver.setText("Close")
        closeDriver.clicked.connect(lambda:self.closeDriverInstance(uuid))
        instanceLayout.addWidget(closeDriver)
        spacerItem4 = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        instanceLayout.addItem(spacerItem4)
        self.instancesContainerLayout.addWidget(driverInstance)


        