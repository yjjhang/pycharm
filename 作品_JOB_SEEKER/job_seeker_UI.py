# 張詠鈞的python工作區
# File: 職缺蒐尋器_UI
# Created: 2026/1/12 下午 03:53

# -*- coding: utf-8 -*-
"""
job_seeker_UI.py
- 匯入你的「職缺蒐尋器.py / job_seeker.py」使用原本抓取/解析/輸出 CSV
- 預覽區改成 ttk.Treeview（類似 C# DataGridView），只顯示前 N 筆概略欄位
"""

import os
import sys
import time
import threading
import queue
import importlib.util
import webbrowser
import urllib.request
import subprocess

from typing import List, Dict, Optional
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
from urllib.error import URLError

# -------------------------
# 動態載入（支援中文檔名）
# -------------------------

FLASK_URL = "http://127.0.0.1:5000/"

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
# Entry Placeholder
# -------------------------
class PlaceholderEntry(tk.Entry):
    def __init__(self, master, placeholder: str, width=60, **kwargs):
        super().__init__(master, width=width, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = "#888"
        self.normal_color = self.cget("fg") or "#000"
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
# UI
# -------------------------
class JobSearchUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("104 職缺蒐尋器（UI）")
        self.geometry("1100x680")

        self._q: "queue.Queue[tuple]" = queue.Queue()

        try:
            self.job_mod = load_job_module()
        except Exception as e:
            messagebox.showerror("啟動失敗", str(e))
            raise

        self._build_ui()
        self.after(120, self._poll_queue)

        self.flask_url = "http://127.0.0.1:5000/"

        # 取得目前 UI 這支 .py 所在資料夾 = 專案根目錄（你的檔案都放同層時最準）
        this_dir = os.path.dirname(os.path.abspath(__file__))

        # 如果旁邊存在 作品_JOB_SEEKER 這個資料夾，就把它當專案根目錄
        proj_dir = os.path.join(this_dir, "作品_JOB_SEEKER")
        if os.path.isdir(proj_dir):
            self.base_dir = proj_dir
        else:
            # 如果你本來就已經在作品資料夾內執行，就用目前資料夾
            self.base_dir = this_dir

        # CSV 輸出資料夾
        self.csv_dir = os.path.join(self.base_dir, "csv_file")
        os.makedirs(self.csv_dir, exist_ok=True)

    def _build_ui(self):
        frm = tk.Frame(self)
        frm.pack(fill="x", padx=12, pady=10)

        tk.Label(frm, text="1. 請輸入職缺關鍵字：").grid(row=0, column=0, sticky="w")
        self.ent_keyword = PlaceholderEntry(frm, "軟體工程師等等", width=62)
        self.ent_keyword.grid(row=0, column=1, sticky="w", padx=6)

        tk.Label(frm, text="2. 輸入區域（逗號分隔多筆）：").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.ent_area = PlaceholderEntry(frm, "桃園市,桃園市龜山區", width=62)
        self.ent_area.grid(row=1, column=1, sticky="w", padx=6, pady=(8, 0))

        tk.Label(frm, text="說明：可用 , 隔開打多個查詢地點", fg="#666").grid(
            row=2, column=1, sticky="w", padx=6, pady=(2, 0)
        )

        btnfrm = tk.Frame(self)
        btnfrm.pack(fill="x", padx=12)

        self.btn_export = tk.Button(btnfrm, text="匯出成 CSV（並顯示預覽）", command=self.on_export_clicked)
        self.btn_export.pack(side="left")

        self.btn_open_folder = tk.Button(btnfrm, text="瀏覽 CSV 檔案", command=self.on_open_csv_folder_clicked)
        self.btn_open_folder.pack(side="left", padx=8)

        self.btn_web = tk.Button(btnfrm, text="開啟 Web 版", command=self.on_open_web_clicked)
        self.btn_web.pack(side="left", padx=8)

        self.lbl_status = tk.Label(btnfrm, text="狀態：待命", fg="#333")
        self.lbl_status.pack(side="left", padx=12)

        # ===== 預覽區：Treeview (像 DataGridView) =====
        tk.Label(self, text="4. 104 求職資訊預覽（表格概略，完整看 CSV）：").pack(anchor="w", padx=12, pady=(10, 0))

        table_frame = tk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=12, pady=10)

        cols = ("no", "title", "company", "salary", "location")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=18)
        self.tree.heading("no", text="No.")
        self.tree.heading("title", text="Title")
        self.tree.heading("company", text="Company")
        self.tree.heading("salary", text="Salary")
        self.tree.heading("location", text="Location")

        # 欄寬/對齊（你可自行調）
        self.tree.column("no", width=60, anchor="e", stretch=False)
        self.tree.column("title", width=360, anchor="w", stretch=True)
        self.tree.column("company", width=260, anchor="w", stretch=True)
        self.tree.column("salary", width=160, anchor="w", stretch=False)
        self.tree.column("location", width=220, anchor="w", stretch=False)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # 讓 Treeview 看起來更像表格（可選）
        # ===== Excel-like style =====
        style = ttk.Style()
        # Windows 上建議用 vista / winnative；若不可用就 fallback
        for theme in ("vista", "winnative", "clam"):
            try:
                style.theme_use(theme)
                break
            except Exception:
                pass

        style.configure(
            "Excel.Treeview",
            rowheight=24,
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Excel.Treeview.Heading",
            font=("Segoe UI", 10, "bold"),
        )

        # 套用 style
        self.tree.configure(style="Excel.Treeview")

        # 斑馬紋（很像 Excel）
        self.tree.tag_configure("odd", background="#FFFFFF")
        self.tree.tag_configure("even", background="#F3F6FA")

    def set_status(self, s: str):
        self.lbl_status.config(text=f"狀態：{s}")
        self.update_idletasks()

    def _clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _fill_table(self, rows: List[Dict[str, str]], preview_limit: int = 30):
        self._clear_table()

        n = min(preview_limit, len(rows))
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

    def on_open_csv_folder_clicked(self):
        try:
            os.startfile(self.csv_dir)  # Windows 直接開資料夾
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
        self.btn_export.config(state="disabled")
        self.set_status("查詢中…")
        self._clear_table()

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

            # 2) ✅ 寫入 MSSQL（使用你現成的 insert_snapshot_rows）
            try:
                from job_MSSQL_db import insert_snapshot_rows

                # 嘗試從主程式取得 conn_str（你不需要改 DB 模組）
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
                    self.btn_export.config(state="normal")
                elif typ == "status":
                    self.set_status(payload)
        except queue.Empty:
            pass
        finally:
            self.after(120, self._poll_queue)



if __name__ == "__main__":

    app = JobSearchUI()
    app.mainloop()

