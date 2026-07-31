from robustConstruct import RobustConstruct
from PyQt5.QtWidgets import QApplication, QDialog
import sys

class RobustDialog(RobustConstruct):

    def setupUi(self, dialog:QDialog):
        super().setupUi(dialog)

if __name__ == "__main__":
    if not 'fusion' in sys.argv:
        QApplication.setStyle('Fusion')
    app = QApplication(sys.argv)
    mainDialog = QDialog()
    applicationClass = RobustDialog()
    applicationClass.setupUi(mainDialog)
    screen = QApplication.primaryScreen().geometry()
    x = screen.width() - mainDialog.width()
    y = (screen.height() - mainDialog.height() - 100) // 2
    mainDialog.move(x, y)
    mainDialog.show()
    sys.exit(app.exec())