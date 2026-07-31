from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets


def setUpSplitters(robustClass):
    hSplitter: QtWidgets.QSplitter = robustClass.mainHorizontalSplitter
    vSplitter: QtWidgets.QSplitter = robustClass.controlVerticalSplitter
    minWidth = 500
    minHeight = 200

    robustClass.driverWindow.setMinimumWidth(minWidth)
    robustClass.controlPanel.setMinimumWidth(minWidth)
    robustClass.statusArea.setMinimumHeight(minHeight)
    robustClass.scrollArea.setMinimumHeight(minHeight)

    # DriverWindow absorbs window resize; controlPanel keeps its width unless user drags
    hSplitter.setStretchFactor(0, 1)
    hSplitter.setStretchFactor(1, 0)
    # scrollArea absorbs resize; statusArea keeps its height unless user drags
    vSplitter.setStretchFactor(0, 0)
    vSplitter.setStretchFactor(1, 1)

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

    if hSplitter.size().width() > 0:
        applyHorizontalSizes()
    else:
        QTimer.singleShot(0, applyHorizontalSizes)

    if vSplitter.size().height() > 0:
        applyVerticalSizes()
    else:
        QTimer.singleShot(0, applyVerticalSizes)

    robustClass.applyHorizontalSizes = applyHorizontalSizes
    robustClass.applyVerticalSizes = applyVerticalSizes
