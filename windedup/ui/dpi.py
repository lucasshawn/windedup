import sys
import ctypes

def enable_high_dpi_awareness():
    """
    Enables Windows Per-Monitor V2 DPI awareness.
    Prevents Windows Desktop Window Manager (DWM) from bitmap-stretching
    the window on high-DPI displays (which causes blurry text and fuzzy borders).
    """
    if sys.platform != "win32":
        return

    try:
        # Windows 10 Creators Update (1703)+ : DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 (-4)
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            # Windows 8.1+ : PROCESS_PER_MONITOR_DPI_AWARE (2)
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                # Windows Vista+ fallback
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
