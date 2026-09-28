import os
import sys
import json
import logging
from logging.handlers import RotatingFileHandler
import threading
import traceback
from datetime import datetime
from typing import Optional, Dict, Any

# Global log file and marker paths
LOG_FILE_PATH: str = ""
CRASH_MARKER_PATH: str = ""

def get_log_file_path() -> str:
    global LOG_FILE_PATH
    if LOG_FILE_PATH:
        return LOG_FILE_PATH

    appdata = os.environ.get("APPDATA")
    if appdata:
        log_dir = os.path.join(appdata, "Windedup")
    else:
        log_dir = os.path.join(os.path.expanduser("~"), ".windedup")

    try:
        os.makedirs(log_dir, exist_ok=True)
        LOG_FILE_PATH = os.path.join(log_dir, "windedup.log")
    except Exception:
        # Fallback to local directory
        LOG_FILE_PATH = os.path.abspath("windedup.log")

    return LOG_FILE_PATH

def get_crash_marker_path() -> str:
    global CRASH_MARKER_PATH
    if CRASH_MARKER_PATH:
        return CRASH_MARKER_PATH

    log_path = get_log_file_path()
    log_dir = os.path.dirname(log_path)
    CRASH_MARKER_PATH = os.path.join(log_dir, "crash.marker")
    return CRASH_MARKER_PATH

def write_crash_marker(
    exc_type,
    exc_value,
    exc_traceback,
    context: str = "Unhandled Exception"
) -> None:
    """Writes a persistent marker file so next startup can detect and report the crash."""
    # Do not persist crash markers for unit tests
    if context.startswith("Unit Test"):
        return

    try:
        marker_path = get_crash_marker_path()
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = "".join(tb_lines)

        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "context": context,
            "error_type": exc_type.__name__ if exc_type else "Exception",
            "error_message": str(exc_value),
            "traceback": tb_text,
            "log_file": get_log_file_path(),
            "python_version": sys.version,
            "platform": sys.platform
        }

        with open(marker_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to write crash marker file: {e}")

def has_previous_crash() -> Optional[Dict[str, Any]]:
    """Checks whether a crash marker exists from a previous run and returns its data."""
    try:
        marker_path = get_crash_marker_path()
        if os.path.exists(marker_path):
            with open(marker_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Failed to read crash marker file: {e}")
    return None

def clear_previous_crash() -> None:
    """Removes the crash marker file once acknowledged or dismissed by user."""
    try:
        marker_path = get_crash_marker_path()
        if os.path.exists(marker_path):
            os.remove(marker_path)
    except Exception as e:
        logging.error(f"Failed to remove crash marker file: {e}")

def consume_previous_crash() -> Optional[Dict[str, Any]]:
    """Reads previous crash marker data and removes the marker from disk immediately.
    Ensures that a crash notification is only shown once and never haunts the user on future startups."""
    info = has_previous_crash()
    if info:
        clear_previous_crash()
    return info

def get_crash_report_text(crash_info: Dict[str, Any]) -> str:
    """Formats full crash diagnostics for developer submission or clipboard."""
    return (
        f"Windedup Crash Report\n"
        f"Contact: PowerHouse PNW Development <powerhousepnw@gmail.com>\n"
        f"--------------------------------------------------\n"
        f"Timestamp:      {crash_info.get('timestamp', 'Unknown')}\n"
        f"Context:        {crash_info.get('context', 'Unknown')}\n"
        f"Error Type:     {crash_info.get('error_type', 'Exception')}\n"
        f"Error Message:  {crash_info.get('error_message', 'No details')}\n"
        f"Platform:       {crash_info.get('platform', sys.platform)}\n"
        f"Python Version: {crash_info.get('python_version', sys.version)}\n"
        f"Log File Path:  {crash_info.get('log_file', get_log_file_path())}\n"
        f"--------------------------------------------------\n"
        f"Traceback:\n"
        f"{crash_info.get('traceback', 'No traceback available')}\n"
    )

_LOGGING_INITIALIZED: bool = False

def setup_logging(force: bool = False) -> str:
    """Configures global logging to file and console with rotation."""
    global _LOGGING_INITIALIZED
    log_path = get_log_file_path()

    root_logger = logging.getLogger()
    for h in root_logger.handlers:
        if isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == os.path.abspath(log_path):
            _LOGGING_INITIALIZED = True
            return log_path

    if _LOGGING_INITIALIZED and not force:
        return log_path

    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)-7s] [%(threadName)-12s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    try:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        sys.stderr.write(f"Failed to create file handler for logging: {e}\n")

    # Console handler (if stdout/stderr are valid)
    if sys.stdout is not None:
        try:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        except Exception:
            pass

    logging.info("=" * 60)
    logging.info("Windedup logging initialized")
    logging.info(f"Log file: {log_path}")
    logging.info(f"Python: {sys.version}")
    logging.info(f"Platform: {sys.platform} | Executable: {sys.executable}")
    logging.info("=" * 60)

    return log_path

def log_and_show_exception(
    exc_type,
    exc_value,
    exc_traceback,
    context: str = "Unhandled Exception",
    show_dialog: bool = True
):
    """Logs full traceback and displays an informative error modal to the user."""
    logger = logging.getLogger("CRASH_HANDLER")
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_text = "".join(tb_lines)

    logger.critical(f"FATAL ERROR in {context}:\n{tb_text}")
    write_crash_marker(exc_type, exc_value, exc_traceback, context=context)

    if show_dialog:
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk._default_root
            if root is None:
                root = tk.Tk()
                root.withdraw()

            log_file = get_log_file_path()
            short_err = f"{exc_type.__name__}: {exc_value}" if exc_type else str(exc_value)

            messagebox.showerror(
                "Windedup Error",
                f"An error occurred in Windedup ({context}):\n\n"
                f"{short_err}\n\n"
                f"A diagnostic log has been saved to:\n{log_file}",
                parent=root if root and root.winfo_exists() else None
            )
        except Exception as dialog_err:
            logger.error(f"Failed to display crash dialog: {dialog_err}")

def install_root_exception_handlers():
    """Installs hooks for sys, threading, and Tkinter exceptions."""
    setup_logging()

    # 1. Main thread unhandled exceptions
    def sys_excepthook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        log_and_show_exception(exc_type, exc_value, exc_traceback, context="Main Thread")

    sys.excepthook = sys_excepthook

    # 2. Threading exceptions (Python 3.8+)
    def thread_excepthook(args):
        log_and_show_exception(
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
            context=f"Background Thread ({args.thread.name})"
        )

    if hasattr(threading, "excepthook"):
        threading.excepthook = thread_excepthook
