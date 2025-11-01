"""
Android-specific device controller implementation using ADB.
"""
import os
import subprocess
import sys

from config import load_config
from logging_controller import get_logger

configs = load_config()

try:
    logger = get_logger()
except Exception as e:
    print(f"ERROR: Failed to load logger configuration: {e}")
    sys.exit(1)


def execute_adb(adb_command):
    """Execute an ADB command and return the result."""
    result = subprocess.run(adb_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    logger.error(f"Command execution failed: {adb_command}")
    logger.error(result.stderr)
    return "ERROR"


class AndroidController:
    """Android device controller using ADB commands."""
    
    @staticmethod
    def list_all_devices():
        """List all connected Android devices."""
        adb_command = "adb devices"
        device_list = []
        result = execute_adb(adb_command)
        if result != "ERROR":
            devices = result.split("\n")[1:]
            for d in devices:
                if d.strip():  # Skip empty lines
                    device_list.append(d.split()[0])
        return device_list
    
    def __init__(self, device):
        self.device = device
        self.screenshot_dir = configs["ANDROID_SCREENSHOT_DIR"]
        self.xml_dir = configs["ANDROID_XML_DIR"]
        self.width, self.height = self.get_device_size()
        self.backslash = "\\"
    
    def get_device_size(self):
        """Get Android device screen dimensions."""
        adb_command = f"adb -s {self.device} shell wm size"
        result = execute_adb(adb_command)
        if result != "ERROR":
            return map(int, result.split(": ")[1].split("x"))
        return 0, 0
    
    def get_screenshot(self, prefix, save_dir):
        """Capture and pull screenshot from Android device."""
        cap_command = f"adb -s {self.device} shell screencap -p " \
                      f"{os.path.join(self.screenshot_dir, prefix + '.png').replace(self.backslash, '/')}"
        pull_command = f"adb -s {self.device} pull " \
                       f"{os.path.join(self.screenshot_dir, prefix + '.png').replace(self.backslash, '/')} " \
                       f"{os.path.join(save_dir, prefix + '.png')}"
        result = execute_adb(cap_command)
        if result != "ERROR":
            result = execute_adb(pull_command)
            if result != "ERROR":
                return os.path.join(save_dir, prefix + ".png")
            return result
        return result
    
    def get_xml(self, prefix, save_dir):
        """Get UI hierarchy XML dump from Android device."""
        dump_command = f"adb -s {self.device} shell uiautomator dump " \
                       f"{os.path.join(self.xml_dir, prefix + '.xml').replace(self.backslash, '/')}"
        pull_command = f"adb -s {self.device} pull " \
                       f"{os.path.join(self.xml_dir, prefix + '.xml').replace(self.backslash, '/')} " \
                       f"{os.path.join(save_dir, prefix + '.xml')}"
        result = execute_adb(dump_command)
        if result != "ERROR":
            result = execute_adb(pull_command)
            if result != "ERROR":
                return os.path.join(save_dir, prefix + ".xml")
            return result
        return result
    
    def back(self):
        """Send Android back button event."""
        adb_command = f"adb -s {self.device} shell input keyevent KEYCODE_BACK"
        ret = execute_adb(adb_command)
        return ret
    
    def tap(self, x, y):
        """Tap at coordinates (x, y) on Android device."""
        adb_command = f"adb -s {self.device} shell input tap {x} {y}"
        ret = execute_adb(adb_command)
        return ret
    
    def text(self, input_str):
        """Input text on Android device."""
        input_str = input_str.replace(" ", "%s")
        input_str = input_str.replace("'", "")
        adb_command = f"adb -s {self.device} shell input text {input_str}"
        ret = execute_adb(adb_command)
        return ret
    
    def long_press(self, x, y, duration=1000):
        """Long press at coordinates (x, y) on Android device."""
        adb_command = f"adb -s {self.device} shell input swipe {x} {y} {x} {y} {duration}"
        ret = execute_adb(adb_command)
        return ret
    
    def swipe(self, x, y, direction, dist="medium", quick=False):
        """Swipe from (x, y) in direction on Android device."""
        unit_dist = int(self.width / 10)
        if dist == "long":
            unit_dist *= 3
        elif dist == "medium":
            unit_dist *= 2
        if direction == "up":
            offset = 0, -2 * unit_dist
        elif direction == "down":
            offset = 0, 2 * unit_dist
        elif direction == "left":
            offset = -1 * unit_dist, 0
        elif direction == "right":
            offset = unit_dist, 0
        else:
            return "ERROR"
        duration = 200 if quick else 400
        adb_command = f"adb -s {self.device} shell input swipe {x} {y} {x+offset[0]} {y+offset[1]} {duration}"
        ret = execute_adb(adb_command)
        return ret
    
    def swipe_precise(self, start, end, duration=400):
        """Precise swipe from start to end coordinates on Android device."""
        start_x, start_y = start
        end_x, end_y = end
        adb_command = f"adb -s {self.device} shell input swipe {start_x} {start_y} {end_x} {end_y} {duration}"
        ret = execute_adb(adb_command)
        return ret
