from PyQt5.QtCore import QThread
from drivers import DriverManager

class QWorker(QThread):

    driverManager = DriverManager()

    def __init__(self):
        super().__init__()

    def run(self,driversCount):
        self.driverManager.constructDrivers(driversCount)