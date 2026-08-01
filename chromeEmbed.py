"""Embed / detach a Chrome HWND into a Qt host widget."""
import win32gui
import win32con
from PyQt5.QtCore import Qt


GWL_STYLE = -16
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000

_FRAME_STYLES = WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU


def _get_style(hwnd):
    return win32gui.GetWindowLong(hwnd, GWL_STYLE)


def _set_style(hwnd, style):
    win32gui.SetWindowLong(hwnd, GWL_STYLE, style)


def embedChrome(hwnd, hostWidget):
    if not hwnd or hostWidget is None:
        return False
    try:
        hostWidget.setAttribute(Qt.WA_NativeWindow, True)
        host_hwnd = int(hostWidget.winId())
        style = _get_style(hwnd)
        if hostWidget.property("_chromeOrigStyle") is None:
            hostWidget.setProperty("_chromeOrigStyle", style)
        style = (style | WS_CHILD) & ~WS_POPUP & ~_FRAME_STYLES
        _set_style(hwnd, style)
        win32gui.SetParent(hwnd, host_hwnd)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        resizeChrome(hwnd, hostWidget)
        return True
    except Exception:
        return False


def resizeChrome(hwnd, hostWidget):
    if not hwnd or hostWidget is None:
        return
    try:
        w = max(hostWidget.width(), 1)
        h = max(hostWidget.height(), 1)
        win32gui.MoveWindow(hwnd, 0, 0, w, h, True)
    except Exception:
        pass


def detachChrome(hwnd, orig_style=None):
    if not hwnd:
        return
    try:
        win32gui.SetParent(hwnd, 0)
        if orig_style is not None:
            _set_style(hwnd, orig_style)
        else:
            style = _get_style(hwnd)
            style = (style | _FRAME_STYLES | WS_POPUP) & ~WS_CHILD
            _set_style(hwnd, style)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    except Exception:
        pass
