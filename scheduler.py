import logging
import schedule
import time

logger = logging.getLogger(__name__)


def start(job_fn, run_time: str = "20:00") -> None:
    schedule.every().thursday.at(run_time).do(job_fn)
    logger.info("Scheduler started — report will run every Thursday at %s Israel time.", run_time)

    while True:
        schedule.run_pending()
        time.sleep(30)
