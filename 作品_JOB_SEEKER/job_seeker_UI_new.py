# 張詠鈞的python工作區
# File: job_seeker_UI_new
# Created: 2026/1/31 下午 03:14
# -*- coding: utf-8 -*-
"""
job_seeker_UI.py
- 匯入你的「job_seeker.py」使用原本抓取/解析/輸出 CSV
- UI：商業化版（Header + Card + Table + StatusBar + Progress）
"""

import os
import sys
import threading
import queue
import importlib.util
import webbrowser
import urllib.request
import subprocess

from typing import List, Dict, Optional
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from urllib.error import URLError


FLASK_URL = "http://127.0.0.1:5000/"


# -------------------------
# 動態載入（支援中文檔名）
# -------------------------
def load_job_module() -> object:
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 確保同層模組（area_mapper / job_MSSQL_db）可被 import
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    candidates = ["job_seeker.py"]
    py_path: Optional[str] = None
    for fn in candidates:
        p = os.path.join(base_dir, fn)
        if os.path.isfile(p):
            py_path = p
            break

    if not py_path:
        raise FileNotFoundError(
            f"同層找不到：{', '.join(candidates)}\n"
            f"請確認 UI 與你的主程式放同一資料夾。"
        )

    spec = importlib.util.spec_from_file_location("job_tracker_module", py_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("無法載入模組（spec 建立失敗）。")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# -------------------------
# Entry Placeholder（保留你原本）
# -------------------------
class PlaceholderEntry(tk.Entry):
    def __init__(self, master, placeholder: str, width=60, **kwargs):
        super().__init__(master, width=width, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = "#94a3b8"
        self.normal_color = self.cget("fg") or "#e5e7eb"
        self._has_placeholder = False

        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self._set_placeholder()

    def _set_placeholder(self):
        self.delete(0, tk.END)
        self.insert(0, self.placeholder)
        self.config(fg=self.placeholder_color)
        self._has_placeholder = True

    def _on_focus_in(self, _):
        if self._has_placeholder:
            self.delete(0, tk.END)
            self.config(fg=self.normal_color)
            self._has_placeholder = False

    def _on_focus_out(self, _):
        if not self.get().strip():
            self._set_placeholder()

    def get_value(self) -> str:
        return "" if self._has_placeholder else self.get().strip()


def trunc(s: str, n: int) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[: max(0, n - 1)] + "…"


# -------------------------
# 商業版 UI（保留功能 / 只升級外觀與佈局）
# -------------------------
class JobSearchUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("104 職缺蒐尋器")
        self.geometry("1180x720")
        self.minsize(1080, 640)

        self._q: "queue.Queue[tuple]" = queue.Queue()

        try:
            self.job_mod = load_job_module()
        except Exception as e:
            messagebox.showerror("啟動失敗", str(e))
            raise

        # base_dir / csv_dir（保留你原本邏輯）
        this_dir = os.path.dirname(os.path.abspath(__file__))
        proj_dir = os.path.join(this_dir, "作品_JOB_SEEKER")
        if os.path.isdir(proj_dir):
            self.base_dir = proj_dir
        else:
            self.base_dir = this_dir

        self.csv_dir = os.path.join(self.base_dir, "csv_file")
        os.makedirs(self.csv_dir, exist_ok=True)

        self.flask_url = FLASK_URL

        # 商業化 theme
        self._apply_theme()

        # Build UI
        self._build_ui()

        # queue poll
        self.after(120, self._poll_queue)

        # initial
        self.set_status("待命")

    # -------------------------
    # Theme
    # -------------------------
    def _apply_theme(self):
        # Colors (商業感：深色系 + card + 清楚層級)
        self.C_BG = "#0b1220"        # app background
        self.C_HEADER = "#0f172a"    # header
        self.C_CARD = "#111c33"      # card
        self.C_TEXT = "#e5e7eb"
        self.C_MUTED = "#94a3b8"
        self.C_BORDER = "#23314f"
        self.C_PRIMARY = "#3b82f6"
        self.C_PRIMARY_H = "#2563eb"

        self.configure(bg=self.C_BG)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background=self.C_BG)
        style.configure("Card.TFrame", background=self.C_CARD)
        style.configure("Header.TFrame", background=self.C_HEADER)

        style.configure("Title.TLabel", background=self.C_HEADER, foreground=self.C_TEXT,
                        font=("Segoe UI", 16, "bold"))
        style.configure("SubTitle.TLabel", background=self.C_HEADER, foreground=self.C_MUTED,
                        font=("Segoe UI", 10))

        style.configure("H1.TLabel", background=self.C_BG, foreground=self.C_TEXT,
                        font=("Segoe UI", 11, "bold"))
        style.configure("Muted.TLabel", background=self.C_BG, foreground=self.C_MUTED)

        style.configure("CardLabel.TLabel", background=self.C_CARD, foreground=self.C_TEXT,
                        font=("Segoe UI", 10, "bold"))
        style.configure("CardHint.TLabel", background=self.C_CARD, foreground=self.C_MUTED)

        # Buttons
        style.configure("Primary.TButton",
                        background=self.C_PRIMARY,
                        foreground="white",
                        padding=(14, 10),
                        borderwidth=0)
        style.map("Primary.TButton", background=[("active", self.C_PRIMARY_H)])

        style.configure("Secondary.TButton",
                        background=self.C_BORDER,
                        foreground=self.C_TEXT,
                        padding=(14, 10),
                        borderwidth=0)
        style.map("Secondary.TButton", background=[("active", "#2b3b61")])

        # Treeview (更像產品表格)
        style.configure("Treeview",
                        background="#0b1326",
                        fieldbackground="#0b1326",
                        foreground=self.C_TEXT,
                        rowheight=28,
                        borderwidth=0)
        style.map("Treeview",
                  background=[("selected", "#1f3b75")],
                  foreground=[("selected", "white")])

        style.configure("Treeview.Heading",
                        background="#122046",
                        foreground=self.C_TEXT,
                        relief="flat",
                        font=("Segoe UI", 10, "bold"))
        style.map("Treeview.Heading", background=[("active", "#1a2b5c")])

        # Progressbar
        style.configure("Thin.Horizontal.TProgressbar", thickness=6)

    # -------------------------
    # UI Layout
    # -------------------------
    def _build_ui(self):
        # Root grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ttk.Frame(self, style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ttk.Label(header, text="104 職缺蒐尋器", style="Title.TLabel") \
            .grid(row=0, column=0, sticky="w", padx=18, pady=(14, 2))
        ttk.Label(header, text="輸入條件 → 一鍵抓取 → 匯出 CSV → 預覽結果（含 MSSQL 寫入）", style="SubTitle.TLabel") \
            .grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

        # Body
        body = ttk.Frame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=14, pady=12)
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Left panel (card + buttons + progress)
        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        left.grid_rowconfigure(2, weight=1)

        # Search card
        card = ttk.Frame(left, style="Card.TFrame")
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        ttk.Label(card, text="搜尋條件", style="CardLabel.TLabel") \
            .grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

        ttk.Label(card, text="關鍵字", style="CardHint.TLabel") \
            .grid(row=1, column=0, sticky="w", padx=14, pady=(4, 2))

        # 用你原本 PlaceholderEntry，但加上商業感字體/顏色/邊框
        self.ent_keyword = PlaceholderEntry(
            card, "軟體工程師等等", width=30,
            font=("Segoe UI", 10),
            bg="#0b1326", fg=self.C_TEXT,
            insertbackground=self.C_TEXT,
            relief="flat", highlightthickness=1,
            highlightbackground=self.C_BORDER,
            highlightcolor=self.C_PRIMARY
        )
        self.ent_keyword.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10), ipady=6)

        ttk.Label(card, text="地區（逗號分隔多筆）", style="CardHint.TLabel") \
            .grid(row=3, column=0, sticky="w", padx=14, pady=(2, 2))

        self.ent_area = PlaceholderEntry(
            card, "桃園市,桃園市龜山區", width=30,
            font=("Segoe UI", 10),
            bg="#0b1326", fg=self.C_TEXT,
            insertbackground=self.C_TEXT,
            relief="flat", highlightthickness=1,
            highlightbackground=self.C_BORDER,
            highlightcolor=self.C_PRIMARY
        )
        self.ent_area.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 6), ipady=6)

        ttk.Label(card, text="範例：台北市,新北市板橋區", style="CardHint.TLabel") \
            .grid(row=5, column=0, sticky="w", padx=14, pady=(0, 12))

        # Buttons
        btns = ttk.Frame(left)
        btns.grid(row=1, column=0, sticky="ew", pady=12)
        btns.grid_columnconfigure(0, weight=1)

        self.btn_export = ttk.Button(btns, text="產出 CSV（並顯示預覽）", style="Primary.TButton",
                                     command=self.on_export_clicked)
        self.btn_export.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.btn_open_folder = ttk.Button(btns, text="瀏覽 CSV 檔案", style="Secondary.TButton",
                                          command=self.on_open_csv_folder_clicked)
        self.btn_open_folder.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        self.btn_web = ttk.Button(btns, text="開啟 Web 版", style="Secondary.TButton",
                                  command=self.on_open_web_clicked)
        self.btn_web.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        # Progress / status in left card
        prog = ttk.Frame(left, style="Card.TFrame")
        prog.grid(row=2, column=0, sticky="ew")
        prog.grid_columnconfigure(0, weight=1)

        ttk.Label(prog, text="處理狀態", style="CardLabel.TLabel") \
            .grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

        self.progress = ttk.Progressbar(prog, mode="indeterminate", style="Thin.Horizontal.TProgressbar")
        self.progress.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        self.lbl_status = ttk.Label(prog, text="狀態：待命", style="CardHint.TLabel")
        self.lbl_status.grid(row=2, column=0, sticky="w", padx=14, pady=(0, 12))

        # Right panel: result table card
        right = ttk.Frame(body, style="Card.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        topbar = ttk.Frame(right, style="Card.TFrame")
        topbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        topbar.grid_columnconfigure(0, weight=1)

        ttk.Label(topbar, text="搜尋結果預覽（表格概略，完整看 CSV）", style="CardLabel.TLabel") \
            .grid(row=0, column=0, sticky="w")

        self.lbl_count = ttk.Label(topbar, text="0 筆", style="CardHint.TLabel")
        self.lbl_count.grid(row=0, column=1, sticky="e")

        table_frame = ttk.Frame(right, style="Card.TFrame")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        cols = ("no", "title", "company", "salary", "location")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")

        # headings + clickable sort
        self._set_heading("no", "No.")
        self._set_heading("title", "Title")
        self._set_heading("company", "Company")
        self._set_heading("salary", "Salary")
        self._set_heading("location", "Location")

        self.tree.column("no", width=60, anchor="center", stretch=False)
        self.tree.column("title", width=360, anchor="w")
        self.tree.column("company", width=260, anchor="w")
        self.tree.column("salary", width=160, anchor="center", stretch=False)
        self.tree.column("location", width=220, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # zebra
        self.tree.tag_configure("odd", background="#0b1326")
        self.tree.tag_configure("even", background="#0e1933")

        # empty hint
        self.empty_hint = ttk.Label(
            table_frame,
            text="尚無資料。請在左側輸入條件後點「產出 CSV」。",
            style="Muted.TLabel"
        )
        self.empty_hint.place(relx=0.5, rely=0.5, anchor="center")

        # Footer (status bar)
        footer = ttk.Frame(self)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        self.footer_left = ttk.Label(footer, text="Ready", style="Muted.TLabel")
        self.footer_left.grid(row=0, column=0, sticky="w", padx=14, pady=10)

        self.footer_right = ttk.Label(footer, text="", style="Muted.TLabel")
        self.footer_right.grid(row=0, column=1, sticky="e", padx=14, pady=10)

    # -------------------------
    # Table sort helpers
    # -------------------------
    def _set_heading(self, col, text):
        self.tree.heading(col, text=text, command=lambda c=col: self._sort_by(c, False))

    def _sort_by(self, col, descending):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children("")]
        data.sort(reverse=descending)
        for index, (_, item) in enumerate(data):
            self.tree.move(item, "", index)
            self.tree.item(item, tags=("even" if index % 2 == 0 else "odd",))
        self.tree.heading(col, command=lambda: self._sort_by(col, not descending))

    # -------------------------
    # Busy / Status (保持你原本 set_status 介面)
    # -------------------------
    def set_status(self, s: str):
        # 上方 card 的狀態
        if hasattr(self, "lbl_status"):
            self.lbl_status.config(text=f"狀態：{s}")

        # footer
        if hasattr(self, "footer_left"):
            self.footer_left.config(text=f"Status: {s}")

        self.update_idletasks()

    def _set_busy(self, busy: bool):
        if busy:
            try:
                self.progress.start(12)
            except Exception:
                pass
            self.btn_export.state(["disabled"])
            self.btn_open_folder.state(["disabled"])
            self.btn_web.state(["disabled"])
            if hasattr(self, "footer_right"):
                self.footer_right.config(text="Working…")
        else:
            try:
                self.progress.stop()
            except Exception:
                pass
            self.btn_export.state(["!disabled"])
            self.btn_open_folder.state(["!disabled"])
            self.btn_web.state(["!disabled"])
            if hasattr(self, "footer_right"):
                self.footer_right.config(text="")

    # -------------------------
    # Table fill (保留你原本邏輯，外觀微調)
    # -------------------------
    def _clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _fill_table(self, rows: List[Dict[str, str]], preview_limit: int = 30):
        self._clear_table()

        n = min(preview_limit, len(rows))
        self.lbl_count.config(text=f"{n} / {len(rows)} 筆")
        self.empty_hint.place_forget()

        self.set_status(f"完成（顯示前 {n} 筆，CSV 為完整資料）")

        for i, r in enumerate(rows[:n], start=1):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert(
                "",
                "end",
                values=(
                    i,
                    trunc(r.get("title", ""), 45),
                    trunc(r.get("company", ""), 28),
                    trunc(r.get("salary_text", ""), 18),
                    trunc(r.get("location", ""), 20),
                ),
                tags=(tag,)
            )

        if n == 0:
            self.lbl_count.config(text="0 筆")
            self.empty_hint.place(relx=0.5, rely=0.5, anchor="center")

    # -------------------------
    # Buttons (保留你原本功能)
    # -------------------------
    def on_open_csv_folder_clicked(self):
        try:
            os.startfile(self.csv_dir)
        except Exception:
            subprocess.Popen(["explorer", self.csv_dir])

    def on_open_web_clicked(self):
        try:
            urllib.request.urlopen(self.flask_url, timeout=1)
            webbrowser.open_new_tab(self.flask_url)
        except URLError:
            messagebox.showerror("Web 版未啟動", "Flask 伺服器尚未啟動，請先執行 flask_demo.py")

    def on_export_clicked(self):
        keyword = self.ent_keyword.get_value()
        areas_text = self.ent_area.get_value()

        if not keyword or not areas_text:
            messagebox.showwarning("提醒", "關鍵字與區域不可為空。")
            return

        area_inputs = [a.strip() for a in areas_text.replace("，", ",").split(",") if a.strip()]
        try:
            resolved = [self.job_mod.resolve_area(a) for a in area_inputs]
        except Exception as e:
            messagebox.showerror("地區解析失敗", str(e))
            return

        area_codes_csv = ",".join(r.area_code for r in resolved)
        area_names = ",".join(r.matched_name for r in resolved)

        out_name = f"{self.job_mod.now_tag()}_104_{self.job_mod.safe_filename(keyword)}_{self.job_mod.safe_filename(area_names)}.csv"
        save_path = os.path.join(self.csv_dir, out_name)
        if os.path.exists(save_path):
            name, ext = os.path.splitext(out_name)
            k = 1
            while True:
                candidate = os.path.join(self.csv_dir, f"{name}_{k:02d}{ext}")
                if not os.path.exists(candidate):
                    save_path = candidate
                    break
                k += 1

        # UI busy
        self._set_busy(True)
        self.set_status("查詢中…")
        self._clear_table()
        self.lbl_count.config(text="0 筆")
        self.empty_hint.place(relx=0.5, rely=0.5, anchor="center")

        th = threading.Thread(
            target=self._worker_fetch_and_export,
            args=(save_path, keyword, area_names, area_codes_csv),
            daemon=True
        )
        th.start()

    def _worker_fetch_and_export(self, save_path: str, keyword: str, area_names: str, area_codes_csv: str):
        try:
            max_pages = 3

            # ✅ 只走 Playwright
            all_rows = self.job_mod.fetch_jobs_via_playwright(
                keyword=keyword,
                area_text=area_names,
                area_codes_csv=area_codes_csv,
                max_pages=max_pages,
                headless=False,
                timeout_ms=45000
            )

            if not all_rows:
                self._q.put(("error", "Playwright 沒抓到任何職缺（可能 104 當下限制或條件太嚴格）。"))
                return

            # 1) 寫 CSV
            self.job_mod.write_csv(all_rows, save_path, keyword=keyword, areas_text=area_names)

            # 2) ✅ 寫入 MSSQL
            try:
                from job_MSSQL_db import insert_snapshot_rows

                conn_str = ""
                if hasattr(self.job_mod, "CONN_STR"):
                    conn_str = getattr(self.job_mod, "CONN_STR") or ""
                elif hasattr(self.job_mod, "conn_str"):
                    conn_str = getattr(self.job_mod, "conn_str") or ""
                elif hasattr(self.job_mod, "get_conn_str"):
                    conn_str = self.job_mod.get_conn_str() or ""

                if not conn_str.strip():
                    raise RuntimeError("找不到 MSSQL 連線字串（請在主程式提供 CONN_STR 或 get_conn_str()）。")

                inserted = insert_snapshot_rows(
                    rows=all_rows,
                    keyword=keyword,
                    areas=area_names,
                    conn_str=conn_str,
                    snapshot_time=None
                )

                self._q.put(("status", f"MSSQL：新增 {inserted} 筆（同日重複 job_id 不會更新快照，屬既有設計）"))

            except Exception as e:
                self._q.put(("status", f"MSSQL 寫入失敗（不影響 CSV/預覽）：{e}"))

            # 3) 更新 UI
            self._q.put(("rows", all_rows))
            self._q.put(("done", f"匯出成功：\n{save_path}\n\n共 {len(all_rows)} 筆（CSV 為完整資料）"))

        except Exception as e:
            self._q.put(("error", str(e)))
        finally:
            self._q.put(("enable", None))

    def _poll_queue(self):
        try:
            while True:
                typ, payload = self._q.get_nowait()
                if typ == "rows":
                    self._fill_table(payload, preview_limit=30)
                elif typ == "done":
                    messagebox.showinfo("成功", payload)
                elif typ == "error":
                    self.set_status("失敗")
                    messagebox.showerror("錯誤", payload)
                elif typ == "enable":
                    self._set_busy(False)
                elif typ == "status":
                    self.set_status(payload)
        except queue.Empty:
            pass
        finally:
            self.after(120, self._poll_queue)


def main():
    app = JobSearchUI()
    app.mainloop()


if __name__ == "__main__":
    main()
