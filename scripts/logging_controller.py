from enum import Enum
from datetime import datetime

from colorama import Fore, Style
import sys

from config import load_config
try:
    configs = load_config()
except Exception as e:
    logger.error(f"ERROR: Failed to load configuration: {e}")
    sys.exit(1)

def print_with_color(text: str, color=""):
    if color == "red":
        print(Fore.RED + text)
    elif color == "green":
        print(Fore.GREEN + text)
    elif color == "yellow":
        print(Fore.YELLOW + text)
    elif color == "blue":
        print(Fore.BLUE + text)
    elif color == "magenta":
        print(Fore.MAGENTA + text)
    elif color == "cyan":
        print(Fore.CYAN + text)
    elif color == "white":
        print(Fore.WHITE + text)
    elif color == "black":
        print(Fore.BLACK + text)
    else:
        print(text)
    print(Style.RESET_ALL)

# Logger instance (will be initialized after config load)
logger = None

def init_logger(mode="prod"):
    """Initialize logger"""
    global logger
    # If mode not provided, try to get from config
    if mode == "prod":
        try:
            from config import load_config
            configs = load_config()
            mode = configs.get("LOG_MODE", "prod")
        except Exception:
            pass  # Use default mode
    
    logger = Logger(mode)
    return logger

def get_logger():
    """Get logger instance"""
    global logger
    if logger is None:
        logger = init_logger()
    return logger

class LogLevel(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    SHOW = 4

class Logger:
    def __init__(self, mode="prod"):
        self.mode = mode
        self.is_dev = mode.lower() == "dev"
        self.is_stage = mode.lower() == "stage"
        self.is_prod = mode.lower() == "prod"
        
    def _should_print(self, level: str):
        """Determine if message should be printed based on mode"""
        if self.is_dev:
            return True  # Show everything in development
        elif self.is_stage:
            return level in ["INFO", "WARNING", "ERROR", "SHOW"]
        elif self.is_prod:
            return level in ["SHOW"]

    def _should_log(self, level: str):
        """Determine if message should be logged based on mode"""
        if self.is_dev:
            return True  # Log everything in development
        
        # Production mode: log "INFO", "WARNING", "ERROR", "SHOW" messages
        return level in ["INFO", "WARNING", "ERROR", "SHOW"]

    def _get_timestamp(self):
        """Get formatted timestamp"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def debug(self, text: str, color="yellow"):
        """Debug messages (only shown in development mode)"""
        if self._should_print("DEBUG"):
            timestamp = self._get_timestamp()
            print_with_color(f"[{timestamp}] {text}", color)
    
    def info(self, text: str, color="green"):
        """Info messages (only shown in development mode)"""
        if self._should_print("INFO"):
            timestamp = self._get_timestamp()
            print_with_color(f"[{timestamp}] {text}", color)
    
    def warning(self, text: str, color="magenta"):
        """Warning messages (only shown in development mode)"""
        if self._should_print("WARNING"):
            timestamp = self._get_timestamp()
            print_with_color(f"[{timestamp}] {text}", color)
    
    def error(self, text: str, color="red"):
        """Error messages (only shown in development mode)"""
        if self._should_print("ERROR"):
            timestamp = self._get_timestamp()
            print_with_color(f"[{timestamp}] {text}", color)

    def show(self, text: str, color="blue", sender="system"):
        """Show messages (shown in production mode)"""
        if self._should_print("SHOW"):
            timestamp = self._get_timestamp()
            print_with_color(f"[{timestamp}] {text}", color)

            if configs.get("ENABLE_CHAT_INTERFACE", False):
                try:
                    import socket, json
                    msg = json.dumps({"text": text, "sender": sender}).encode()
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect(("127.0.0.1", 5055))
                    s.sendall(msg)
                    s.close()
                except Exception as e:
                    pass








    # def question(self, text: str, color="blue"):
    #     """Questions asked to user (always shown - essential for production)"""
    #     self.info(text, color)
    
    # def answer(self, text: str, color="cyan"):
    #     """User answers (always shown - essential for production)"""
    #     self.info(f"Answer: {text}", color)
    
    # def action(self, text: str, color="green"):
    #     """Actions taken (shown in dev, essential actions in prod)"""
    #     if self.is_dev:
    #         print_with_color(text, color)
    #     # In production, might want to show only key actions
    #     # For now, we'll hide most actions in production
    
    # def round_info(self, text: str, color="yellow"):
    #     """Round information (only in development)"""
    #     self.debug(text, color)
    
    # def llm_response(self, observation: str, thought: str, action: str, summary: str, readable: str):
    #     """LLM response parsing (only in development)"""
    #     self.debug(f"Observation: => {observation}", "magenta")
    #     self.debug(f"Thought: => {thought}", "magenta")
    #     self.debug(f"Action: => {action}", "green")
    #     self.debug(f"Summary: => {summary}", "magenta")
    #     self.debug(f"ReadableSummarisation: => {readable}", "magenta")


