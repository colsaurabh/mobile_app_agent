"""
Generic device controller that provides a unified interface
for controlling both Android and iOS devices.
"""
from config import load_config

configs = load_config()

# Platform detection and controller imports
def _detect_platform(device):
    """Detect if device is Android or iOS based on device identifier."""
    # Android devices typically have alphanumeric serials
    # iOS devices typically have UUID format or can be detected via Appium
    # For now, we'll use a simple heuristic or config
    platform = configs.get("PLATFORM", "android").lower()
    return platform

def list_all_devices():
    """
    List all available devices (Android and iOS).
    Returns a list of device identifiers.
    """
    platform = configs.get("PLATFORM", "android").lower()
    
    if platform == "ios":
        from ios_controller import IOSController
        return IOSController.list_all_devices()
    else:
        from android_controller import AndroidController
        return AndroidController.list_all_devices()


class DeviceController:
    """
    Generic device controller that delegates to platform-specific implementations.
    """
    def __init__(self, device, platform=None):
        """
        Initialize the device controller.
        
        Args:
            device: Device identifier (Android serial or iOS UDID)
            platform: Platform type ("android" or "ios"). If None, auto-detects.
        """
        if platform is None:
            platform = _detect_platform(device)
        
        platform = platform.lower()
        
        if platform == "ios":
            from ios_controller import IOSController
            self.controller = IOSController(device)
        else:
            from android_controller import AndroidController
            self.controller = AndroidController(device)
        
        self.device = device
        self.platform = platform
    
    def get_device_size(self):
        """Get device screen dimensions (width, height)."""
        return self.controller.get_device_size()
    
    def get_screenshot(self, prefix, save_dir):
        """Capture and save a screenshot."""
        return self.controller.get_screenshot(prefix, save_dir)
    
    def get_xml(self, prefix, save_dir):
        """Get UI hierarchy XML dump."""
        return self.controller.get_xml(prefix, save_dir)
    
    def tap(self, x, y):
        """Tap at coordinates (x, y)."""
        return self.controller.tap(x, y)
    
    def text(self, input_str):
        """Input text string."""
        return self.controller.text(input_str)
    
    def text_replace(self, input_str):
        """Input text string."""
        return self.controller.text_replace(input_str)

    def long_press(self, x, y, duration=1000):
        """Long press at coordinates (x, y) for duration milliseconds."""
        return self.controller.long_press(x, y, duration)
    
    def swipe(self, x, y, direction, dist="medium", quick=False):
        """Swipe from (x, y) in direction."""
        return self.controller.swipe(x, y, direction, dist, quick)
    
    def swipe_precise(self, start, end, duration=400):
        """Precise swipe from start coordinates to end coordinates."""
        return self.controller.swipe_precise(start, end, duration)
    
    def back(self):
        """Send back button event."""
        return self.controller.back()
