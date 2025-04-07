import os
import json
import logging
import boto3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda function to finalize the record signing process

    This function:
    1. Logs completion metrics
    2. Can send notifications (optional)
    3. Returns final summary

    Returns:
        dict: Final status summary
    """
    logger.info(f"Finalizing record signing process with event: {event}")

    start_time = event.get("start_time", datetime.now().isoformat())

    try:
        start_datetime = datetime.fromisoformat(start_time)
        end_datetime = datetime.now()
        duration_seconds = (end_datetime - start_datetime).total_seconds()
        duration_formatted = (
            f"{duration_seconds // 3600}h {(duration_seconds % 3600) // 60}m {duration_seconds % 60:.2f}s"
        )
    except (ValueError, TypeError):
        duration_seconds = None
        duration_formatted = "Unknown"

    summary = {
        "status": "completed",
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": duration_seconds,
        "duration_formatted": duration_formatted,
        "message": "Record signing process completed successfully",
    }

    logger.info(f"Record signing completed in {duration_formatted}")

    sns_topic_arn = os.environ.get("COMPLETION_SNS_TOPIC_ARN")
    if sns_topic_arn:
        try:
            sns = boto3.client("sns")
            sns.publish(
                TopicArn=sns_topic_arn,
                Subject="Record Signing Process Completed",
                Message=json.dumps(summary, indent=2),
            )
            logger.info(f"Completion notification sent to SNS topic: {sns_topic_arn}")
        except Exception as e:
            logger.warning(f"Failed to send SNS notification: {str(e)}")

    return summary
