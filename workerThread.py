from PyQt5.QtCore import QThread
from drivers import DriverManager

class QWorker(QThread):

    driverManager = DriverManager()

    def run(self,driversCount, isHidden):
        self.driverManager.constructDrivers(driversCount, isHidden)
