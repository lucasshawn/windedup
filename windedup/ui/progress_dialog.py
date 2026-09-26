import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from windedup.core.models import ScanProgress

class ProgressDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, on_cancel: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.title("Scanning for Duplicates...")

        try:
            dpi = self.winfo_fpixels('1i')
            scale = max(1.0, dpi / 96.0)
        except Exception:
            scale = 1.0

        dlg_w = int(480 * scale)
        dlg_h = int(200 * scale)
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

        # Phase label
        self.lbl_phase = ttk.Label(self, text="Phase 1: Discovering files...", font=("Segoe UI", 10, "bold"))
        self.lbl_phase.pack(anchor="w", padx=pad_x, pady=(int(16 * scale), int(6 * scale)))

        # Progress bar (0 - 100)
        bar_len = int(436 * scale)
        self.progress_bar = ttk.Progressbar(self, orient="horizontal", length=bar_len, mode="determinate", maximum=100.0)
        self.progress_bar.pack(padx=pad_x, pady=int(6 * scale))

        # Percent and file counts
        info_frame = ttk.Frame(self)
        info_frame.pack(fill="x", padx=pad_x, pady=int(3 * scale))
        self.lbl_percent = ttk.Label(info_frame, text="0%", font=("Segoe UI", 10, "bold"), foreground="#005A9E")
        self.lbl_percent.pack(side="left")

        self.lbl_stats = ttk.Label(info_frame, text="Files scanned: 0", font=("Segoe UI", 9))
        self.lbl_stats.pack(side="right")

        # Current file path label
        self.lbl_path = ttk.Label(self, text="", font=("Segoe UI", 8), foreground="#555555")
        self.lbl_path.pack(anchor="w", padx=pad_x, pady=(int(3 * scale), int(12 * scale)))

        # Cancel button
        self.btn_cancel = ttk.Button(self, text="Cancel", command=self._handle_cancel)
        self.btn_cancel.pack(pady=(0, int(12 * scale)))

        self.protocol("WM_DELETE_WINDOW", self._handle_cancel)

    def _handle_cancel(self):
        self.btn_cancel.config(state="disabled", text="Cancelling...")
        if self.on_cancel:
            self.on_cancel()

    def update_progress(self, p: ScanProgress):
        if not self.winfo_exists():
            return

        if p.phase == "enumerating":
            self.lbl_phase.config(text="Phase 1: Discovering files...")
            self.lbl_stats.config(text=f"Files examined: {p.files_scanned}")
            self.lbl_percent.config(text="Enumerating...")
        elif p.phase == "comparing":
            self.lbl_phase.config(text="Phase 2: Pre-filtering candidates...")
            self.progress_bar["value"] = p.percent
            self.lbl_percent.config(text=f"{p.percent:.0f}%")
            self.lbl_stats.config(text=f"Candidates checked: {p.candidate_count}")
        elif p.phase == "hashing":
            self.lbl_phase.config(text="Phase 3: Comparing full file hashes...")
            self.progress_bar["value"] = p.percent
            self.lbl_percent.config(text=f"{p.percent:.0f}%")
            self.lbl_stats.config(text=f"Candidates verified: {p.candidate_count}")
        elif p.phase == "complete":
            self.progress_bar["value"] = 100.0
            self.lbl_percent.config(text="100%")

        path_text = p.current_path
        if len(path_text) > 60:
            path_text = "..." + path_text[-57:]
        self.lbl_path.config(text=path_text)
