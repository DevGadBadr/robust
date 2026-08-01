from robustConstruct import RobustConstruct
from PyQt5.QtWidgets import QApplication, QDialog, QMainWindow
import sys

class RobustMain(RobustConstruct):

    def setupUi(self, dialog:QDialog):
        super().setupUi(dialog)

if __name__ == "__main__":
    if not 'fusion' in sys.argv:
        QApplication.setStyle('Fusion')
    app = QApplication(sys.argv)
    mainDialog = QMainWindow()
    applicationClass = RobustMain()
    applicationClass.setupUi(mainDialog)
    applicationClass.restoreWindowGeometry()
    sys.exit(app.exec())
