"""Windows-specific bits. Everything degrades to a harmless no-op elsewhere so the app can be
developed and tested on other systems."""

import ctypes
import os
import subprocess
import sys

IS_WIN = sys.platform == "win32"

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "FocusCat"

GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000


def enable_dpi_awareness():
    """Stop Windows from blurry-upscaling us on high-DPI screens."""
    if not IS_WIN:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def work_area(root):
    """(left, top, right, bottom) of the primary screen minus the taskbar."""
    if IS_WIN:
        try:
            from ctypes import wintypes
            rect = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
                return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            pass
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


def _hwnd(root):
    return ctypes.windll.user32.GetParent(root.winfo_id())


def set_no_activate(root, enabled):
    """Clicking the cat shouldn't pull focus away from what you're doing (or out of Alt+Tab)."""
    if not IS_WIN:
        return
    try:
        user32 = ctypes.windll.user32
        hwnd = _hwnd(root)
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enabled:
            style |= WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        else:
            style &= ~WS_EX_NOACTIVATE
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    except Exception:
        pass


def set_click_through(root):
    """Let every click go through this window to whatever is underneath."""
    if not IS_WIN:
        return
    try:
        user32 = ctypes.windll.user32
        hwnd = _hwnd(root)
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    except Exception:
        pass


def launch_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    exe = sys.executable
    pythonw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pythonw):
        exe = pythonw
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "FocusCat.pyw")
    return f'"{exe}" "{script}"'


def get_autostart():
    if not IS_WIN:
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, RUN_NAME)
            return True
    except OSError:
        return False


def set_autostart(enabled):
    if not IS_WIN:
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(key, RUN_NAME)
            except FileNotFoundError:
                pass


def open_file(path):
    try:
        if IS_WIN:
            subprocess.Popen(["notepad.exe", path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass
