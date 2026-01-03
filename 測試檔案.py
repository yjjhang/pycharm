# 張詠鈞的python工作區
# File: 測試檔案
# Created: 2026/1/3 上午 11:48

import pyodbc

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=lpc:localhost;"
    "DATABASE=job_seek;"
    "UID=cim;"
    "PWD=1234;"
    "TrustServerCertificate=yes;"
)

conn = pyodbc.connect(CONN_STR, autocommit=True)
cur = conn.cursor()
cur.execute("SELECT @@SERVERNAME, DB_NAME();")
print(cur.fetchone())
conn.close()
print("OK")