from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from scraper import scrape_all
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCHEDULER] %(message)s",
    datefmt="%H:%M:%S"
)

TRACKED_PRODUCTS = [
    "samsung galaxy s24",
    "iphone 15",
    "boat earphones",
    "nike shoes",
    "apple watch"
]


def refresh_prices():
    logging.info("Starting price refresh...")
    for product in TRACKED_PRODUCTS:
        logging.info(f"Refreshing: {product}")
        try:
            results = scrape_all(product)
            logging.info(f"  ✅ {len(results)} results saved for '{product}'")
        except Exception as e:
            logging.error(f"  ❌ Failed: {e}")
        time.sleep(5)
    logging.info("Refresh complete!")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=refresh_prices,
        trigger=IntervalTrigger(hours=3),
        id="price_refresh",
        replace_existing=True
    )
    scheduler.start()
    logging.info("Scheduler running — refreshes every 3 hours")
    return scheduler


if __name__ == "__main__":
    print("Testing scheduler now...")
    refresh_prices()
    print("\nStarting loop (Ctrl+C to stop)...")
    s = start_scheduler()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        s.shutdown()
        print("Stopped.")