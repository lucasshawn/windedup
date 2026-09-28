import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import subprocess
import urllib.parse
import webbrowser
from typing import Dict, Any, Optional

from windedup.core.logger import (
    clear_previous_crash,
    get_crash_report_text,
    get_log_file_path
)

DEVELOPER_EMAIL = "lucas_shawn@hotmail.com"

class CrashReportDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, crash_info: Dict[str, Any]):
        super().__init__(parent)
        self.parent = parent
        self.crash_info = crash_info

        self.title("Windedup - Previous Crash Detected")
        self.geometry("740x580")
        self.minsize(580, 440)
        self.transient(parent)
        self.grab_set()

        # Guarantee marker is cleared from disk as soon as dialog is created
        clear_previous_crash()

        self._build_ui()
        self._center_window()
        self.protocol("WM_DELETE_WINDOW", self._on_dismiss)

    def _center_window(self):
        self.update_idletasks()
        try:
            w = self.winfo_width()
            h = self.winfo_height()
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=(18, 16))
        main_frame.pack(fill="both", expand=True)

        # 1. Action Buttons Bar (Packed at bottom FIRST so it is NEVER cut off)
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side="bottom", fill="x", pady=(10, 0))

        btn_email = ttk.Button(
            btn_frame,
            text=f"✉️ Send Report to Developer ({DEVELOPER_EMAIL})",
            command=self._send_email_report
        )
        btn_email.pack(side="left", padx=(0, 6))

        btn_copy = ttk.Button(
            btn_frame,
            text="📋 Copy Report",
            command=self._copy_to_clipboard
        )
        btn_copy.pack(side="left", padx=(0, 6))

        btn_open_log = ttk.Button(
            btn_frame,
            text="📄 Open Log File",
            command=self._open_log_file
        )
        btn_open_log.pack(side="left", padx=(0, 6))

        btn_dismiss = ttk.Button(
            btn_frame,
            text="Dismiss",
            command=self._on_dismiss
        )
        btn_dismiss.pack(side="right")

        # 2. Header Banner
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 10))

        lbl_icon = ttk.Label(header_frame, text="⚠️", font=("Segoe UI", 24))
        lbl_icon.pack(side="left", padx=(0, 12))

        text_header_frame = ttk.Frame(header_frame)
        text_header_frame.pack(side="left", fill="x", expand=True)

        lbl_title = ttk.Label(
            text_header_frame,
            text="Windedup detected that its previous run crashed",
            font=("Segoe UI", 12, "bold"),
            foreground="#C42B1C"
        )
        lbl_title.pack(anchor="w")

        timestamp = self.crash_info.get("timestamp", "Unknown time")
        context = self.crash_info.get("context", "Application Crash")
        lbl_sub = ttk.Label(
            text_header_frame,
            text=f"Crash occurred on {timestamp} in '{context}'. Diagnostic logs were preserved.",
            font=("Segoe UI", 9)
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # 3. Crash Summary Line
        summary_frame = ttk.LabelFrame(main_frame, text=" Exception Details ", padding=(12, 8))
        summary_frame.pack(fill="x", pady=(0, 10))

        err_type = self.crash_info.get("error_type", "Exception")
        err_msg = self.crash_info.get("error_message", "No details")
        lbl_err = ttk.Label(
            summary_frame,
            text=f"{err_type}: {err_msg}",
            font=("Consolas", 10, "bold"),
            foreground="#8A1F11",
            wraplength=660
        )
        lbl_err.pack(anchor="w")

        # 4. Traceback Viewer (Fills remaining space between summary and buttons)
        tb_frame = ttk.LabelFrame(main_frame, text=" Full Traceback & Diagnostic Log ", padding=(10, 8))
        tb_frame.pack(fill="both", expand=True)

        self.txt_traceback = tk.Text(
            tb_frame,
            wrap="none",
            height=10,
            font=("Consolas", 9),
            background="#F8F9FA",
            foreground="#212529",
            padx=8,
            pady=8,
            borderwidth=1,
            relief="solid"
        )
        vsb = ttk.Scrollbar(tb_frame, orient="vertical", command=self.txt_traceback.yview)
        hsb = ttk.Scrollbar(tb_frame, orient="horizontal", command=self.txt_traceback.xview)
        self.txt_traceback.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.txt_traceback.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tb_frame.rowconfigure(0, weight=1)
        tb_frame.columnconfigure(0, weight=1)

        report_content = get_crash_report_text(self.crash_info)
        self.txt_traceback.insert("1.0", report_content)
        self.txt_traceback.config(state="disabled")

    def _send_email_report(self):
        """Prepares an email to the developer with the crash diagnostics."""
        report_text = get_crash_report_text(self.crash_info)
        # Copy to clipboard as a reliable fallback
        try:
            self.clipboard_clear()
            self.clipboard_append(report_text)
        except Exception:
            pass

        err_type = self.crash_info.get("error_type", "Crash")
        subject = f"Windedup Crash Report: {err_type}"
        # Truncate body for mailto URL limits (2000 chars) if needed
        safe_body = report_text[:1800]
        if len(report_text) > 1800:
            safe_body += "\n... [Full report copied to your clipboard! Please paste into email body]"

        encoded_subject = urllib.parse.quote(subject)
        encoded_body = urllib.parse.quote(safe_body)
        mailto_url = f"mailto:{DEVELOPER_EMAIL}?subject={encoded_subject}&body={encoded_body}"

        opened = False
        try:
            webbrowser.open(mailto_url)
            opened = True
        except Exception:
            try:
                os.startfile(mailto_url)
                opened = True
            except Exception:
                opened = False

        if opened:
            messagebox.showinfo(
                "Report Prepared",
                f"Your default email client has been opened with a draft to {DEVELOPER_EMAIL}.\n\n"
                f"The full diagnostic log has also been copied to your clipboard!",
                parent=self
            )
        else:
            messagebox.showinfo(
                "Report Copied",
                f"Could not open mail client directly.\n\n"
                f"The complete diagnostic report has been copied to your clipboard. "
                f"Please paste and send to {DEVELOPER_EMAIL}.",
                parent=self
            )

    def _copy_to_clipboard(self):
        report_text = get_crash_report_text(self.crash_info)
        try:
            self.clipboard_clear()
            self.clipboard_append(report_text)
            messagebox.showinfo("Copied", "Crash report copied to clipboard!", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy to clipboard: {e}", parent=self)

    def _open_log_file(self):
        log_path = self.crash_info.get("log_file") or get_log_file_path()
        try:
            if os.path.exists(log_path):
                os.startfile(log_path)
            else:
                messagebox.showwarning("File Missing", f"Log file not found at:\n{log_path}", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open log file: {e}", parent=self)

    def _on_dismiss(self):
        clear_previous_crash()
        self.destroy()
