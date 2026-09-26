import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import os
from typing import List, Optional

from windedup.core.models import DuplicateGroup, ScanProgress
from windedup.core.scanner import scan_directory
from windedup.core.rules import (
    apply_keep_newest,
    apply_keep_oldest,
    apply_keep_shortest_path,
    apply_prefer_folder
)
from windedup.core.recycle import execute_deduplication, validate_safety_invariants
from windedup.ui.tree_view import DuplicateTreeView, format_size
from windedup.ui.progress_dialog import ProgressDialog

class WindedupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Windedup - Duplicate File Finder & Deduplicator")
        self.geometry("1100x700")
        self.minsize(850, 520)

        # Apply Windows native ttk theme
        style = ttk.Style(self)
        available_themes = style.theme_names()
        for theme in ("vista", "winnative", "clam", "default"):
            if theme in available_themes:
                style.theme_use(theme)
                break

        self.groups: List[DuplicateGroup] = []
        self.scan_queue: queue.Queue = queue.Queue()
        self.cancel_event: Optional[threading.Event] = None
        self.progress_dialog: Optional[ProgressDialog] = None

        self._build_ui()

    def _build_ui(self):
        # 1. Top Folder Selection Bar
        top_frame = ttk.LabelFrame(self, text="Target Folder", padding=(12, 8))
        top_frame.pack(fill="x", padx=12, pady=(10, 5))

        self.txt_folder = ttk.Entry(top_frame, font=("Segoe UI", 9))
        self.txt_folder.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse = ttk.Button(top_frame, text="Browse...", command=self._browse_folder)
        btn_browse.pack(side="left", padx=(0, 8))

        self.btn_scan = ttk.Button(top_frame, text="Scan for Duplicates", command=self._start_scan)
        self.btn_scan.pack(side="left")

        # 2. Quick Dedup & Rules Toolbar
        tools_frame = ttk.Frame(self, padding=(12, 6))
        tools_frame.pack(fill="x")

        ttk.Label(tools_frame, text="Quick Rules:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))
        self.btn_rule_newest = ttk.Button(tools_frame, text="Keep Newest", command=self._rule_newest, state="disabled")
        self.btn_rule_newest.pack(side="left", padx=2)

        self.btn_rule_oldest = ttk.Button(tools_frame, text="Keep Oldest", command=self._rule_oldest, state="disabled")
        self.btn_rule_oldest.pack(side="left", padx=2)

        self.btn_rule_shortest = ttk.Button(tools_frame, text="Keep Shortest Path", command=self._rule_shortest, state="disabled")
        self.btn_rule_shortest.pack(side="left", padx=2)

        self.btn_rule_folder = ttk.Button(tools_frame, text="Prefer Folder...", command=self._rule_prefer_folder, state="disabled")
        self.btn_rule_folder.pack(side="left", padx=2)

        self.lbl_stats = ttk.Label(tools_frame, text="Select a folder to begin scanning", font=("Segoe UI", 9), foreground="#005A9E")
        self.lbl_stats.pack(side="right", padx=5)

        # 3. Main Hierarchical Treeview
        tree_frame = ttk.Frame(self, padding=(12, 5))
        tree_frame.pack(fill="both", expand=True)

        self.tree_view = DuplicateTreeView(tree_frame, on_selection_changed=self._update_stats_display)
        self.tree_view.pack(fill="both", expand=True)

        # 4. Bottom Action Bar
        bottom_frame = ttk.Frame(self, padding=(12, 10))
        bottom_frame.pack(fill="x")

        self.var_recycle = tk.BooleanVar(value=True)
        chk_recycle = ttk.Checkbutton(
            bottom_frame,
            text="Send tossed files to Windows Recycle Bin (Safe & Reversible)",
            variable=self.var_recycle
        )
        chk_recycle.pack(side="left")

        self.btn_dedup = ttk.Button(bottom_frame, text="Dedup Now", command=self._execute_dedup)
        self.btn_dedup.pack(side="right")
        self.btn_dedup.config(state="disabled")

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Select Folder to Scan")
        if folder:
            self.txt_folder.delete(0, tk.END)
            self.txt_folder.insert(0, os.path.normpath(folder))

    def _start_scan(self):
        folder = self.txt_folder.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("Invalid Folder", "Please select a valid existing directory to scan.")
            return

        self.btn_scan.config(state="disabled")
        self._set_rule_buttons_state("disabled")
        self.btn_dedup.config(state="disabled")

        self.cancel_event = threading.Event()
        self.progress_dialog = ProgressDialog(self, on_cancel=self._cancel_scan)

        worker = threading.Thread(
            target=self._scan_worker,
            args=(folder, self.cancel_event),
            daemon=True
        )
        worker.start()
        self.after(50, self._check_scan_queue)

    def _cancel_scan(self):
        if self.cancel_event:
            self.cancel_event.set()

    def _scan_worker(self, folder: str, cancel_ev: threading.Event):
        def on_prog(prog: ScanProgress):
            self.scan_queue.put(("progress", prog))

        groups = scan_directory(folder, progress_callback=on_prog, cancel_event=cancel_ev)
        self.scan_queue.put(("done", groups))

    def _check_scan_queue(self):
        try:
            while not self.scan_queue.empty():
                msg_type, data = self.scan_queue.get_nowait()
                if msg_type == "progress" and self.progress_dialog:
                    self.progress_dialog.update_progress(data)
                elif msg_type == "done":
                    if self.progress_dialog:
                        self.progress_dialog.destroy()
                        self.progress_dialog = None
                    self.btn_scan.config(state="normal")
                    self.groups = data
                    self.tree_view.populate(self.groups)

                    if self.groups:
                        self._set_rule_buttons_state("normal")
                        self.btn_dedup.config(state="normal")
                    else:
                        self._set_rule_buttons_state("disabled")
                        self.btn_dedup.config(state="disabled")
                        if self.cancel_event and self.cancel_event.is_set():
                            messagebox.showinfo("Scan Cancelled", "Scan was cancelled by the user.")
                        else:
                            messagebox.showinfo("Scan Complete", "No duplicate files found in the selected folder!")
                    return
        except queue.Empty:
            pass

        self.after(50, self._check_scan_queue)

    def _set_rule_buttons_state(self, state: str):
        self.btn_rule_newest.config(state=state)
        self.btn_rule_oldest.config(state=state)
        self.btn_rule_shortest.config(state=state)
        self.btn_rule_folder.config(state=state)

    def _update_stats_display(self):
        total_groups = len(self.groups)
        total_toss = sum(g.toss_count for g in self.groups)
        total_reclaim = sum(g.reclaimable_bytes for g in self.groups)

        if total_groups == 0:
            self.lbl_stats.config(text="No duplicate files loaded")
        else:
            self.lbl_stats.config(
                text=f"Duplicates: {total_groups} groups | Marked to toss: {total_toss} files ({format_size(total_reclaim)} reclaimable)"
            )

    def _rule_newest(self):
        apply_keep_newest(self.groups)
        self.tree_view.refresh_views()

    def _rule_oldest(self):
        apply_keep_oldest(self.groups)
        self.tree_view.refresh_views()

    def _rule_shortest(self):
        apply_keep_shortest_path(self.groups)
        self.tree_view.refresh_views()

    def _rule_prefer_folder(self):
        folder = filedialog.askdirectory(title="Select Folder to Keep Duplicates Inside")
        if folder:
            apply_prefer_folder(self.groups, folder)
            self.tree_view.refresh_views()

    def _execute_dedup(self):
        validation_errors = validate_safety_invariants(self.groups)
        if validation_errors:
            messagebox.showerror(
                "Cannot Proceed with Dedup",
                "Safety Invariant Violation:\n\n" + "\n".join(validation_errors[:5]) +
                (f"\n... and {len(validation_errors) - 5} more" if len(validation_errors) > 5 else "")
            )
            return

        total_toss = sum(g.toss_count for g in self.groups)
        total_reclaim = sum(g.reclaimable_bytes for g in self.groups)
        if total_toss == 0:
            messagebox.showinfo("No Files to Dedup", "No files are currently marked as [TOSS].")
            return

        recycle_enabled = self.var_recycle.get()
        target_desc = "Windows Recycle Bin (Restorable)" if recycle_enabled else "PERMANENT DELETION (Irreversible!)"

        confirm = messagebox.askyesno(
            "Confirm Deduplication",
            f"Are you sure you want to deduplicate now?\n\n"
            f"• Files to remove: {total_toss}\n"
            f"• Disk space to recover: {format_size(total_reclaim)}\n"
            f"• Destination: {target_desc}\n\n"
            f"Safety check passed: At least one original copy will be kept for every group.",
            icon="warning" if not recycle_enabled else "question"
        )
        if not confirm:
            return

        try:
            deleted_count, freed, errors = execute_deduplication(self.groups, use_recycle_bin=recycle_enabled)

            # Keep only groups that still have 2 or more files
            self.groups = [g for g in self.groups if len(g.entries) >= 2]
            self.tree_view.populate(self.groups)

            err_msg = ""
            if errors:
                err_msg = f"\n\nEncountered {len(errors)} error(s) during removal:\n" + "\n".join(f"{p}: {e}" for p, e in errors[:5])

            messagebox.showinfo(
                "Deduplication Complete",
                f"Successfully removed {deleted_count} file(s), reclaiming {format_size(freed)}!{err_msg}"
            )
        except Exception as ex:
            messagebox.showerror("Error", f"Deduplication failed: {str(ex)}")

def main():
    app = WindedupApp()
    app.mainloop()

if __name__ == "__main__":
    main()
