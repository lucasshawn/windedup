"""
Windedup application metadata and build information.
"""

APP_NAME = "Windedup"
APP_DESCRIPTION = "Duplicate File Finder & Deduplicator for Windows"
VERSION = "1.1.0"
AUTHOR = "PowerHouse PNW Development"
CONTACT_NAME = "PowerHouse PNW Development"
CONTACT_EMAIL = "powerhousepnw@gmail.com"


def get_build_timestamp() -> str:
    """
    Returns the build timestamp string.
    If generated during build by Makefile, returns the value in windedup._build_info.
    Otherwise returns 'Development Build'.
    """
    try:
        from windedup._build_info import BUILD_TIMESTAMP  # type: ignore
        return BUILD_TIMESTAMP
    except (ImportError, ModuleNotFoundError, AttributeError):
        return "Development Build"
