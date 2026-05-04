from selenium import webdriver
import threading
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import queue
from uuid import uuid4

options = webdriver.ChromeOptions()
options.add_argument("--headless")

class DriverManager(QObject):
    drivers:dict = {}
    threads:list = []
    status = pyqtSignal(dict)
    finished = pyqtSignal(dict)
    counter = 0

    def createDriver(self):
        driverUUID = uuid4()
        self.status.emit({"type":"driverCreating","uuid":driverUUID})
        driver = webdriver.Chrome(options=options)
        threadQueue = queue.Queue()
        oneDriver = {"driver":driver,"dropped":False,"threadQueue":threadQueue,"uuid":driverUUID}
        self.drivers[driverUUID] = oneDriver
        self.status.emit({"type":"driverReady","uuid":driverUUID})
        if len(self.drivers) == self.counter:
            self.finished.emit({"msg":"All Drivers Ready","type":"allDriversReady"})
        while True:
            task = threadQueue.get()
            try:
                driver.current_url
            except:
                break
            if task == "close":
                driver.close()
                break
            func , kwargs = task
            if func == "assignNumber":
                driver.execute_script("document.title = 'Driver " + str(kwargs['number']) + "'")
            else:
                func()
            threadQueue.task_done()

    def constructDrivers(self,count):
        for _ in range(count):
            driverThread = threading.Thread(target=self.createDriver)
            self.threads.append(driverThread)
            driverThread.start()
            self.counter += 1