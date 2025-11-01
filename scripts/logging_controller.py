from enum import Enum
from utils import print_with_color

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
        
    def _should_print(self, level: str):
        """Determine if message should be printed based on mode"""
        if self.is_dev:
            return True  # Show everything in development
        
        # Production mode: only prints SHOW messages
        return level in ["SHOW"]

    def _should_log(self, level: str):
        """Determine if message should be logged based on mode"""
        if self.is_dev:
            return True  # Log everything in development
        
        # Production mode: log "INFO", "WARNING", "ERROR", "SHOW" messages
        return level in ["INFO", "WARNING", "ERROR", "SHOW"]
    
    def debug(self, text: str, color=""):
        """Debug messages (only shown in development mode)"""
        if self._should_print("DEBUG"):
            print_with_color(text, color)
    
    def info(self, text: str, color=""):
        """Info messages (only shown in development mode)"""
        if self._should_print("INFO"):
            print_with_color(text, color)
    
    def warning(self, text: str, color="yellow"):
        """Warning messages (only shown in development mode)"""
        if self._should_print("WARNING"):
            print_with_color(text, color)
    
    def error(self, text: str, color="red"):
        """Error messages (only shown in development mode)"""
        if self._should_print("ERROR"):
            print_with_color(text, color)

    def show(self, text: str, color="blue"):
        """Show messages (shown in production mode)"""
        if self._should_print("SHOW"):
            print_with_color(text, color)








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


