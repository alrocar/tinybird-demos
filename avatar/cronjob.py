from apscheduler.schedulers.blocking import BlockingScheduler
from avatar import run

scheduler = BlockingScheduler()
scheduler.add_job(run, "interval", seconds=300)

scheduler.start()
