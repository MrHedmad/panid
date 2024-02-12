import logging

from logging import StreamHandler

from colorama import Back, Fore, Style, init

__version__ = "0.1.0"
__all__ = ["__version__"]

init() # Init colorama

class ColorFormatter(logging.Formatter):
    # Change this dictionary to suit your coloring needs!
    COLORS = {
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "DEBUG": Style.BRIGHT + Fore.MAGENTA,
        "INFO": Fore.GREEN,
        "CRITICAL": Style.BRIGHT + Fore.RED,
    }

    def format(self, record):
        reset = Fore.RESET + Back.RESET + Style.NORMAL
        color = self.COLORS.get(record.levelname, "")
        if color:
            record.name = Style.BRIGHT + Fore.BLUE + record.name + reset
            if record.levelname != "INFO":
                record.msg = color + record.msg + reset
            record.levelname = color + record.levelname + reset
        return logging.Formatter.format(self, record)


# Setup logging
log = logging.getLogger("panid")  # Keep this at the module level name
log.setLevel(logging.DEBUG)  # Keep this at DEBUG - set levels in handlers themselves
log.propagate = False

format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
console_formatter = ColorFormatter(format)

stream_h = StreamHandler()
stream_h.setFormatter(console_formatter)
stream_h.setLevel(logging.INFO)

log.addHandler(stream_h)
