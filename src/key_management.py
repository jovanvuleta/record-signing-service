import base64
import os
import time

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


class KeyManagementService:
    """Service to manage the pool of signing keys using AWS KMS"""

    def __init__(self, db_connection):
        self.db = db_connection
        self.kms = boto3.client("kms")
        self.dynamodb = boto3.resource("dynamodb")
        self.key_usage_table = self.dynamodb.Table(os.environ.get("KEY_USAGE_TABLE", "key_usage"))

    def generate_test_keys(self, num_keys=100):
        """Generate test keys in AWS KMS (only for testing)"""
        for i in range(num_keys):
            key_id = f"signing_key_{i}"

            # Create a new KMS key for signing
            response = self.kms.create_key(
                Description=f"Signing key {i} for record signing service",
                KeyUsage="SIGN_VERIFY",
                CustomerMasterKeySpec="RSA_2048",
                Origin="AWS_KMS",
            )

            # Get the key ARN
            key_arn = response["KeyMetadata"]["Arn"]

            # Create an alias for easier identification
            self.kms.create_alias(AliasName=f"alias/{key_id}", TargetKeyId=response["KeyMetadata"]["KeyId"])

            # Initialize key usage tracking
            self.key_usage_table.put_item(
                Item={"key_id": key_arn, "alias": key_id, "last_used": 0, "in_use": False}  # Unix timestamp
            )

    def get_available_key(self):
        """Get the least recently used available key

        Returns:
            str: key_id (ARN of the KMS key)
        """
        # Query DynamoDB for available keys, sorted by last_used
        response = self.key_usage_table.scan(
            FilterExpression="in_use = :false", ExpressionAttributeValues={":false": False}
        )

        available_keys = sorted(response["Items"], key=lambda k: k["last_used"])

        if not available_keys:
            raise Exception("No keys available for signing")

        # Get the least recently used key
        key_id = available_keys[0]["key_id"]

        # Mark the key as in-use
        self.key_usage_table.update_item(
            Key={"key_id": key_id}, UpdateExpression="SET in_use = :true", ExpressionAttributeValues={":true": True}
        )

        return key_id

    def release_key(self, key_id):
        """Mark a key as no longer in use"""
        current_time = int(time.time())

        self.key_usage_table.update_item(
            Key={"key_id": key_id},
            UpdateExpression="SET in_use = :false, last_used = :time",
            ExpressionAttributeValues={":false": False, ":time": current_time},
        )

    def sign_data(self, key_id, data):
        """Sign data with the specified KMS key

        Args:
            key_id: The KMS key ID (ARN)
            data: The data to sign (string)

        Returns:
            str: Base64-encoded signature
        """
        # Convert data to bytes if it's not already
        if isinstance(data, str):
            data = data.encode("utf-8")

        try:
            # Sign the data using KMS
            response = self.kms.sign(
                KeyId=key_id,
                Message=data,
                MessageType="RAW",
                SigningAlgorithm="RSASSA_PKCS1_V1_5_SHA_256",
            )

            # The signature is already in bytes format
            signature = response["Signature"]

            # Return base64 encoded signature
            return base64.b64encode(signature).decode("utf-8")

        except ClientError as e:
            print(f"Error signing data with KMS: {e}")
            raise

    def verify_signature(self, key_id, data, signature):
        """Verify a signature using KMS

        Args:
            key_id: The KMS key ID (ARN)
            data: The data that was signed (string)
            signature: The base64-encoded signature

        Returns:
            bool: True if the signature is valid, False otherwise
        """
        # Convert data to bytes if it's not already
        if isinstance(data, str):
            data = data.encode("utf-8")

        # Decode the signature from base64
        signature_bytes = base64.b64decode(signature)

        try:
            # Verify the signature using KMS
            response = self.kms.verify(
                KeyId=key_id,
                Message=data,
                MessageType="RAW",
                Signature=signature_bytes,
                SigningAlgorithm="RSASSA_PKCS1_V1_5_SHA_256",
            )

            return response["SignatureValid"]

        except ClientError as e:
            print(f"Error verifying signature with KMS: {e}")
            return False
