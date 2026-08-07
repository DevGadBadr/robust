from PyQt5.QtCore import QTimer, QVariantAnimation, Qt
from PyQt5 import QtWidgets
from PyQt5.QtGui import QPainter, QPixmap, QTransform


def setUpSplitters(robustClass):
    hSplitter: QtWidgets.QSplitter = robustClass.mainHorizontalSplitter
    vSplitter: QtWidgets.QSplitter = robustClass.controlVerticalSplitter
    jobsSplitter: QtWidgets.QSplitter = robustClass.jobsVerticalSplitter
    minWidth = 500
    minHeight = 100

    robustClass.driverWindow.setMinimumWidth(minWidth)
    robustClass.controlPanel.setMinimumWidth(minWidth)
    robustClass.statusArea.setMinimumHeight(minHeight)
    robustClass.scrollArea.setMinimumHeight(minHeight)
    # status + drivers each need minHeight
    robustClass.controlVerticalSplitter.setMinimumHeight(2 * minHeight)
    robustClass.jobsArea.setMinimumHeight(minHeight)

    # DriverWindow absorbs window resize; controlPanel keeps its width unless user drags
    hSplitter.setStretchFactor(0, 1)
    hSplitter.setStretchFactor(1, 0)
    # scrollArea absorbs resize; statusArea keeps its height unless user drags
    vSplitter.setStretchFactor(0, 0)
    vSplitter.setStretchFactor(1, 1)
    # control stack absorbs resize; jobsArea keeps its height unless user drags
    jobsSplitter.setStretchFactor(0, 1)
    jobsSplitter.setStretchFactor(1, 0)

    robustClass.verticalLayout.setStretch(4, 1)

    def applyHorizontalSizes():
        controlWidth = getattr(robustClass, "controlPanelWidth", 500)
        total = hSplitter.size().width() or 1020
        driverWidth = max(total - controlWidth, robustClass.driverWindow.minimumWidth())
        hSplitter.setSizes([driverWidth, controlWidth])

    def applyVerticalSizes():
        statusHeight = getattr(robustClass, "statusAreaHeight", 200)
        total = vSplitter.size().height() or 400
        scrollMin = robustClass.scrollArea.minimumHeight()
        statusMin = robustClass.statusArea.minimumHeight()
        statusHeight = max(min(statusHeight, total - scrollMin), statusMin)
        vSplitter.setSizes([statusHeight, total - statusHeight])

    def applyJobsVerticalSizes():
        jobsHeight = getattr(robustClass, "jobsAreaHeight", 200)
        total = jobsSplitter.size().height() or 400
        controlMin = robustClass.controlVerticalSplitter.minimumHeight()
        jobsMin = robustClass.jobsArea.minimumHeight()
        jobsHeight = max(min(jobsHeight, total - controlMin), jobsMin)
        jobsSplitter.setSizes([total - jobsHeight, jobsHeight])

    def applyAllSplitterSizes():
        applyHorizontalSizes()
        applyJobsVerticalSizes()
        applyVerticalSizes()

    sized = (
        hSplitter.size().width() > 0
        and vSplitter.size().height() > 0
        and jobsSplitter.size().height() > 0
    )
    if sized:
        applyAllSplitterSizes()
    else:
        QTimer.singleShot(0, applyAllSplitterSizes)

    robustClass.applyHorizontalSizes = applyHorizontalSizes
    robustClass.applyVerticalSizes = applyVerticalSizes
    robustClass.applyJobsVerticalSizes = applyJobsVerticalSizes
    robustClass.applyAllSplitterSizes = applyAllSplitterSizes

def setupSpinner(robustMainWindow):
    canvasSize = 30

    robustMainWindow.spinnerPixmap = QPixmap("./resources/spinner.png").scaled(
        canvasSize, canvasSize, Qt.KeepAspectRatio, Qt.SmoothTransformation
    )

    robustMainWindow.spinnerAnimation = QVariantAnimation()
    robustMainWindow.spinnerAnimation.setStartValue(0.0)
    robustMainWindow.spinnerAnimation.setEndValue(360.0)
    robustMainWindow.spinnerAnimation.setDuration(1000)  # 1 sec per rotation
    robustMainWindow.spinnerAnimation.setLoopCount(-1)   # infinite

    def rotate(angle):
        canvas = QPixmap(canvasSize, canvasSize)
        canvas.fill(Qt.transparent)

        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.translate(canvasSize / 2, canvasSize / 2)
        painter.rotate(angle)
        painter.translate(-robustMainWindow.spinnerPixmap.width() / 2,
                           -robustMainWindow.spinnerPixmap.height() / 2)
        painter.drawPixmap(0, 0, robustMainWindow.spinnerPixmap)
        painter.end()

        robustMainWindow.loadingLabel.setPixmap(canvas)

    robustMainWindow.spinnerAnimation.valueChanged.connect(rotate)

    def startSpinner():
        robustMainWindow.loadingLabel.setFixedSize(canvasSize, canvasSize)
        robustMainWindow.loadingLabel.setAlignment(Qt.AlignCenter)
        robustMainWindow.loadingLabel.show()
        robustMainWindow.spinnerAnimation.start()

    def stopSpinner():
        robustMainWindow.spinnerAnimation.stop()
        robustMainWindow.loadingLabel.hide()

    robustMainWindow.startSpinner = startSpinner
    robustMainWindow.stopSpinner = stopSpinner