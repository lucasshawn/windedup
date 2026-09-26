import tkinter as tk
from tkinter import ttk
import os
import subprocess
import time
from typing import List, Callable, Optional, Dict
from windedup.core.models import DuplicateGroup, FileEntry

# Checkbox glyphs
CHECKED = "☑"      # Marked to TOSS (delete)
UNCHECKED = "☐"    # Marked to KEEP (preserve)
PARTIAL = "⊟"      # Mixed in group

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
        self._group_to_item: Dict[str, str] = {}

        self._build_ui()

    def _build_ui(self):
        try:
            dpi = self.winfo_fpixels('1i')
            scale = max(1.0, dpi / 96.0)
        except Exception:
            scale = 1.0

        style = ttk.Style(self)
        row_height = int(28 * scale)
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=row_height)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), padding=(6, 4))

        columns = ("name", "size", "status", "modified", "path")
        self.tree = ttk.Treeview(self, columns=columns, show="tree headings", selectmode="browse")

        self.tree.heading("#0", text="  Toss?  Group / Items", anchor="w")
        self.tree.heading("name", text="File Name", anchor="w")
        self.tree.heading("size", text="Size", anchor="e")
        self.tree.heading("status", text="Action Status", anchor="center")
        self.tree.heading("modified", text="Date Modified", anchor="w")
        self.tree.heading("path", text="Full Path", anchor="w")

        self.tree.column("#0", width=int(180 * scale), stretch=False)
        self.tree.column("name", width=int(180 * scale))
        self.tree.column("size", width=int(95 * scale), anchor="e")
        self.tree.column("status", width=int(170 * scale), anchor="center")
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
        self.tree.tag_configure("keep", foreground="#0E700E", font=("Segoe UI", 10))
        self.tree.tag_configure("toss", foreground="#C42B1C", font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("group_header", font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("group_all_toss", foreground="#C42B1C", font=("Segoe UI", 10, "bold"))

        # Bindings
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<space>", self._on_space)
        self.tree.bind("<Button-3>", self._on_right_click)

        # Context Menus
        self.child_menu = tk.Menu(self, tearoff=0, font=("Segoe UI", 9))
        self.child_menu.add_command(label="Toggle Toss / Keep (Spacebar)", command=self._ctx_toggle)
        self.child_menu.add_separator()
        self.child_menu.add_command(label="Keep this file (Toss others in group)", command=self._ctx_keep_this)
        self.child_menu.add_command(label="Toss this file", command=self._ctx_toss_this)
        self.child_menu.add_command(label="Toss all copies in this group (Delete all)", command=self._ctx_toss_group)
        self.child_menu.add_separator()
        self.child_menu.add_command(label="Open enclosing folder in Explorer", command=self._ctx_open_folder)
        self.child_menu.add_command(label="Open file", command=self._ctx_open_file)

        self.group_menu = tk.Menu(self, tearoff=0, font=("Segoe UI", 9))
        self.group_menu.add_command(label="Mark Entire Group to Toss (Delete all copies)", command=self._ctx_toss_group)
        self.group_menu.add_command(label="Mark Entire Group to Keep (Preserve all copies)", command=self._ctx_keep_group)

    def _get_group_checkbox_state(self, group: DuplicateGroup) -> tuple[str, str, str]:
        total = len(group.entries)
        toss = group.toss_count
        if toss == total and total > 0:
            return CHECKED, f"{CHECKED} TOSS ALL ({total} copies)", "group_all_toss"
        elif toss == 0:
            return UNCHECKED, f"{UNCHECKED} KEEP ALL (0 of {total} to toss)", "group_header"
        else:
            return PARTIAL, f"{PARTIAL} {toss} to Toss, {group.keep_count} to Keep", "group_header"

    def populate(self, groups: List[DuplicateGroup]):
        self.groups = groups
        self.tree.delete(*self.tree.get_children())
        self._item_to_entry.clear()
        self._item_to_group.clear()
        self._group_to_item.clear()

        for group in self.groups:
            chk, status_desc, tag = self._get_group_checkbox_state(group)
            group_header_text = f" {chk}  Group ({len(group.entries)} copies)"

            parent_id = self.tree.insert(
                "",
                "end",
                text=group_header_text,
                values=(
                    group.filename,
                    format_size(group.size),
                    status_desc,
                    "",
                    f"Hash: {group.hash[:16]}..."
                ),
                tags=(tag,),
                open=True
            )
            self._item_to_group[parent_id] = group
            self._group_to_item[group.group_id] = parent_id

            # Child path rows
            for entry in group.entries:
                child_chk = CHECKED if not entry.is_keep else UNCHECKED
                status_text = f"{CHECKED} TOSS" if not entry.is_keep else f"{UNCHECKED} KEEP"
                status_tag = "toss" if not entry.is_keep else "keep"
                mtime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.mtime))

                child_id = self.tree.insert(
                    parent_id,
                    "end",
                    text=f"    {child_chk}  ",
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
        """Updates checkbox glyphs and statuses across all items and group headers."""
        # Update child items
        for item_id, entry in self._item_to_entry.items():
            child_chk = CHECKED if not entry.is_keep else UNCHECKED
            status_text = f"{CHECKED} TOSS" if not entry.is_keep else f"{UNCHECKED} KEEP"
            status_tag = "toss" if not entry.is_keep else "keep"

            self.tree.item(item_id, text=f"    {child_chk}  ")
            values = list(self.tree.item(item_id, "values"))
            if len(values) >= 3:
                values[2] = status_text
                self.tree.item(item_id, values=values, tags=(status_tag,))

        # Update parent group headers
        for parent_id, group in self._item_to_group.items():
            if parent_id not in self._item_to_entry:
                chk, status_desc, tag = self._get_group_checkbox_state(group)
                group_header_text = f" {chk}  Group ({len(group.entries)} copies)"
                self.tree.item(parent_id, text=group_header_text)
                values = list(self.tree.item(parent_id, "values"))
                if len(values) >= 3:
                    values[2] = status_desc
                    self.tree.item(parent_id, values=values, tags=(tag,))

        if self.on_selection_changed:
            self.on_selection_changed()

    def toggle_item(self, item_id: str):
        # 1. If child item clicked: toggle that specific file
        if item_id in self._item_to_entry:
            entry = self._item_to_entry[item_id]
            entry.is_keep = not entry.is_keep
            self.refresh_views()
        # 2. If parent group row clicked: toggle all items in group
        elif item_id in self._item_to_group:
            group = self._item_to_group[item_id]
            # If all are currently toss, switch all to keep. Otherwise, switch all to toss.
            all_toss = (group.toss_count == len(group.entries))
            target_keep = all_toss
            for e in group.entries:
                e.is_keep = target_keep
            self.refresh_views()

    def _on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.toggle_item(item_id)

    def _on_space(self, event):
        selected = self.tree.selection()
        if selected:
            self.toggle_item(selected[0])

    def _on_right_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            if item_id in self._item_to_entry:
                self.child_menu.post(event.x_root, event.y_root)
            elif item_id in self._item_to_group:
                self.group_menu.post(event.x_root, event.y_root)

    def _ctx_toggle(self):
        sel = self.tree.selection()
        if sel:
            self.toggle_item(sel[0])

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

    def _ctx_toss_group(self):
        sel = self.tree.selection()
        if sel and sel[0] in self._item_to_group:
            group = self._item_to_group[sel[0]]
            for e in group.entries:
                e.is_keep = False
            self.refresh_views()

    def _ctx_keep_group(self):
        sel = self.tree.selection()
        if sel and sel[0] in self._item_to_group:
            group = self._item_to_group[sel[0]]
            for e in group.entries:
                e.is_keep = True
            self.refresh_views()

    def _ctx_open_folder(self):
        sel = self.tree.selection()
        if sel and sel[0] in self._item_to_entry:
            path = self._item_to_entry[sel[0]].path
            folder = os.path.dirname(path)
            try:
                if os.path.exists(folder):
                    os.startfile(folder)
                else:
                    subprocess.run(["explorer", folder])
            except Exception:
                try:
                    subprocess.run(["explorer", folder])
                except Exception:
                    pass

    def _ctx_open_file(self):
        sel = self.tree.selection()
        if sel and sel[0] in self._item_to_entry:
            path = self._item_to_entry[sel[0]].path
            try:
                os.startfile(path)
            except Exception as e:
                from tkinter import messagebox
                messagebox.showwarning(
                    "Cannot Open File",
                    f"Could not open file:\n{path}\n\nReason: {e}"
                )
