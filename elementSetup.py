from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QGraphicsOpacityEffect
from PyQt5 import QtWidgets

def setUpMiddleLine(middleLine: QWidget, robustClass):
    statusArea: QtWidgets.QTextBrowser = robustClass.statusArea
    scrollArea: QtWidgets.QScrollArea = robustClass.scrollArea
    body: QtWidgets.QVBoxLayout = robustClass.body
    minHeight = 100
    opcaityEffect = QGraphicsOpacityEffect()
    opcaityEffect.setOpacity(0.2)
    def handleLineMove(event):
        delta = event.pos().y()
        if delta == 0:
            return
        if delta > 0:  # dragging down → scrollArea shrinks, statusArea grows
            allowed = scrollArea.size().height() - minHeight
            delta = min(delta, allowed)
        else:          # dragging up → statusArea shrinks, scrollArea grows
            allowed = -(statusArea.size().height() - minHeight)
            delta = max(delta, allowed)
        scrollArea.resize(scrollArea.width(), scrollArea.height() - delta)
        scrollArea.move(scrollArea.pos().x(), scrollArea.pos().y() + delta)
        statusArea.resize(statusArea.width(), statusArea.height() + delta)
        middleLine.move(middleLine.pos().x(), middleLine.pos().y() + delta)
        robustClass.verticalLayout.activate()
        body.setStretch(0, statusArea.height()) 
        body.setStretch(2, scrollArea.height())  
    middleLine.setCursor(Qt.SizeVerCursor)
    middleLine.setGraphicsEffect(opcaityEffect)
    middleLine.mouseMoveEvent = handleLineMove