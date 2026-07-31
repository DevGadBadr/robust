from ui.uijobContent import Ui_jobContentDialog
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication


class JobContentConstruct(Ui_jobContentDialog):
    def __init__(self, scraped_text=""):
        super().__init__()
        self.scraped_text = scraped_text

    def setupUi(self, jobContentDialog):
        super().setupUi(jobContentDialog)
        jobContentDialog.setWindowFlags(jobContentDialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        jobContentDialog.setWindowFlags(jobContentDialog.windowFlags() | Qt.WindowMinimizeButtonHint)
        jobContentDialog.setWindowTitle("Content")
        self.dialog = jobContentDialog
        self.textBrowser.setPlainText(self.scraped_text if self.scraped_text else "No content yet")
        self.connectActions()

    def connectActions(self):
        self.copyButton.clicked.connect(self.handleCopyButton)
        self.closeButton.clicked.connect(self.handleCloseButton)

    def handleCopyButton(self):
        QApplication.clipboard().setText(self.textBrowser.toPlainText())

    def handleCloseButton(self):
        self.dialog.close()
