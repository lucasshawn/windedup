import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from windedup.core.models import DeleteProgress
from windedup.ui.tree_view import format_size

class DeleteProgressDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, on_cancel: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.title("Deduplicating Files...")

        try:
            dpi = self.winfo_fpixels('1i')
            scale = max(1.0, dpi / 96.0)
        except Exception:
            scale = 1.0

        dlg_w = int(500 * scale)
        dlg_h = int(210 * scale)
        self.geometry(f"{dlg_w}x{dlg_h}")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.on_cancel = on_cancel

        # Center on parent window
        self.update_idletasks()
        try:
            parent_x = parent.winfo_rootx()
            parent_y = parent.winfo_rooty()
            parent_w = parent.winfo_width()
            parent_h = parent.winfo_height()
            pos_x = parent_x + (parent_w - dlg_w) // 2
            pos_y = parent_y + (parent_h - dlg_h) // 2
            self.geometry(f"{dlg_w}x{dlg_h}+{max(0, pos_x)}+{max(0, pos_y)}")
        except Exception:
            pass

        pad_x = int(22 * scale)

        # Header label
        self.lbl_action = ttk.Label(self, text="Deduplicating selected files...", font=("Segoe UI", 10, "bold"))
        self.lbl_action.pack(anchor="w", padx=pad_x, pady=(int(16 * scale), int(6 * scale)))

        # Progress bar
        bar_len = int(456 * scale)
        self.progress_bar = ttk.Progressbar(self, orient="horizontal", length=bar_len, mode="determinate", maximum=100.0)
        self.progress_bar.pack(padx=pad_x, pady=int(6 * scale))

        # Percentage & Counter Frame
        info_frame = ttk.Frame(self)
        info_frame.pack(fill="x", padx=pad_x, pady=int(3 * scale))

        self.lbl_percent = ttk.Label(info_frame, text="0%", font=("Segoe UI", 10, "bold"), foreground="#C42B1C")
        self.lbl_percent.pack(side="left")

        self.lbl_counts = ttk.Label(info_frame, text="Deleted: 0 files (0 B)", font=("Segoe UI", 9))
        self.lbl_counts.pack(side="right")

        # Current file path label
        self.lbl_path = ttk.Label(self, text="Preparing...", font=("Segoe UI", 8), foreground="#444444")
        self.lbl_path.pack(anchor="w", padx=pad_x, pady=(int(4 * scale), int(12 * scale)))

        # Cancel button
        self.btn_cancel = ttk.Button(self, text="Cancel", command=self._handle_cancel)
        self.btn_cancel.pack(pady=(0, int(10 * scale)))

        self.protocol("WM_DELETE_WINDOW", self._handle_cancel)

    def _handle_cancel(self):
        self.btn_cancel.config(state="disabled", text="Stopping...")
        if self.on_cancel:
            self.on_cancel()

    def update_progress(self, p: DeleteProgress):
        if not self.winfo_exists():
            return

        self.progress_bar["value"] = p.percent
        self.lbl_percent.config(text=f"{p.percent:.0f}%")
        self.lbl_counts.config(
            text=f"Deleted: {p.current} of {p.total} ({format_size(p.bytes_freed)} freed)"
        )

        if p.percent >= 100.0:
            self.lbl_action.config(text="Deduplication complete!")
            self.lbl_path.config(text="Finished processing all marked files.")
            self.btn_cancel.config(state="disabled")
        else:
            path_text = p.current_path
            if len(path_text) > 65:
                path_text = "..." + path_text[-62:]
            self.lbl_path.config(text=f"Deleting: {path_text}")
