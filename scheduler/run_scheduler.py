#!/usr/bin/env python3

import datetime
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from crawler import BookScraper, setup_logging, run_crawl_job


if __name__ == "__main__":
    # 1. Set up logging
    setup_logging()

    # 2. Set up base url constant
    BASE_URL = "https://books.toscrape.com/"

    # 3. Setting up the Scheduler
    scheduler = BlockingScheduler()

    # run scheduler every day at 3:00 AM
    scheduler.add_job(run_crawl_job, "cron", hour=3, minute=0)

    # Run it once currently
    scheduler.add_job(
        run_crawl_job,
        "date",
        run_date=datetime.datetime.now() + datetime.timedelta(seconds=2),
    )

    logging.info("--- Scheduler starting... ---")
    logging.info("--- A job is scheduled to run now, and then daily at 3:00 AM. ---")
    logging.info("--- Press Ctrl+C to stop the scheduler. ---")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("--- Scheduler stopped manually. ---")
