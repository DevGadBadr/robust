from selenium import webdriver
import threading
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from collections import deque
import queue
from uuid import uuid4
import psutil
from selenium.common import SessionNotCreatedException
import win32gui
import win32process
import win32con
import elementPicker


# Consecutive failed polls tolerated while trying to restore a picker that a
# navigation wiped, before the pick is given up on.
MAX_PICK_RECOVERIES = 20


class DriverManager(QObject):
    drivers: dict = {}
    threads: list = []
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
        self.status.emit({"type": "driverCreating", "uuid": driverUUID})
        options = webdriver.ChromeOptions()
        if isHeadless:
            options.add_argument("--headless")
        try:
            driver = webdriver.Chrome(options=options)
        except SessionNotCreatedException:
            self.status.emit({"type": "driverCreationFailed", "uuid": driverUUID, "error": "Session not created"})
            return
        driverpid = driver.service.process.pid
        chromePid = self.getChromeWindowPid(driverpid)
        hwnd = self.findHWND(chromePid) if chromePid and not isHeadless else None
        # Hidden checkbox used to hide external Chrome; for embed we unhide before parenting.
        if hwnd and isHidden and not isHeadless:
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
        threadQueue = queue.Queue()
        oneDriver = {
            "driver": driver,
            "dropped": False,
            "threadQueue": threadQueue,
            "uuid": driverUUID,
            "pid": driverpid,
            "chromePid": chromePid,
            "HWND": hwnd,
            "visible": True,
            "embedded": False,
            "headless": isHeadless,
            "pickArmed": False,
            "pickJobUuid": None,
            "pickRecoveries": 0,
        }
        self.drivers[driverUUID] = oneDriver
        if self.appClosed:
            self.createTimer.stop()
            print("App Closed Before Driver " + str(driverUUID) + " Ready. Closing Driver.")
            driver.quit()
            return
        self.status.emit({"type": "driverReady", "uuid": driverUUID, "headless": isHeadless})
        if len(self.drivers) == self.counter:
            self.finished.emit({"msg": "All Drivers Ready", "type": "allDriversReady"})
        while True:
            task = threadQueue.get()
            try:
                driver.current_url
            except Exception:
                self.status.emit({"type": "driverDied", "uuid": driverUUID})
                break
            if task == "close":
                try:
                    elementPicker.cancel(driver)
                except Exception:
                    pass
                driver.quit()
                break

            func, kwargs = task
            if func == "assignNumber":
                driver.execute_script("document.title = 'Driver " + str(kwargs['number']) + "'")
            elif func == "elementPickStart":
                try:
                    elementPicker.start(driver, kwargs.get("jobuuid"))
                    oneDriver["pickArmed"] = True
                    oneDriver["pickJobUuid"] = kwargs.get("jobuuid")
                    oneDriver["pickRecoveries"] = 0
                except Exception as e:
                    oneDriver["pickArmed"] = False
                    oneDriver["pickJobUuid"] = None
                    self.status.emit({
                        "type": "elementPickCancelled",
                        "uuid": driverUUID,
                        "jobuuid": kwargs.get("jobuuid"),
                        "error": str(e),
                    })
            elif func == "elementPickCancel":
                try:
                    elementPicker.cancel(driver)
                except Exception:
                    pass
                oneDriver["pickArmed"] = False
                oneDriver["pickJobUuid"] = None
                self.status.emit({
                    "type": "elementPickCancelled",
                    "uuid": driverUUID,
                    "jobuuid": kwargs.get("jobuuid"),
                })
            elif func == "elementPickPoll":
                if not oneDriver.get("pickArmed"):
                    threadQueue.task_done()
                    continue
                try:
                    result = elementPicker.poll(driver)
                except Exception:
                    result = None
                if not result:
                    oneDriver["pickRecoveries"] = 0
                else:
                    status = result.get("status")
                    if status == "picked":
                        oneDriver["pickArmed"] = False
                        oneDriver["pickJobUuid"] = None
                        locatorType = result.get("type")
                        locatorValue = result.get("value")
                        locatorContext = result.get("context")
                        try:
                            verified, verifyError = elementPicker.verify(
                                driver, locatorType, locatorValue, locatorContext
                            )
                        except Exception as e:
                            verified, verifyError = False, str(e)
                        try:
                            elementPicker.cancel(driver)
                        except Exception:
                            pass
                        self.status.emit({
                            "type": "elementPicked",
                            "uuid": driverUUID,
                            "jobuuid": result.get("jobuuid"),
                            "locatorType": locatorType,
                            "locatorValue": locatorValue,
                            "locatorContext": locatorContext,
                            "verified": bool(verified),
                            "error": "" if verified else (verifyError or "locator did not resolve"),
                        })
                    elif status == "cancelled":
                        oneDriver["pickArmed"] = False
                        oneDriver["pickJobUuid"] = None
                        try:
                            elementPicker.cancel(driver)
                        except Exception:
                            pass
                        self.status.emit({
                            "type": "elementPickCancelled",
                            "uuid": driverUUID,
                            "jobuuid": result.get("jobuuid"),
                            "error": result.get("error", ""),
                        })
                    elif status == "lost":
                        # A navigation (or an early poll during one) wiped the
                        # in-page picker, so put it back instead of going quiet.
                        recoveries = oneDriver.get("pickRecoveries", 0) + 1
                        oneDriver["pickRecoveries"] = recoveries
                        jobuuid = oneDriver.get("pickJobUuid")
                        reArmError = None
                        if recoveries <= MAX_PICK_RECOVERIES:
                            try:
                                elementPicker.start(driver, jobuuid)
                            except Exception as e:
                                reArmError = str(e)
                        else:
                            reArmError = result.get("reason") or "picker could not be restored"
                        if reArmError and recoveries > MAX_PICK_RECOVERIES:
                            oneDriver["pickArmed"] = False
                            oneDriver["pickJobUuid"] = None
                            self.status.emit({
                                "type": "elementPickCancelled",
                                "uuid": driverUUID,
                                "jobuuid": jobuuid,
                                "error": reArmError,
                            })
            else:
                result, jobuuid, direction, artifact = func()
                screenshot = None
                if oneDriver.get("headless"):
                    try:
                        screenshot = driver.get_screenshot_as_png()
                    except Exception:
                        screenshot = None
                self.status.emit({
                    "type": "driverResult",
                    "result": result,
                    "artifact": artifact,
                    "screenshot": screenshot,
                    "uuid": driverUUID,
                    "jobuuid": jobuuid,
                    "direction": direction,
                })
            threadQueue.task_done()

    def constructDrivers(self, count, isHeadless, isHidden):
        self.createTimer.start()
        for _ in range(count):
            driverThread = threading.Thread(target=self.createDriver, args=(isHeadless, isHidden,))
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
        try:
            proc = psutil.Process(target_pid)
            all_pids = set([target_pid] + [c.pid for c in proc.children(recursive=True)])
        except psutil.NoSuchProcess:
            return None
        found = []

        def callback(hwnd, _):
            if win32gui.GetParent(hwnd) != 0:
                return
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid in all_pids:
                title = win32gui.GetWindowText(hwnd)
                if title:
                    found.append(hwnd)

        win32gui.EnumWindows(callback, None)
        if not found:
            return None
        return max(found, key=lambda h: win32gui.GetWindowRect(h)[2] * win32gui.GetWindowRect(h)[3])
