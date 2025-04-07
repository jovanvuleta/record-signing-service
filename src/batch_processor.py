import os
import json
import time
import boto3
import logging
from datetime import datetime

from database import Database
from key_management import KeyManagementService
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")


def lambda_handler(event, context):
    """
    Lambda function to process a batch of records for signing

    Expected event structure:
    {
        "batch_id": "unique_batch_identifier",
        "execution_arn": "step_function_execution_arn",
        "batch_size": 100,  # Optional, can use environment variable
        "start_time": "iso_timestamp"  # Optional, for process timing
    }
    """
    batch_start_time = time.time()
    logger.info(f"Starting batch processor with event: {event}")

    batch_id = event.get("batch_id")
    process_start_time = event.get("start_time")  # Preserve for overall process timing

    if not batch_id:
        if "Records" in event and len(event["Records"]) > 0:
            message = json.loads(event["Records"][0]["body"])
            batch_id = message.get("batch_id")
            process_start_time = message.get("start_time")

    if not batch_id:
        raise ValueError("No batch_id provided in event or SQS message")

    db = Database()
    key_service = KeyManagementService(db)

    try:
        batch_size = event.get("batch_size", int(os.environ.get("BATCH_SIZE", "100")))

        logger.info(f"Fetching batch of {batch_size} unsigned records")
        records = db.get_unsigned_batch(batch_size)

        if not records:
            logger.info("No unsigned records found to process")
            db.close()
            return {
                "status": "completed",
                "records_processed": 0,
                "start_time": process_start_time,
            }

        logger.info("Requesting signing key")
        key_id = key_service.get_available_key()
        logger.info(f"Using key: {key_id}")

        try:
            signature_data = []
            signed_time = datetime.now()

            for record_id, data in records:
                signature = key_service.sign_data(key_id, data)

                signature_data.append((signature, signed_time, key_id, record_id))

            logger.info(f"Updating {len(signature_data)} signatures in database")
            db.update_signatures(signature_data)

            records_processed = len(signature_data)

        finally:
            # Release the key only if it was acquired
            if key_id:
                logger.info(f"Releasing key: {key_id}")
                key_service.release_key(key_id)

        remaining = db.count_remaining_records()
        logger.info(f"Signed {records_processed} records. {remaining} records remaining.")

        elapsed_time = time.time() - batch_start_time
        logger.info(f"Batch processing completed in {elapsed_time:.2f} seconds")

        result = {
            "status": "in_progress" if remaining > 0 else "completed",
            "batch_id": batch_id,
            "records_processed": records_processed,
            "records_remaining": remaining,
        }

        if process_start_time:
            result["start_time"] = process_start_time

        return result

    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()
