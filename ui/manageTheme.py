from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
import winreg
import ctypes

DarkPalette: QPalette = QPalette()
DarkPalette.setColor(QPalette.Window, QColor(53, 53, 53))
DarkPalette.setColor(QPalette.WindowText, Qt.white)
DarkPalette.setColor(QPalette.Base, QColor(25, 25, 25))
DarkPalette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
DarkPalette.setColor(QPalette.ToolTipBase, Qt.white)
DarkPalette.setColor(QPalette.ToolTipText, Qt.white)
DarkPalette.setColor(QPalette.Text, Qt.white)
DarkPalette.setColor(QPalette.Button, QColor(53, 53, 53))
DarkPalette.setColor(QPalette.ButtonText, Qt.white)
DarkPalette.setColor(QPalette.BrightText, Qt.red)
DarkPalette.setColor(QPalette.Link, QColor(42, 130, 218))
DarkPalette.setColor(QPalette.Highlight, QColor(42, 130, 218))
DarkPalette.setColor(QPalette.HighlightedText, Qt.black)

LightPalette: QPalette = QPalette()
LightPalette.setColor(QPalette.Window, QColor(240, 240, 240))
LightPalette.setColor(QPalette.WindowText, Qt.black)
LightPalette.setColor(QPalette.Base, QColor(255, 255, 255))
LightPalette.setColor(QPalette.AlternateBase, QColor(233, 233, 233))
LightPalette.setColor(QPalette.ToolTipBase, Qt.black)
LightPalette.setColor(QPalette.ToolTipText, Qt.black)
LightPalette.setColor(QPalette.Text, Qt.black)
LightPalette.setColor(QPalette.Button, QColor(240, 240, 240))
LightPalette.setColor(QPalette.ButtonText, Qt.black)
LightPalette.setColor(QPalette.BrightText, Qt.red)
LightPalette.setColor(QPalette.Link, QColor(42, 130, 218))
LightPalette.setColor(QPalette.Highlight, QColor(42, 130, 218))
LightPalette.setColor(QPalette.HighlightedText, Qt.white)


def isWindowsDarkMode():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0  # 0 = dark, 1 = light
    except FileNotFoundError:
        return False  # default to light if key missing


def enableDarkTitlebar(hwnd):
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    value = ctypes.c_int(1)
    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))

def enableLightTitlebar(hwnd):
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    value = ctypes.c_int(0)
    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))


def isDarkThemeActive():
    app = QApplication.instance()
    if app is None:
        return False
    return app.palette().color(QPalette.Window).lightness() < 128


def applyTitlebarToWidget(widget, dark=None):
    if widget is None:
        return
    if dark is None:
        dark = isDarkThemeActive()
    hwnd = int(widget.winId())
    if dark:
        enableDarkTitlebar(hwnd)
    else:
        enableLightTitlebar(hwnd)


def applyTitlebarToTopLevels(dark=None):
    if dark is None:
        dark = isDarkThemeActive()
    app = QApplication.instance()
    if app is None:
        return
    for widget in app.topLevelWidgets():
        if widget.isWindow():
            applyTitlebarToWidget(widget, dark)
