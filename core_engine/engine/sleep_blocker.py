import platform
import subprocess
from .logger import get_logger

logger = get_logger("sleep_blocker")

class PreventSystemSleep:
    """Context manager that communicates with the OS kernel to prevent sleep."""
    def __init__(self):
        self.os_type = platform.system()
        self.caffeinate_process = None

    def __enter__(self):
        try:
            if self.os_type == 'Windows':
                import ctypes
                # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
                # Forces Windows to keep the CPU running even if the screen is off/lid closed
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
                logger.info("Windows sleep prevention activated.")
            elif self.os_type == 'Darwin':
                # macOS 'caffeinate' command prevents idle sleep
                self.caffeinate_process = subprocess.Popen(['caffeinate', '-i'])
                logger.info("macOS sleep prevention activated.")
        except Exception as e:
            logger.warning(f"Could not activate sleep prevention: {e}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.os_type == 'Windows':
                import ctypes
                # Revert to standard ES_CONTINUOUS
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
                logger.info("Windows sleep prevention released.")
            elif self.os_type == 'Darwin' and self.caffeinate_process:
                self.caffeinate_process.terminate()
                logger.info("macOS sleep prevention released.")
        except Exception as e:
            logger.warning(f"Error releasing sleep prevention: {e}")
