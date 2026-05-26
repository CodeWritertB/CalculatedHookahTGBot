"""
Logging setup for the Hookah Shift Management Bot

Configures a rotating file handler and console output and installs a
global exception hook to ensure uncaught exceptions are logged.
"""
import logging
from logging.handlers import RotatingFileHandler
import sys

LOG_FILE = "bot.log"


def configure_logging():
    """Configure root logger: console + rotating file."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Formatter
    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler (if not already attached)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        root.addHandler(ch)

    # Rotating file handler
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
    fh.setFormatter(fmt)
    root.addHandler(fh)


def _excepthook(exc_type, exc_value, exc_traceback):
    logging.getLogger().exception("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


# Install the hook
sys.excepthook = _excepthook
