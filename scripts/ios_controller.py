"""
iOS-specific device controller implementation using Appium.
"""
import os
import time
from appium import webdriver
from appium.options.ios import XCUITestOptions
import sys
from logging_controller import get_logger

from config import load_config

configs = load_config()

try:
    logger = get_logger()
except Exception as e:
    print(f"ERROR: Failed to load logger configuration: {e}")
    sys.exit(1)

class IOSController:
    """iOS device controller using Appium."""
    
    @staticmethod
    def list_all_devices():
        """List all connected iOS devices."""
        # This would typically use 'xcrun xctrace list devices' or similar
        # For now, return devices from config or allow manual specification
        # Saurabh: ToDo: Correct this. Take it from device connected.
        ios_devices = configs.get("IOS_DEVICES", [])
        if isinstance(ios_devices, list):
            return ios_devices
        return []
    
    def __init__(self, device):
        self.device = device
        self.width, self.height = 0, 0
        self.driver = None
        self._initialize_driver()
        self.width, self.height = self.get_device_size()
    
    def __del__(self):
        """Cleanup: close driver connection."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def _initialize_driver(self):
        """Initialize Appium WebDriver for iOS device."""
        try:
            options = XCUITestOptions()
            options.platform_name = "iOS"
            options.device_name = configs.get("IOS_DEVICE_NAME", "iPhone")
            options.automation_name = "XCUITest"
            options.udid = self.device
            options.platform_version = configs.get("IOS_PLATFORM_VERSION", "17.0")
            options.new_command_timeout = 300
            
            # Optional bundle ID if needed
            if configs.get("IOS_BUNDLE_ID"):
                options.bundle_id = configs["IOS_BUNDLE_ID"]
                options.auto_launch = configs.get("IOS_AUTO_LAUNCH", False)
            
            appium_server = configs.get("APPIUM_SERVER", "http://localhost:4723")
            self.driver = webdriver.Remote(appium_server, options=options)
            time.sleep(2)  # Wait for connection
        except Exception as e:
            logger.error(f"Failed to initialize iOS driver: {e}")
            raise
    
    def get_device_size(self):
        """Get iOS device screen dimensions."""
        try:
            window_size = self.driver.get_window_size()
            return window_size['width'], window_size['height']
        except Exception as e:
            logger.error(f"Failed to get device size: {e}")
            return 0, 0
    
    def get_screenshot(self, prefix, save_dir):
        """Capture and save screenshot from iOS device."""
        try:
            screenshot_path = os.path.join(save_dir, prefix + ".png")
            self.driver.save_screenshot(screenshot_path)
            return screenshot_path
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return "ERROR"
    
    def get_xml(self, prefix, save_dir):
        """Get UI hierarchy XML dump from iOS device."""
        try:
            # Appium provides source as XML-like structure
            source = self.driver.page_source
            xml_path = os.path.join(save_dir, prefix + ".xml")
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(source)
            return xml_path
        except Exception as e:
            logger.error(f"Failed to get XML: {e}")
            return "ERROR"

    def tap(self, x, y):
        """Tap at coordinates (x, y) on iOS device."""
        try:
            self.driver.execute_script("mobile: tap", {"x": x, "y": y})
            return "OK"
        except Exception as e:
            logger.error(f"Failed to tap: {e}")
            return "ERROR"

    def text(self, input_str):
        """Input text on iOS device."""
        try:
            self.driver.execute_script("mobile: keys", {"keys": list(input_str)})
            return "OK"
        except Exception as e:
            logger.error(f"Failed to input text: {e}")
            return "ERROR"
    
    def swipe(self, x, y, direction, dist="medium", quick=False):
        """Swipe from (x, y) in direction on iOS device."""
        try:
            unit_dist = int(self.width / 10)
            if dist == "long":
                unit_dist *= 3
            elif dist == "medium":
                unit_dist *= 2
            
            if direction == "up":
                offset_x, offset_y = 0, -2 * unit_dist
            elif direction == "down":
                offset_x, offset_y = 0, 2 * unit_dist
            elif direction == "left":
                offset_x, offset_y = -1 * unit_dist, 0
            elif direction == "right":
                offset_x, offset_y = unit_dist, 0
            else:
                return "ERROR"
            
            # self.driver.execute_script("mobile: swipe", {
            #     "direction": "up",
            #     "velocity": 500
            # })

            duration_sec = (200 if quick else 400) / 1000.0
            self.driver.execute_script("mobile: dragFromToForDuration", {
                "fromX": x,
                "fromY": y,
                "toX": x + offset_x,
                "toY": y + offset_y,
                "duration": duration_sec
            })
            return "OK"
        except Exception as e:
            logger.error(f"Failed to swipe: {e}")
            return "ERROR"
    
    def swipe_precise(self, start, end, duration=400):
        """Precise swipe from start to end coordinates on iOS device."""
        try:
            start_x, start_y = start
            end_x, end_y = end
            duration_sec = duration / 1000.0
            self.driver.execute_script("mobile: dragFromToForDuration", {
                "fromX": start_x,
                "fromY": start_y,
                "toX": end_x,
                "toY": end_y,
                "duration": duration_sec,
            })
            return "OK"
        except Exception as e:
            logger.error(f"Failed to swipe precise: {e}")
            return "ERROR"

    def long_press(self, x, y, duration=5000):
        """Long press at coordinates (x, y) on iOS device."""
        try:
            self.driver.execute_script("mobile: touchAndHold", {
                "x": x,
                "y": y,
                "duration": duration / 1000.0  # Convert to seconds
            })
            return "OK"
        except Exception as e:
            logger.error(f"Failed to long press: {e}")
            return "ERROR"

    def back(self):
        """Send iOS back action (if available) or swipe from left edge."""
        try:
            # iOS doesn't have a universal back button, but we can try swipe from left
            self.driver.execute_script("mobile: swipe", {
                "direction": "right",
                "fromX": 0,
                "fromY": self.height // 2,
                "toX": self.width // 4,
                "toY": self.height // 2
            })
            return "OK"
        except Exception as e:
            logger.error(f"Failed to execute back: {e}")
            return "ERROR"
    


# Then update `scripts/and_controller.py` to maintain backward compatibility:

# ```python:scripts/and_controller.py
# """
# Backward compatibility wrapper for AndroidController.
# This file is kept for compatibility but new code should use device_controller.py
# """
# from scripts.device_controller import DeviceController, list_all_devices
# from scripts.android_controller import AndroidController

# # Re-export for backward compatibility
# __all__ = ['AndroidController', 'list_all_devices', 'AndroidElement']

# # Keep AndroidElement for backward compatibility
# class AndroidElement:
#     def __init__(self, uid, bbox, attrib):
#         self.uid = uid
#         self.bbox = bbox
#         self.attrib = attrib
# ```
