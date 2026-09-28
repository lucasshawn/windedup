import tkinter as tk
from tkinter import ttk, font, filedialog, messagebox
import os
import sys
import queue
import logging
import threading
import traceback
from typing import List, Optional

from windedup.ui.dpi import enable_high_dpi_awareness
from windedup.core.models import DuplicateGroup, ScanProgress, DeleteProgress
from windedup.core.scanner import scan_directory
from windedup.core.rules import (
    apply_keep_newest,
    apply_keep_oldest,
    apply_keep_shortest_path,
    apply_prefer_folder,
    apply_toss_all,
    apply_keep_all
)
from windedup.core.recycle import execute_deduplication, get_completely_discarded_groups
from windedup.core.logger import log_and_show_exception, get_log_file_path
from windedup.core.filter import parse_masks, filter_duplicate_groups
from windedup.ui.tree_view import DuplicateTreeView, format_size
from windedup.ui.progress_dialog import ProgressDialog
from windedup.ui.delete_dialog import DeleteProgressDialog
from windedup.ui.about_dialog import AboutDialog

class WindedupApp(tk.Tk):
    def report_callback_exception(self, exc, val, tb):
        """Root Tkinter callback exception hook to log and show crashes."""
        log_and_show_exception(exc, val, tb, context="Tkinter Event Callback")

    def __init__(self):
        enable_high_dpi_awareness()
        super().__init__()
        self.title("Windedup - Duplicate File Finder & Deduplicator")
        self.geometry("1180x740")
        self.minsize(920, 580)

        self._set_app_icon()
        self._configure_styling()

        self.all_groups: List[DuplicateGroup] = []
        self.displayed_groups: List[DuplicateGroup] = []
        self._filter_debounce_id: Optional[str] = None

        self.scan_queue: queue.Queue = queue.Queue()
        self.delete_queue: queue.Queue = queue.Queue()
        self.cancel_event: Optional[threading.Event] = None
        self.delete_cancel_event: Optional[threading.Event] = None
        self.progress_dialog: Optional[ProgressDialog] = None
        self.delete_dialog: Optional[DeleteProgressDialog] = None

        self._build_ui()
        self._check_previous_crash()

    @property
    def groups(self) -> List[DuplicateGroup]:
        """Returns the currently active / filtered groups."""
        return self.displayed_groups

    @groups.setter
    def groups(self, value: List[DuplicateGroup]):
        self.displayed_groups = value

    def _check_previous_crash(self):
        """Detects if previous session crashed and displays the reporter dialog once."""
        from windedup.core.logger import consume_previous_crash
        crash_info = consume_previous_crash()
        if crash_info:
            from windedup.ui.crash_dialog import CrashReportDialog
            self.after(200, lambda: CrashReportDialog(self, crash_info))

    def _show_about_dialog(self):
        AboutDialog(self)

    def _set_app_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        ico_path = os.path.join(base_dir, "assets", "icon.ico")
        png_path = os.path.join(base_dir, "assets", "icon.png")

        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        if os.path.exists(png_path):
            try:
                self._icon_img = tk.PhotoImage(file=png_path)
                self.iconphoto(True, self._icon_img)
            except Exception:
                pass

    def _configure_styling(self):
        for font_name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
            try:
                f = font.nametofont(font_name)
                f.configure(family="Segoe UI", size=10)
            except Exception:
                pass

        try:
            hf = font.nametofont("TkHeadingFont")
            hf.configure(family="Segoe UI", size=10, weight="bold")
        except Exception:
            pass

        self.style = ttk.Style(self)
        available_themes = self.style.theme_names()
        for theme in ("vista", "winnative", "clam", "default"):
            if theme in available_themes:
                self.style.theme_use(theme)
                break

    def _build_ui(self):
        # 0. Top Menu Bar
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="About Windedup...", command=self._show_about_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menubar)

        # 1. Top Folder Selection Bar
        top_frame = ttk.LabelFrame(self, text=" Target Folder ", padding=(14, 10))
        top_frame.pack(fill="x", padx=14, pady=(12, 6))

        self.txt_folder = ttk.Entry(top_frame, font=("Segoe UI", 10))
        self.txt_folder.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_browse = ttk.Button(top_frame, text="Browse...", command=self._browse_folder)
        btn_browse.pack(side="left", padx=(0, 8))

        self.btn_scan = ttk.Button(top_frame, text="Scan for Duplicates", command=self._start_scan)
        self.btn_scan.pack(side="left")

        # 2. Path & Name Filter Masks (Real-Time)
        filter_frame = ttk.LabelFrame(self, text=" Path & Name View Filters (Semicolon-Separated) ", padding=(14, 8))
        filter_frame.pack(fill="x", padx=14, pady=(0, 6))

        lbl_hint = ttk.Label(
            filter_frame,
            text="Filter which duplicates appear in the view (e.g. Include: *.png; docs\\* | Exclude: *.tmp; *node_modules*; temp). To protect a folder from deletion, use 'Prefer Folder...' below.",
            font=("Segoe UI", 8),
            foreground="#555555"
        )
        lbl_hint.pack(anchor="w", pady=(0, 6))

        filter_grid = ttk.Frame(filter_frame)
        filter_grid.pack(fill="x")

        lbl_inc = ttk.Label(filter_grid, text="Include:", font=("Segoe UI", 9, "bold"))
        lbl_inc.grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2)

        self.txt_include = ttk.Entry(filter_grid, font=("Segoe UI", 9))
        self.txt_include.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=2)

        lbl_exc = ttk.Label(filter_grid, text="Exclude:", font=("Segoe UI", 9, "bold"))
        lbl_exc.grid(row=0, column=2, sticky="w", padx=(0, 6), pady=2)

        self.txt_exclude = ttk.Entry(filter_grid, font=("Segoe UI", 9))
        self.txt_exclude.grid(row=0, column=3, sticky="ew", padx=(0, 10), pady=2)

        self.btn_clear_filters = ttk.Button(filter_grid, text="Clear Filters", command=self._clear_filters)
        self.btn_clear_filters.grid(row=0, column=4, sticky="e", pady=2)

        filter_grid.columnconfigure(1, weight=1)
        filter_grid.columnconfigure(3, weight=1)

        self.txt_include.bind("<KeyRelease>", self._on_filter_changed)
        self.txt_exclude.bind("<KeyRelease>", self._on_filter_changed)

        # 3. Quick Dedup & Rules Toolbar
        tools_frame = ttk.Frame(self, padding=(14, 6))
        tools_frame.pack(fill="x")

        ttk.Label(tools_frame, text="Quick Filters:", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 8))
        self.btn_rule_newest = ttk.Button(tools_frame, text="Keep Newest", command=self._rule_newest, state="disabled")
        self.btn_rule_newest.pack(side="left", padx=2)

        self.btn_rule_oldest = ttk.Button(tools_frame, text="Keep Oldest", command=self._rule_oldest, state="disabled")
        self.btn_rule_oldest.pack(side="left", padx=2)

        self.btn_rule_shortest = ttk.Button(tools_frame, text="Keep Shortest Path", command=self._rule_shortest, state="disabled")
        self.btn_rule_shortest.pack(side="left", padx=2)

        self.btn_rule_folder = ttk.Button(tools_frame, text="Prefer Folder...", command=self._rule_prefer_folder, state="disabled")
        self.btn_rule_folder.pack(side="left", padx=2)

        ttk.Separator(tools_frame, orient="vertical").pack(side="left", fill="y", padx=8, pady=2)

        self.btn_toss_all = ttk.Button(tools_frame, text="Check All (Toss All)", command=self._rule_toss_all, state="disabled")
        self.btn_toss_all.pack(side="left", padx=2)

        self.btn_keep_all = ttk.Button(tools_frame, text="Uncheck All (Keep All)", command=self._rule_keep_all, state="disabled")
        self.btn_keep_all.pack(side="left", padx=2)

        self.lbl_stats = ttk.Label(tools_frame, text="Select a folder to begin scanning", font=("Segoe UI", 10), foreground="#005A9E")
        self.lbl_stats.pack(side="right", padx=5)

        # 3. Main Hierarchical Treeview with Checkboxes
        tree_frame = ttk.Frame(self, padding=(14, 6))
        tree_frame.pack(fill="both", expand=True)

        self.tree_view = DuplicateTreeView(tree_frame, on_selection_changed=self._update_stats_display)
        self.tree_view.pack(fill="both", expand=True)

        # 4. Bottom Action Bar
        bottom_frame = ttk.Frame(self, padding=(14, 12))
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
        try:
            def on_prog(prog: ScanProgress):
                self.scan_queue.put(("progress", prog))

            logging.info(f"Scan worker starting for directory: {folder}")
            groups = scan_directory(folder, progress_callback=on_prog, cancel_event=cancel_ev)
            logging.info(f"Scan worker completed successfully. Found {len(groups)} duplicate groups.")
            self.scan_queue.put(("done", groups))
        except Exception as e:
            logging.exception(f"Unhandled exception in scan worker for '{folder}': {e}")
            self.scan_queue.put(("error", (str(e), traceback.format_exc())))

    def _check_scan_queue(self):
        try:
            while not self.scan_queue.empty():
                msg_type, data = self.scan_queue.get_nowait()
                if msg_type == "progress" and self.progress_dialog:
                    self.progress_dialog.update_progress(data)
                elif msg_type == "error":
                    err_msg, tb_str = data
                    if self.progress_dialog:
                        self.progress_dialog.destroy()
                        self.progress_dialog = None
                    self.btn_scan.config(state="normal")
                    messagebox.showerror(
                        "Scan Failed",
                        f"An error occurred while scanning for duplicates:\n\n{err_msg}\n\n"
                        f"A diagnostic log has been written to:\n{get_log_file_path()}"
                    )
                    return
                elif msg_type == "done":
                    if self.progress_dialog:
                        self.progress_dialog.destroy()
                        self.progress_dialog = None
                    self.btn_scan.config(state="normal")
                    self.all_groups = data
                    self._apply_filter()

                    if not self.all_groups:
                        if self.cancel_event and self.cancel_event.is_set():
                            messagebox.showinfo("Scan Cancelled", "Scan was cancelled by the user.")
                        else:
                            messagebox.showinfo("Scan Complete", "No duplicate files found in the selected folder!")
                    elif not self.displayed_groups:
                        messagebox.showinfo(
                            "Scan Complete",
                            f"Found {len(self.all_groups)} duplicate group(s), but none match the active include/exclude filters.\n\n"
                            f"Clear or adjust your filters to view them."
                        )
                    return
        except queue.Empty:
            pass

        self.after(50, self._check_scan_queue)

    def _on_filter_changed(self, event=None):
        """Debounces real-time filter updates so fast typing remains responsive."""
        if self._filter_debounce_id:
            self.after_cancel(self._filter_debounce_id)
        self._filter_debounce_id = self.after(150, self._apply_filter)

    def _clear_filters(self):
        """Clears both include and exclude filters and refreshes the view."""
        self.txt_include.delete(0, tk.END)
        self.txt_exclude.delete(0, tk.END)
        self._apply_filter()

    def _apply_filter(self):
        """Filters in-memory groups according to active include/exclude masks."""
        self._filter_debounce_id = None
        inc_str = self.txt_include.get().strip() if hasattr(self, "txt_include") else ""
        exc_str = self.txt_exclude.get().strip() if hasattr(self, "txt_exclude") else ""

        inc_masks = parse_masks(inc_str)
        exc_masks = parse_masks(exc_str)

        if not inc_masks and not exc_masks:
            self.displayed_groups = list(self.all_groups)
        else:
            self.displayed_groups = filter_duplicate_groups(
                self.all_groups,
                include_masks=inc_masks,
                exclude_masks=exc_masks
            )

        self.tree_view.populate(self.displayed_groups)
        self._update_stats_display()

        has_items = len(self.displayed_groups) > 0
        self._set_rule_buttons_state("normal" if has_items else "disabled")
        self.btn_dedup.config(state="normal" if has_items else "disabled")

    def _set_rule_buttons_state(self, state: str):
        self.btn_rule_newest.config(state=state)
        self.btn_rule_oldest.config(state=state)
        self.btn_rule_shortest.config(state=state)
        self.btn_rule_folder.config(state=state)
        self.btn_toss_all.config(state=state)
        self.btn_keep_all.config(state=state)

    def _update_stats_display(self):
        total_groups = len(self.displayed_groups)
        total_toss = sum(g.toss_count for g in self.displayed_groups)
        total_reclaim = sum(g.reclaimable_bytes for g in self.displayed_groups)

        completely_discarded = len(get_completely_discarded_groups(self.displayed_groups))
        extra_note = f" (⚠️ {completely_discarded} group(s) marked for 100% deletion)" if completely_discarded > 0 else ""

        filter_note = ""
        if len(self.all_groups) != len(self.displayed_groups):
            filter_note = f" (filtered from {len(self.all_groups)} total)"

        if total_groups == 0:
            if self.all_groups:
                self.lbl_stats.config(text=f"0 duplicate groups match active filter ({len(self.all_groups)} total loaded)")
            else:
                self.lbl_stats.config(text="No duplicate files loaded")
        else:
            self.lbl_stats.config(
                text=f"Duplicates: {total_groups} groups{filter_note} | Marked to toss: {total_toss} files ({format_size(total_reclaim)} reclaimable){extra_note}"
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

    def _rule_toss_all(self):
        apply_toss_all(self.groups)
        self.tree_view.refresh_views()

    def _rule_keep_all(self):
        apply_keep_all(self.groups)
        self.tree_view.refresh_views()

    def _execute_dedup(self):
        total_toss = sum(g.toss_count for g in self.groups)
        total_reclaim = sum(g.reclaimable_bytes for g in self.groups)
        if total_toss == 0:
            messagebox.showinfo("No Files to Dedup", "No files are currently checked as [TOSS].")
            return

        recycle_enabled = self.var_recycle.get()
        target_desc = "Windows Recycle Bin (Restorable)" if recycle_enabled else "PERMANENT DELETION (Irreversible!)"

        discarded_groups = get_completely_discarded_groups(self.groups)
        warn_clause = ""
        if discarded_groups:
            warn_clause = (
                f"\n\n⚠️ Notice: {len(discarded_groups)} duplicate group(s) have ALL copies checked to toss "
                f"and will have zero surviving copies left on your drive!"
            )

        confirm = messagebox.askyesno(
            "Confirm Deduplication",
            f"Are you sure you want to deduplicate now?\n\n"
            f"• Files to remove: {total_toss}\n"
            f"• Disk space to recover: {format_size(total_reclaim)}\n"
            f"• Destination: {target_desc}{warn_clause}",
            icon="warning" if (not recycle_enabled or discarded_groups) else "question"
        )
        if not confirm:
            return

        # Disable UI controls during deletion
        self.btn_dedup.config(state="disabled")
        self.btn_scan.config(state="disabled")
        self._set_rule_buttons_state("disabled")

        self.delete_cancel_event = threading.Event()
        self.delete_dialog = DeleteProgressDialog(self, on_cancel=self._cancel_delete)

        worker = threading.Thread(
            target=self._delete_worker,
            args=(recycle_enabled, self.delete_cancel_event),
            daemon=True
        )
        worker.start()
        self.after(30, self._check_delete_queue)

    def _cancel_delete(self):
        if self.delete_cancel_event:
            self.delete_cancel_event.set()

    def _delete_worker(self, use_recycle_bin: bool, cancel_ev: threading.Event):
        try:
            def on_prog(prog: DeleteProgress):
                self.delete_queue.put(("progress", prog))

            logging.info(f"Delete worker starting (use_recycle_bin={use_recycle_bin})")
            deleted_count, freed, errors = execute_deduplication(
                self.groups,
                use_recycle_bin=use_recycle_bin,
                progress_callback=on_prog,
                cancel_event=cancel_ev
            )
            logging.info(f"Delete worker completed. Removed={deleted_count}, Freed={freed}, Errors={len(errors)}")
            self.delete_queue.put(("done", (deleted_count, freed, errors)))
        except Exception as e:
            logging.exception(f"Unhandled exception in delete worker: {e}")
            self.delete_queue.put(("error", (str(e), traceback.format_exc())))

    def _check_delete_queue(self):
        try:
            while not self.delete_queue.empty():
                msg_type, data = self.delete_queue.get_nowait()
                if msg_type == "progress" and self.delete_dialog:
                    self.delete_dialog.update_progress(data)
                elif msg_type == "error":
                    err_msg, tb_str = data
                    if self.delete_dialog:
                        self.delete_dialog.destroy()
                        self.delete_dialog = None
                    self.btn_scan.config(state="normal")
                    if self.groups:
                        self._set_rule_buttons_state("normal")
                        self.btn_dedup.config(state="normal")
                    messagebox.showerror(
                        "Deduplication Failed",
                        f"An error occurred during deduplication:\n\n{err_msg}\n\n"
                        f"A diagnostic log has been written to:\n{get_log_file_path()}"
                    )
                    return
                elif msg_type == "done":
                    deleted_count, freed, errors = data
                    if self.delete_dialog:
                        self.delete_dialog.destroy()
                        self.delete_dialog = None

                    # Re-enable controls
                    self.btn_scan.config(state="normal")

                    # Keep only groups that still have 2 or more files (or clear empty ones)
                    self.all_groups = [g for g in self.all_groups if len(g.entries) >= 2]
                    self._apply_filter()

                    err_msg = ""
                    if errors:
                        err_msg = f"\n\nEncountered {len(errors)} error(s) during removal:\n" + "\n".join(f"{p}: {e}" for p, e in errors[:5])

                    was_cancelled = self.delete_cancel_event and self.delete_cancel_event.is_set()
                    status_title = "Deduplication Stopped" if was_cancelled else "Deduplication Complete"
                    cancel_note = " (Cancelled early by user)" if was_cancelled else ""

                    messagebox.showinfo(
                        status_title,
                        f"Successfully removed {deleted_count} file(s), reclaiming {format_size(freed)}!{cancel_note}{err_msg}"
                    )
                    return
        except queue.Empty:
            pass

        self.after(30, self._check_delete_queue)

def main():
    app = WindedupApp()
    app.mainloop()

if __name__ == "__main__":
    main()
