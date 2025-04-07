import os
import json
import uuid
import boto3
import logging
from datetime import datetime

from database import Database
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")
lambda_client = boto3.client("lambda")


def lambda_handler(event, context):
    """
    Lambda function to submit batches of records to the processing queue

    Expected event structure:
    {
        "execution_arn": "step_function_execution_arn",
        "batch_size": 10000,  # Number of records per batch
        "concurrency": 10,  # Number of concurrent batches to process
        "direct_invoke": false  # Whether to invoke processor directly instead of using SQS
    }
    """
    logger.info(f"Starting batch submitter with event: {event}")

    execution_arn = event.get("execution_arn")
    batch_size = event.get("batch_size", int(os.environ.get("DEFAULT_BATCH_SIZE", 10000)))
    concurrency = event.get("concurrency", int(os.environ.get("DEFAULT_CONCURRENCY", 10)))
    direct_invoke = event.get("direct_invoke", os.environ.get("DIRECT_INVOKE", "false").lower() == "true")
    start_time = event.get("start_time", datetime.now().isoformat())

    queue_url = os.environ.get("BATCH_QUEUE_URL")
    if not queue_url and not direct_invoke:
        logger.error("BATCH_QUEUE_URL environment variable not set")
        return {"status": "error", "message": "Missing required environment variable: BATCH_QUEUE_URL"}

    db = Database()
    try:
        record_count = db.count_remaining_records()
    finally:
        db.close()

    if record_count <= 0:
        logger.info("No records to process")
        return {"status": "completed", "batches_submitted": 0, "records_remaining": 0, "start_time": start_time}

    # Calculate number of batches to submit (limited by concurrency and available records)
    batches_to_submit = min(concurrency, (record_count + batch_size - 1) // batch_size)
    logger.info(f"Planning to submit {batches_to_submit} batches of up to {batch_size} records each")

    batches_submitted = 0

    # Submit batches
    for i in range(batches_to_submit):
        batch_id = str(uuid.uuid4())

        batch_message = {"batch_id": batch_id, "execution_arn": execution_arn, "batch_size": batch_size}

        if direct_invoke:
            processor_function_name = os.environ.get("PROCESSOR_FUNCTION_NAME")
            if not processor_function_name:
                logger.error("PROCESSOR_FUNCTION_NAME environment variable not set")
                continue

            try:
                logger.info(f"Directly invoking processor Lambda for batch {batch_id}")
                lambda_client.invoke(
                    FunctionName=processor_function_name,
                    InvocationType="Event",  # Asynchronous invocation
                    Payload=json.dumps(batch_message),
                )
                batches_submitted += 1
            except Exception as e:
                logger.error(f"Error invoking processor Lambda: {str(e)}")
        else:
            try:
                logger.info(f"Sending batch {batch_id} to SQS queue")
                sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(batch_message))
                batches_submitted += 1
            except Exception as e:
                logger.error(f"Error sending batch to SQS: {str(e)}")

    logger.info(f"Successfully submitted {batches_submitted} batches")

    return {
        "status": "in_progress",
        "batches_submitted": batches_submitted,
        "records_remaining": record_count,
        "start_time": start_time,
    }
