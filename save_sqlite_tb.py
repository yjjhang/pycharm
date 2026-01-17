# 張詠鈞的python工作區
# File: rateBotWebCrawler6
# Created: 2026/1/17 上午 10:06

import sqlite3

def save_cash_and_spot_buy_to_sqlite(db_path: str, rows):
    """
    rows: list[(currency, cash_buy, spot_buy)]
    cash_buy / spot_buy 可為字串數字或 '-' 或 ''，會轉成 REAL 或 NULL
    """
    def to_float(x):
        if x is None:
            return None
        s = str(x).strip()
        if s in ("", "-", "—"):
            return None
        return float(s.replace(",", ""))

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tb_cash_spot_buy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            currency  TEXT NOT NULL,
            cash_buy  REAL,
            spot_buy  REAL
        )
        """)

        data = [(c, to_float(cb), to_float(sb)) for (c, cb, sb) in rows]

        cur.executemany(
            "INSERT INTO tb_cash_spot_buy (currency, cash_buy, spot_buy) VALUES (?, ?, ?)",
            data
        )
        conn.commit()
