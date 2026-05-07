from selenium import webdriver
import threading
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from collections import deque
import queue
from uuid import uuid4

class DriverManager(QObject):
    drivers:dict = {}
    threads:list = []
    status = pyqtSignal(dict)
    finished = pyqtSignal(dict)
    counter = 0
    appClosed = False

    def __init__(self):
        super().__init__()
        self.createTimer = QTimer()
        self.createTimer.setInterval(500)
        self.createTimer.timeout.connect(self.processNextDriverCreate)
        self.createQueue = deque()
        
    def createDriver(self, isHidden):
        print("Creating Driver " + str(self.counter))
        driverUUID = uuid4()
        self.status.emit({"type":"driverCreating","uuid":driverUUID})
        options = webdriver.ChromeOptions()
        if isHidden:
            options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)
        threadQueue = queue.Queue()
        oneDriver = {"driver":driver,"dropped":False,"threadQueue":threadQueue,"uuid":driverUUID}
        self.drivers[driverUUID] = oneDriver
        if self.appClosed:
            self.createTimer.stop()
            print("App Closed Before Driver " + str(driverUUID) + " Ready. Closing Driver.")
            driver.quit()
            return
        self.status.emit({"type":"driverReady","uuid":driverUUID})
        if len(self.drivers) == self.counter:
            self.finished.emit({"msg":"All Drivers Ready","type":"allDriversReady"})
        while True:
            task = threadQueue.get()
            try:
                driver.current_url
            except:
                self.status.emit({"type":"driverDied","uuid":driverUUID})
                break
            if task == "close":
                driver.quit()
                break
            func , kwargs = task
            if func == "assignNumber":
                driver.execute_script("document.title = 'Driver " + str(kwargs['number']) + "'")
            else:
                result, jobuuid, direction = func()
                self.status.emit({"type":"driverResult", "result":result, "uuid":driverUUID, "jobuuid": jobuuid, "direction": direction})
            threadQueue.task_done()

    def constructDrivers(self, count, isHidden):
        self.createTimer.start()
        for _ in range(count):
            driverThread = threading.Thread(target=self.createDriver, args=(isHidden,))
            self.threads.append(driverThread)
            self.createQueue.append(driverThread)
            self.counter += 1
        if not self.createTimer.isActive():
            self.createTimer.start()
        

    def processNextDriverCreate(self):
        if self.createQueue:
            driverThread = self.createQueue.popleft()
            driverThread.start()
        else:
            self.createTimer.stop()
