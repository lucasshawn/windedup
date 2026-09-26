import tkinter as tk
from tkinter import ttk, font
import os
import subprocess
import time
from typing import List, Callable, Optional, Dict
from windedup.core.models import DuplicateGroup, FileEntry

def format_size(bytes_val: int) -> str:
    val = float(bytes_val)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if val < 1024.0:
            return f"{val:.1f} {unit}" if unit != 'B' else f"{int(val)} B"
        val /= 1024.0
    return f"{val:.1f} PB"

class DuplicateTreeView(ttk.Frame):
    def __init__(self, parent, on_selection_changed: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.on_selection_changed = on_selection_changed
        self.groups: List[DuplicateGroup] = []
        self._item_to_entry: Dict[str, FileEntry] = {}
        self._item_to_group: Dict[str, DuplicateGroup] = {}

        self._build_ui()

    def _build_ui(self):
        # Calculate DPI scale factor
        try:
            dpi = self.winfo_fpixels('1i')
            scale = max(1.0, dpi / 96.0)
        except Exception:
            scale = 1.0

        # Configure Treeview styling with modern row height and Segoe UI fonts
        style = ttk.Style(self)
        row_height = int(28 * scale)
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=row_height)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), padding=(6, 4))

        columns = ("name", "size", "status", "modified", "path")
        self.tree = ttk.Treeview(self, columns=columns, show="tree headings", selectmode="browse")

        self.tree.heading("#0", text="Group / Items", anchor="w")
        self.tree.heading("name", text="File Name", anchor="w")
        self.tree.heading("size", text="Size", anchor="e")
        self.tree.heading("status", text="Status (Dedup Action)", anchor="center")
        self.tree.heading("modified", text="Date Modified", anchor="w")
        self.tree.heading("path", text="Full Path", anchor="w")

        self.tree.column("#0", width=int(140 * scale), stretch=False)
        self.tree.column("name", width=int(180 * scale))
        self.tree.column("size", width=int(95 * scale), anchor="e")
        self.tree.column("status", width=int(150 * scale), anchor="center")
        self.tree.column("modified", width=int(155 * scale))
        self.tree.column("path", width=int(450 * scale))

        # Scrollbars
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Tags for styling Keep / Toss
        self.tree.tag_configure("keep", foreground="#0E700E", font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("toss", foreground="#C42B1C", font=("Segoe UI", 10))
        self.tree.tag_configure("group_header", font=("Segoe UI", 10, "bold"))

        # Bindings
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<space>", self._on_space)
        self.tree.bind("<Button-3>", self._on_right_click)

        # Context Menu
        self.context_menu = tk.Menu(self, tearoff=0, font=("Segoe UI", 9))
        self.context_menu.add_command(label="Keep this file (Toss others)", command=self._ctx_keep_this)
        self.context_menu.add_command(label="Toss this file", command=self._ctx_toss_this)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Open enclosing folder in Explorer", command=self._ctx_open_folder)
        self.context_menu.add_command(label="Open file", command=self._ctx_open_file)

    def populate(self, groups: List[DuplicateGroup]):
        self.groups = groups
        self.tree.delete(*self.tree.get_children())
        self._item_to_entry.clear()
        self._item_to_group.clear()

        for group in self.groups:
            # Group parent row
            group_text = f"Group ({len(group.entries)} copies)"
            parent_id = self.tree.insert(
                "",
                "end",
                text=group_text,
                values=(
                    group.filename,
                    format_size(group.size),
                    f"{group.keep_count} Keep / {group.toss_count} Toss",
                    "",
                    f"Hash: {group.hash[:16]}..."
                ),
                tags=("group_header",),
                open=True
            )
            self._item_to_group[parent_id] = group

            # Child path rows
            for entry in group.entries:
                status_text = "[ KEEP ]" if entry.is_keep else "[ TOSS ]"
                status_tag = "keep" if entry.is_keep else "toss"
                mtime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.mtime))

                child_id = self.tree.insert(
                    parent_id,
                    "end",
                    text="  └─",
                    values=(
                        os.path.basename(entry.path),
                        format_size(entry.size),
                        status_text,
                        mtime_str,
                        entry.path
                    ),
                    tags=(status_tag,)
                )
                self._item_to_entry[child_id] = entry
                self._item_to_group[child_id] = group

        if self.on_selection_changed:
            self.on_selection_changed()

    def refresh_views(self):
        """Updates display text and tags based on current is_keep states."""
        for item_id, entry in self._item_to_entry.items():
            status_text = "[ KEEP ]" if entry.is_keep else "[ TOSS ]"
            status_tag = "keep" if entry.is_keep else "toss"
            values = list(self.tree.item(item_id, "values"))
            if len(values) >= 3:
                values[2] = status_text
                self.tree.item(item_id, values=values, tags=(status_tag,))

        # Update parent group rows
        for item_id, group in self._item_to_group.items():
            if item_id not in self._item_to_entry:
                values = list(self.tree.item(item_id, "values"))
                if len(values) >= 3:
                    values[2] = f"{group.keep_count} Keep / {group.toss_count} Toss"
                    self.tree.item(item_id, values=values)

        if self.on_selection_changed:
            self.on_selection_changed()

    def _toggle_item(self, item_id: str):
        if item_id in self._item_to_entry:
            entry = self._item_to_entry[item_id]
            entry.is_keep = not entry.is_keep
            self.refresh_views()

    def _on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self._toggle_item(item_id)

    def _on_space(self, event):
        selected = self.tree.selection()
        if selected:
            self._toggle_item(selected[0])

    def _on_right_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            if item_id in self._item_to_entry:
                self.context_menu.post(event.x_root, event.y_root)

    def _ctx_keep_this(self):
        sel = self.tree.selection()
        if sel and sel[0] in self._item_to_entry:
            target_entry = self._item_to_entry[sel[0]]
            group = self._item_to_group[sel[0]]
            for e in group.entries:
                e.is_keep = (e == target_entry)
            self.refresh_views()

    def _ctx_toss_this(self):
        sel = self.tree.selection()
        if sel and sel[0] in self._item_to_entry:
            target_entry = self._item_to_entry[sel[0]]
            target_entry.is_keep = False
            self.refresh_views()

    def _ctx_open_folder(self):
        sel = self.tree.selection()
        if sel and sel[0] in self._item_to_entry:
            path = self._item_to_entry[sel[0]].path
            folder = os.path.dirname(path)
            subprocess.run(["explorer", folder])

    def _ctx_open_file(self):
        sel = self.tree.selection()
        if sel and sel[0] in self._item_to_entry:
            path = self._item_to_entry[sel[0]].path
            os.startfile(path)
