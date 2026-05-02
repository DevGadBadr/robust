from robustConstruct import RobustConstruct
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QDialog


class RobustDialog(RobustConstruct):
    def __init__(self):
        super().__init__()

    def setupUi(self, RobustDialog):
        super().setupUi(RobustDialog)

    
if __name__ == "__main__":
    app = QApplication([])
    mainDialog = QDialog()
    applicationClass = RobustDialog()
    applicationClass.setupUi(mainDialog)
    mainDialog.show()
    app.exec()