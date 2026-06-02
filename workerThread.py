from PyQt5.QtCore import QThread
from drivers import DriverManager

class QWorker(QThread):

    driverManager = DriverManager()

    def run(self,driversCount, isHeadless, isHidden):
        self.driverManager.constructDrivers(driversCount, isHeadless, isHidden)
