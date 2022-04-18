from celery import Celery
from celery.schedules import crontab
import datetime
import requests
import json

import worker.celery_settings

app = Celery("tasks", broker=f"redis://:{worker.celery_settings.redis_password}@{worker.celery_settings.redis_host}:{worker.celery_settings.redis_port}")


@app.on_after_configure.connect
def setup_period_tasks(sender, **kwargs):
    sender.add_period_task(
        crontab(day_of_month=5),
        dj30_update.s(),
    )

@app.task
def dj30_update():
    payload = {
        "username": "test_admin",
        "email": "admin@domain.com",
        "password": "testPass",
        "role": "admin"
    }
    r_1 = requests.post("http://127.0.0.1:8000/user/login", data=json.dumps(payload))
    r_1_body = r_1.json()
    TOKEN = r_1_body["access_token"]
    
    r = requests.put("http://127.0.0.1:8000/index/update/dj30", headers={"Authorization": TOKEN})



@app.task
def etf_update():
    payload = {
        "username": "test_admin",
        "email": "admin@domain.com",
        "password": "testPass",
        "role": "admin"
    }
    r_1 = requests.post("http://127.0.0.1:8000/user/login", data=json.dumps(payload))
    r_1_body = r_1.json()
    TOKEN = r_1_body["access_token"]

    r = requests.post("http://127.0.0.1:8000/etf/update", headers={"Authorization": TOKEN})
    print(r.text)

    # with open("log.txt", "w") as f:
    #     f.write(f"test log: {x.second}")
    #     print("Check")