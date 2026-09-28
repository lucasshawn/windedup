import tkinter as tk
from tkinter import ttk
import os
import sys
import webbrowser

from windedup.version import (
    APP_NAME,
    APP_DESCRIPTION,
    VERSION,
    AUTHOR,
    CONTACT_EMAIL,
    get_build_timestamp,
)


class AboutDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title(f"About {APP_NAME}")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._load_icon()
        self._build_ui()
        self._center_window(parent)

        self.bind("<Escape>", lambda e: self.destroy())

    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        ico_path = os.path.join(base_dir, "assets", "icon.ico")
        png_path = os.path.join(base_dir, "assets", "icon.png")

        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        self._header_img = None
        if os.path.exists(png_path):
            try:
                full_img = tk.PhotoImage(file=png_path)
                # Subsample 512x512 down to approx 64x64 (divide by 8)
                self._header_img = full_img.subsample(8, 8)
            except Exception:
                pass

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=(24, 20))
        main_frame.pack(fill="both", expand=True)

        # Header Frame: Icon + Title + Subtitle
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 16))

        if self._header_img:
            lbl_icon = ttk.Label(header_frame, image=self._header_img)
            lbl_icon.pack(side="left", padx=(0, 16))

        header_text = ttk.Frame(header_frame)
        header_text.pack(side="left", fill="both", expand=True)

        lbl_title = ttk.Label(header_text, text=APP_NAME, font=("Segoe UI", 16, "bold"))
        lbl_title.pack(anchor="w")

        lbl_desc = ttk.Label(
            header_text,
            text=APP_DESCRIPTION,
            font=("Segoe UI", 9),
            foreground="#555555",
            wraplength=280
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # Metadata Card
        card = ttk.LabelFrame(main_frame, text=" Build & Provenance ", padding=(16, 12))
        card.pack(fill="x", pady=(0, 16))

        rows = [
            ("Version:", VERSION),
            ("Build Date / Time:", get_build_timestamp()),
            ("Author:", AUTHOR),
            ("Contact:", CONTACT_EMAIL),
        ]

        for i, (label_text, val_text) in enumerate(rows):
            ttk.Label(card, text=label_text, font=("Segoe UI", 9, "bold")).grid(
                row=i, column=0, sticky="w", padx=(0, 12), pady=4
            )
            val_lbl = ttk.Label(card, text=val_text, font=("Segoe UI", 9))
            val_lbl.grid(row=i, column=1, sticky="w", pady=4)

            if label_text == "Version:":
                self.version_label = val_lbl
            elif label_text == "Author:":
                self.author_label = val_lbl
            elif label_text == "Build Date / Time:":
                self.build_time_label = val_lbl
            elif label_text == "Contact:":
                self.email_label = val_lbl
                val_lbl.configure(foreground="#0066cc", cursor="hand2")
                val_lbl.bind("<Button-1>", lambda e: self._send_email())

        # Email Actions Frame
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill="x", pady=(0, 16))

        self.btn_copy = ttk.Button(action_frame, text="Copy Email", command=self._copy_email)
        self.btn_copy.pack(side="left", padx=(0, 8))

        btn_mail = ttk.Button(action_frame, text="Send Email", command=self._send_email)
        btn_mail.pack(side="left")

        # Bottom Button
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill="x")
        btn_close = ttk.Button(bottom_frame, text="Close", command=self.destroy, width=10)
        btn_close.pack(side="right")
        btn_close.focus_set()

    def _copy_email(self):
        self.clipboard_clear()
        self.clipboard_append(CONTACT_EMAIL)
        self.update()
        self.btn_copy.configure(text="Copied!")

        def _reset_btn():
            try:
                if self.winfo_exists():
                    self.btn_copy.configure(text="Copy Email")
            except Exception:
                pass

        self.after(2000, _reset_btn)

    def _send_email(self):
        webbrowser.open(f"mailto:{CONTACT_EMAIL}")

    def _center_window(self, parent: tk.Tk):
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), 440)
        h = max(self.winfo_reqheight(), 340)

        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()

        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
