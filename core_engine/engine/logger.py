import logging
import sys

class EngineLogger:
    def __init__(self, name="engine", callback=None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Avoid duplicate handlers
        if not self.logger.handlers:
            # Console Handler
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.callback = callback

    def info(self, message):
        self.logger.info(message)
        if self.callback:
            self.callback(message)

    def error(self, message):
        self.logger.error(message)
        if self.callback:
            self.callback(f"ERROR: {message}")

    def warning(self, message):
        self.logger.warning(message)
        if self.callback:
            self.callback(f"WARNING: {message}")

def get_logger(name="engine", callback=None):
    return EngineLogger(name, callback)
