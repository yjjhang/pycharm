# 張詠鈞的python工作區
# File: flask_demo
# Created: 2026/1/17 下午 01:59

import os
import math
import pyodbc
from flask import Flask, render_template, request

app = Flask(__name__)

# ---- MSSQL Connection Settings ----
# 你可以直接改這裡（或改成環境變數也行）
DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_NAME = os.getenv("DB_NAME", "job_seek")
DB_USER = os.getenv("DB_USER", "cim")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")

# 你機器上可能是 "ODBC Driver 17 for SQL Server" 或 "ODBC Driver 18 for SQL Server"
ODBC_DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 17 for SQL Server")

def get_conn():
    """
    ODBC Driver 18 預設 Encrypt=Yes，若你是本機開發，最省事是 TrustServerCertificate=Yes。
    若你使用 Driver 17，多數情況 Encrypt 不強制。
    """
    conn_str = (
        f"DRIVER={{{ODBC_DRIVER}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
        "TrustServerCertificate=Yes;"
    )
    return pyodbc.connect(conn_str, timeout=5)

def rows_to_dicts(cursor, rows):
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, r)) for r in rows]

@app.get("/")
def index():
    return jobs()

@app.get("/jobs")
def jobs():
    # ---- Query Params ----
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=30, type=int)
    page = max(page, 1)
    page_size = max(min(page_size, 200), 5)  # 限制一下避免一次爆量

    keyword = (request.args.get("keyword") or "").strip()
    areas = (request.args.get("areas") or "").strip()
    snapshot_date = (request.args.get("snapshot_date") or "").strip()  # 'YYYY-MM-DD' or empty

    where = []
    params = []

    # 你表內 keyword/areas 是快照的查詢條件，也可當篩選
    if keyword:
        where.append("[keyword] LIKE ?")
        params.append(f"%{keyword}%")

    if areas:
        where.append("[areas] LIKE ?")
        params.append(f"%{areas}%")

    if snapshot_date:
        where.append("[snapshot_date] = ?")
        params.append(snapshot_date)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    offset = (page - 1) * page_size

    count_sql = f"""
        SELECT COUNT(1)
        FROM [job_seek].[dbo].[job_snapshot]
        {where_sql}
    """

    data_sql = f"""
        SELECT
            [id],
            [snapshot_date],
            [snapshot_time],
            [keyword],
            [areas],
            [job_id],
            [title],
            [company],
            [location],
            [salary_text],
            [post_date],
            [url]
        FROM [job_seek].[dbo].[job_snapshot]
        {where_sql}
        ORDER BY [snapshot_time] DESC, [id] DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY;
    """

    with get_conn() as conn:
        cur = conn.cursor()

        # total count
        cur.execute(count_sql, params)
        total = int(cur.fetchone()[0])

        # page data
        cur.execute(data_sql, params + [offset, page_size])
        rows = cur.fetchall()
        items = rows_to_dicts(cur, rows)

    total_pages = max(1, math.ceil(total / page_size))

    return render_template(
        "jobs.html",
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        keyword=keyword,
        areas=areas,
        snapshot_date=snapshot_date,
    )

if __name__ == "__main__":
    # http://127.0.0.1:5000/jobs
    app.run(host="127.0.0.1", port=5000, debug=True)
