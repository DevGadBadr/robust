from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets


def setUpSplitters(robustClass):
    hSplitter: QtWidgets.QSplitter = robustClass.mainHorizontalSplitter
    vSplitter: QtWidgets.QSplitter = robustClass.controlVerticalSplitter
    minWidth = 100
    minHeight = 100

    robustClass.driverWindow.setMinimumWidth(minWidth)
    robustClass.controlPanel.setMinimumWidth(minWidth)
    robustClass.statusArea.setMinimumHeight(minHeight)
    robustClass.scrollArea.setMinimumHeight(minHeight)

    for splitter in (hSplitter, vSplitter):
        splitter.setChildrenCollapsible(False)

    # driverWindow absorbs window resize; controlPanel keeps its width unless user drags
    hSplitter.setStretchFactor(0, 1)
    hSplitter.setStretchFactor(1, 0)
    vSplitter.setStretchFactor(0, 1)
    vSplitter.setStretchFactor(1, 1)

    # controlVerticalSplitter is item index 4 in verticalLayout
    # (after chooseLabel, head, defaultJob, createButton)
    robustClass.verticalLayout.setStretch(4, 1)

    def applyHorizontalSizes():
        controlWidth = getattr(robustClass, "controlPanelWidth", 500)
        total = hSplitter.size().width() or 1020
        driverWidth = max(total - controlWidth, robustClass.driverWindow.minimumWidth())
        hSplitter.setSizes([driverWidth, controlWidth])

    if hSplitter.size().width() > 0:
        applyHorizontalSizes()
    else:
        QTimer.singleShot(0, applyHorizontalSizes)
