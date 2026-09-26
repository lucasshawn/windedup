#!/usr/bin/env python3
"""
Windedup - Duplicate File Finder & Deduplicator for Windows
"""
from windedup.ui.dpi import enable_high_dpi_awareness

# Must be set prior to Tk initialization for crisp rendering on high-DPI displays
enable_high_dpi_awareness()

from windedup.ui.app import main

if __name__ == "__main__":
    main()
