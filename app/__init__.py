from apscheduler.schedulers.background import BackgroundScheduler
import requests


scheduler = BackgroundScheduler()

def regular_update():
    # r = requests.post("http://127.0.0.1:8000/repeat")
    r = requests.put("http://127.0.0.1:8000/index/dj30")

scheduler.add_job(regular_update, "cron", day=2)
scheduler.start()