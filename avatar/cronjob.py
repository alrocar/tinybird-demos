from apscheduler.schedulers.blocking import BlockingScheduler
from avatar import run

scheduler = BlockingScheduler()
run()
scheduler.add_job(run, "interval", seconds=60)

scheduler.start()
