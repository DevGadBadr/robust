from robustConstruct import RobustConstruct
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow
import sys

# This is the entry point for the application

class RobustMain(RobustConstruct):

    def setupUi(self, mainWindow:QMainWindow):
        super().setupUi(mainWindow)

if __name__ == "__main__":
    if not 'fusion' in sys.argv:
        QApplication.setStyle('Fusion')
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("./resources/robust.png"))
    mainDialog = QMainWindow()
    applicationClass = RobustMain()
    applicationClass.setupUi(mainDialog)
    applicationClass.restoreWindowGeometry()
    sys.exit(app.exec())
