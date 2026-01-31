# 張詠鈞的python工作區
# File: job_MSSQL_db
# Created: 2026/1/3 上午 11:29

# job_db_mssql.py
# MSSQL 版本：寫入每日快照 + 昨天/今天新增消失
# 依賴：pyodbc
# job_MSSQL_db.py
# MSSQL 版本：寫入每日快照 + 昨天/今天新增消失
# 依賴：pyodbc

import datetime
from typing import Dict, List, Tuple, Optional

import pyodbc

TABLE_FULLNAME = "dbo.job_snapshot"


def connect(conn_str: str) -> pyodbc.Connection:
    return pyodbc.connect(conn_str, autocommit=False)


def init_db(conn_str: str) -> None:
    conn = connect(conn_str)
    try:
        cur = conn.cursor()
        cur.execute(f"""
        SET NOCOUNT ON;

        IF OBJECT_ID('{TABLE_FULLNAME}', 'U') IS NULL
        BEGIN
            CREATE TABLE {TABLE_FULLNAME} (
                id BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                snapshot_date DATE NOT NULL,
                snapshot_time DATETIME2(0) NOT NULL,
                keyword NVARCHAR(200) NOT NULL,
                areas NVARCHAR(200) NOT NULL,
                job_id NVARCHAR(50) NOT NULL,
                title NVARCHAR(500) NULL,
                company NVARCHAR(500) NULL,
                location NVARCHAR(500) NULL,
                salary_text NVARCHAR(500) NULL,
                post_date NVARCHAR(50) NULL,
                url NVARCHAR(1000) NULL
            );

            CREATE UNIQUE INDEX UX_job_snapshot
            ON {TABLE_FULLNAME}(snapshot_date, keyword, areas, job_id);

            CREATE INDEX IX_job_snapshot_date
            ON {TABLE_FULLNAME}(snapshot_date);

            CREATE INDEX IX_job_snapshot_jobid
            ON {TABLE_FULLNAME}(job_id);

            CREATE INDEX IX_job_snapshot_kw_area
            ON {TABLE_FULLNAME}(keyword, areas);
        END
        """)
        conn.commit()
    finally:
        conn.close()


def _parse_snapshot_time(snapshot_time: Optional[str]) -> datetime.datetime:
    if snapshot_time:
        return datetime.datetime.strptime(snapshot_time, "%Y-%m-%d %H:%M")
    return datetime.datetime.now().replace(second=0, microsecond=0)


def _fetch_first_scalar(cur: pyodbc.Cursor) -> int:
    """
    對付 pyodbc 多 statement batch：
    一直 nextset() 到遇到真正有結果集（cur.description != None）再 fetchone()
    """
    while cur.description is None:
        has_next = cur.nextset()
        if not has_next:
            return 0
    row = cur.fetchone()
    if not row:
        return 0
    return int(row[0])


def insert_snapshot_rows(
    rows: List[Dict[str, str]],
    keyword: str,
    areas: str,
    conn_str: str,
    snapshot_time: Optional[str] = None
) -> int:
    init_db(conn_str)

    st = _parse_snapshot_time(snapshot_time)
    sd = st.date()

    payload = []
    for r in rows:
        job_id = (r.get("job_id") or "").strip()
        if not job_id:
            continue
        payload.append((
            sd,
            st,
            keyword,
            areas,
            job_id,
            (r.get("title") or "").strip(),
            (r.get("company") or "").strip(),
            (r.get("location") or "").strip(),
            (r.get("salary_text") or "").strip(),
            (r.get("post_date") or "").strip(),
            (r.get("url") or "").strip(),
        ))

    if not payload:
        return 0

    conn = connect(conn_str)
    try:
        cur = conn.cursor()

        cur.execute("""
        SET NOCOUNT ON;

        IF OBJECT_ID('tempdb..#job_stage') IS NOT NULL DROP TABLE #job_stage;

        CREATE TABLE #job_stage (
            snapshot_date DATE NOT NULL,
            snapshot_time DATETIME2(0) NOT NULL,
            keyword NVARCHAR(200) NOT NULL,
            areas NVARCHAR(200) NOT NULL,
            job_id NVARCHAR(50) NOT NULL,
            title NVARCHAR(500) NULL,
            company NVARCHAR(500) NULL,
            location NVARCHAR(500) NULL,
            salary_text NVARCHAR(500) NULL,
            post_date NVARCHAR(50) NULL,
            url NVARCHAR(1000) NULL
        );
        """)

        cur.fast_executemany = True
        cur.executemany("""
            INSERT INTO #job_stage
            (snapshot_date, snapshot_time, keyword, areas, job_id, title, company, location, salary_text, post_date, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, payload)

        # ⚠️ 這裡是重點：NOCOUNT ON + 最後有 SELECT inserted_count
        cur.execute(f"""
        SET NOCOUNT ON;

        DECLARE @Inserted TABLE (job_id NVARCHAR(50));

        MERGE {TABLE_FULLNAME} WITH (HOLDLOCK) AS T
        USING #job_stage AS S
        ON  T.snapshot_date = S.snapshot_date
        AND T.keyword = S.keyword
        AND T.areas = S.areas
        AND T.job_id = S.job_id
        WHEN NOT MATCHED THEN
            INSERT (snapshot_date, snapshot_time, keyword, areas, job_id, title, company, location, salary_text, post_date, url)
            VALUES (S.snapshot_date, S.snapshot_time, S.keyword, S.areas, S.job_id, S.title, S.company, S.location, S.salary_text, S.post_date, S.url)
        OUTPUT inserted.job_id INTO @Inserted(job_id);

        SELECT COUNT(1) AS inserted_count FROM @Inserted;
        """)

        inserted_count = _fetch_first_scalar(cur)

        conn.commit()
        return inserted_count

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _get_job_ids_for_day(conn_str: str, keyword: str, areas: str, snapshot_date: str) -> List[str]:
    init_db(conn_str)
    conn = connect(conn_str)
    try:
        cur = conn.cursor()
        cur.execute(f"""
            SET NOCOUNT ON;
            SELECT DISTINCT job_id
            FROM {TABLE_FULLNAME}
            WHERE snapshot_date = ? AND keyword = ? AND areas = ?;
        """, (snapshot_date, keyword, areas))
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def diff_today_yesterday(
    keyword: str,
    areas: str,
    conn_str: str,
    today: Optional[str] = None
) -> Tuple[List[str], List[str], str, str]:
    if today is None:
        today_date = datetime.date.today().strftime("%Y-%m-%d")
    else:
        today_date = today

    y_date = (datetime.datetime.strptime(today_date, "%Y-%m-%d").date()
              - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    today_ids = set(_get_job_ids_for_day(conn_str, keyword, areas, today_date))
    y_ids = set(_get_job_ids_for_day(conn_str, keyword, areas, y_date))

    new_ids = sorted(list(today_ids - y_ids))
    removed_ids = sorted(list(y_ids - today_ids))
    return new_ids, removed_ids, today_date, y_date


def fetch_jobs_by_ids(job_ids: List[str], conn_str: str) -> List[Dict[str, str]]:
    if not job_ids:
        return []

    init_db(conn_str)
    conn = connect(conn_str)
    try:
        cur = conn.cursor()
        out: List[Dict[str, str]] = []

        for jid in job_ids:
            cur.execute(f"""
                SET NOCOUNT ON;
                SELECT TOP 1
                    job_id, title, company, location, salary_text, post_date, url,
                    CONVERT(VARCHAR(16), snapshot_time, 120) AS snapshot_time
                FROM {TABLE_FULLNAME}
                WHERE job_id = ?
                ORDER BY snapshot_time DESC;
            """, (jid,))
            row = cur.fetchone()
            if not row:
                continue
            out.append({
                "job_id": row[0] or "",
                "title": row[1] or "",
                "company": row[2] or "",
                "location": row[3] or "",
                "salary_text": row[4] or "",
                "post_date": row[5] or "",
                "url": row[6] or "",
                "snapshot_time": row[7] or "",
            })
        return out
    finally:
        conn.close()

