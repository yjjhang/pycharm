# 張詠鈞的python工作區
# File: main
# Created: 2026/1/31 下午 02:01

# job_seeker_app/__main__.py
# 入口：python -m job_seeker_app  -> 預設啟動 UI

def main():
    # 這裡只負責「啟動 UI」，不做其他事情
    from .job_seeker_UI import main as ui_main
    ui_main()


if __name__ == "__main__":
    main()
