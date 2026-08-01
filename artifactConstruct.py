import html
from ui.uijobContent import Ui_jobContentDialog
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication


class JobArtifactConstruct(Ui_jobContentDialog):
    def __init__(self, content=""):
        super().__init__()
        self.content = content

    def setupUi(self, jobContentDialog):
        super().setupUi(jobContentDialog)
        jobContentDialog.setWindowFlags(jobContentDialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        jobContentDialog.setWindowFlags(jobContentDialog.windowFlags() | Qt.WindowMinimizeButtonHint)
        jobContentDialog.setWindowTitle("Content")
        self.dialog = jobContentDialog
        self.textBrowser.setOpenExternalLinks(True)
        if self.content:
            self.textBrowser.setHtml(self.contentToHtml(self.content))
        else:
            self.textBrowser.setPlainText("No content yet")
        self.connectActions()

    def connectActions(self):
        self.copyButton.clicked.connect(self.handleCopyButton)
        self.closeButton.clicked.connect(self.handleCloseButton)

    def handleCopyButton(self):
        QApplication.clipboard().setText(self.textBrowser.toPlainText())

    def handleCloseButton(self):
        self.dialog.close()

    def contentToHtml(self, content):
        parts = []
        for line in content.split("\n"):
            escaped = html.escape(line)
            if line.startswith("http://") or line.startswith("https://"):
                parts.append(f'<a href="{escaped}">{escaped}</a>')
            else:
                parts.append(escaped)
        return "<br>".join(parts)
