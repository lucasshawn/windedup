#!/usr/bin/env python3
"""
Windedup - Duplicate File Finder & Deduplicator for Windows
"""
import sys
import logging
from windedup.core.logger import install_root_exception_handlers, setup_logging, log_and_show_exception

# 1. Install logging and global root-level crash handlers
setup_logging()
install_root_exception_handlers()

# 2. Enable Windows Per-Monitor V2 high-DPI awareness
from windedup.ui.dpi import enable_high_dpi_awareness
enable_high_dpi_awareness()

from windedup.ui.app import main

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_and_show_exception(*sys.exc_info(), context="Application Mainloop")
        sys.exit(1)
