import win32gui, win32con, time, ctypes
from PIL import ImageGrab
import os

os.chdir(r"C:\NOCPing")

hwnd = win32gui.FindWindow(None, "NOCPing")
ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
ctypes.windll.user32.SetForegroundWindow(hwnd)
time.sleep(1.0)

cx, cy = win32gui.ClientToScreen(hwnd, (0, 0))
rect = win32gui.GetWindowRect(hwnd)
l, t, r, b = rect

u32 = ctypes.windll.user32

def click(x, y):
    u32.SetCursorPos(x, y)
    time.sleep(0.2)
    u32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.1)
    u32.mouse_event(0x0004, 0, 0, 0, 0)

def snap(path):
    time.sleep(1.0)
    img = ImageGrab.grab(bbox=(l, t, r, b))
    img.save(path)

tabs = [("screenshots/monitor.png", 63), ("screenshots/portscan.png", 158),
        ("screenshots/banner.png", 260), ("screenshots/traceroute.png", 380),
        ("screenshots/mtr.png", 470)]

for path, tx in tabs:
    click(cx + tx, cy + 46)
    snap(path)
