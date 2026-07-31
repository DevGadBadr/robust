from selenium import webdriver
import threading
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from collections import deque
import queue
from uuid import uuid4
import psutil
import win32gui
import win32process
import win32con

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
        
    def createDriver(self, isHeadless, isHidden):
        driverUUID = uuid4()
        self.status.emit({"type":"driverCreating","uuid":driverUUID})
        options = webdriver.ChromeOptions()
        if isHeadless:
            options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)
        driverpid = driver.service.process.pid
        chromePid = self.getChromeWindowPid(driverpid)
        hwnd = self.findHWND(chromePid) if chromePid else None
        if isHidden:
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
        threadQueue = queue.Queue()
        oneDriver = {"driver":driver,"dropped":False,"threadQueue":threadQueue,"uuid":driverUUID,"pid":driverpid,"chromePid":chromePid,"HWND":hwnd,"visible": not isHidden}
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
                result, jobuuid, direction, artifact = func()
                self.status.emit({"type":"driverResult", "result":result, "artifact":artifact, "uuid":driverUUID, "jobuuid": jobuuid, "direction": direction})
            threadQueue.task_done()

    def constructDrivers(self, count, isHeadless, isHidden):
        self.createTimer.start()
        for _ in range(count):
            driverThread = threading.Thread(target=self.createDriver, args=(isHeadless,isHidden,))
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

    def getChromeWindowPid(self, driver_pid):
        driver_process = psutil.Process(driver_pid)
        children = driver_process.children(recursive=True)
        for child in children:
            if child.name() == "chrome.exe":
                return child.pid
        return None

    def findHWND(self, target_pid):
        # Get all PIDs in the chrome process tree
        try:
            proc = psutil.Process(target_pid)
            all_pids = set([target_pid] + [c.pid for c in proc.children(recursive=True)])
        except psutil.NoSuchProcess:
            return None
        found = []
        def callback(hwnd, _):
            if win32gui.GetParent(hwnd) != 0:
                return
            _ , pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid in all_pids:
                title = win32gui.GetWindowText(hwnd)
                if title:  # only windows with a title
                    found.append(hwnd)
        win32gui.EnumWindows(callback, None)
        # Return the largest window (most likely the main browser window)
        if not found:
            return None
        return max(found, key=lambda h: win32gui.GetWindowRect(h)[2] * win32gui.GetWindowRect(h)[3])