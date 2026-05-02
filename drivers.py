from selenium import webdriver
import threading
from PyQt5.QtCore import QObject, pyqtSignal
import queue
from uuid import uuid4

class oneDriver:
    driver = None
    number: int = 0
    dropped: bool = False
    threadQueue: queue.Queue = None

class DriverManager(QObject):

    drivers:dict = {}
    threads:list = []
    status = pyqtSignal(dict)
    finished = pyqtSignal(dict)
    counter = 0

    def createDriver(self):
        driverUUID = uuid4()
        self.status.emit({"msg":"Creating driver ","type":"driverCreating","uuid":driverUUID})
        options = webdriver.ChromeOptions()
        # options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)
        threadQueue = queue.Queue()
        oneDriver:oneDriver = {"driver":driver,"dropped":False,"threadQueue":threadQueue}
        self.drivers[driverUUID] = oneDriver
        self.status.emit({"msg":"Driver ","type":"driverReady","uuid":driverUUID})
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
            func , args , kwargs = task
            func(driver,*args,**kwargs)
            threadQueue.task_done()

    def constructDrivers(self,count):
        for _ in range(count):
            driverThread = threading.Thread(target=self.createDriver)
            self.threads.append(driverThread)
            driverThread.start()
            self.counter += 1