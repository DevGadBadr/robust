from robustConstruct import RobustConstruct
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QDialog
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
    mainDialog.show()
    sys.exit(app.exec())