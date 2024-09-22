from apscheduler.schedulers.background import BlockingScheduler
from datetime import datetime

scheduler = BlockingScheduler()


def my_func(text):
    print(f"Функция my_func сработала и получила args: {text}")


scheduler.add_job(
    my_func,
    args=['args'],
    trigger='date',
    run_date=datetime(2024, 9, 17, 12, 24, 0),
    id='job_1'
)

scheduler.print_jobs()
scheduler.start()
