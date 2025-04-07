import logging
import os
from datetime import datetime

from dotenv import load_dotenv

from database import Database

load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda function to check the status of record signing process

    This function:
    1. Checks how many records remain unsigned
    2. Returns the count to the Step Function

    Returns:
        dict: Status information including records_remaining
    """
    logger.info(f"Checking remaining records with event: {event}")

    batch_size = event.get("batch_size", int(os.environ.get("BATCH_SIZE", 10000)))
    concurrency = event.get("concurrency", int(os.environ.get("CONCURRENCY", 10)))
    start_time = event.get("start_time", datetime.now().isoformat())

    db = Database()

    try:
        remaining = db.count_remaining_records()
        logger.info(f"Found {remaining} unsigned records remaining")

        return {
            "status": "in_progress" if remaining > 0 else "completed",
            "records_remaining": remaining,
            "batch_size": batch_size,
            "concurrency": concurrency,
            "start_time": start_time,
        }
    except Exception as e:
        logger.error(f"Error checking remaining records: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()
