from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget
from PyQt5 import QtWidgets

def setUpMiddleLine(middleLine: QWidget, robustClass):
    statusArea:QtWidgets.QTextBrowser = robustClass.statusArea
    scrollArea:QtWidgets.QScrollArea = robustClass.scrollArea
    minHeight = 200
    last_y = 0
    def handleLineMove(event):
        nonlocal last_y
        current_y = event.pos().y()
        print(current_y, last_y)
        direction = (current_y - last_y) > 0 # True for down move
        if direction:
            scrollArea.move(scrollArea.pos().x(), scrollArea.pos().y() + 1)
            scrollArea.resize(scrollArea.size().width(), scrollArea.size().height() - 1)
            middleLine.move(middleLine.pos().x(), middleLine.pos().y() + 1)
            statusArea.resize(statusArea.width(), statusArea.height() + 1)
            robustClass.verticalLayout.activate()
            last_y = current_y - 1
        else:
            statusArea.resize(statusArea.width(), statusArea.height() - 1)
            middleLine.move(middleLine.pos().x(), middleLine.pos().y() - 1)
            scrollArea.move(scrollArea.pos().x(), scrollArea.pos().y() - 1)    
            scrollArea.resize(scrollArea.size().width(), scrollArea.size().height() + 1)
            robustClass.verticalLayout.activate()  
            last_y = current_y + 1
    middleLine.setCursor(Qt.SizeVerCursor)
    middleLine.mouseMoveEvent = handleLineMove

