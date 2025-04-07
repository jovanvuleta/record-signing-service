import logging
import os
from datetime import datetime

from dotenv import load_dotenv

from database import Database
from key_management import KeyManagementService

load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Initialize the record signing process

    Expected event structure:
    {
        "batch_size": 100,  # Number of records per batch
        "concurrency": 10,  # Number of concurrent batches
        "total_records": 100000,  # Total records to initialize (only for testing)
        "initialize_db": false,  # Whether to initialize the database with test data
        "initialize_keys": false  # Whether to initialize the key store with test keys
    }
    """
    logger.info(f"Initializing record signing process with event: {event}")

    batch_size = event.get("batch_size", int(os.environ.get("BATCH_SIZE", 100)))
    concurrency = event.get("concurrency", int(os.environ.get("CONCURRENCY", 10)))
    total_records = event.get("total_records", 100000)
    initialize_db = event.get("initialize_db", True)
    initialize_keys = event.get("initialize_keys", True)

    db = Database()
    key_service = KeyManagementService(db)

    # For testing: Initialize database with random records
    if initialize_db:
        logger.info(f"Initializing database with {total_records} records")
        db.initialize_records(total_records)

    # For testing: Initialize key store with test keys
    if initialize_keys:
        logger.info("Initializing key store with test keys")
        key_service.generate_test_keys(100)  # Generate 100 test keys

    record_count = db.count_remaining_records()
    logger.info(f"Found {record_count} unsigned records")

    return {
        "status": "initialized",
        "batch_size": batch_size,
        "concurrency": concurrency,
        "records_remaining": record_count,
        "start_time": datetime.now().isoformat(),
    }
