import json
import os

import boto3
import pg8000
from dotenv import load_dotenv

load_dotenv()


class Database:
    """Database access layer for the record signing service"""

    def __init__(self):
        self.conn = None

        # Get secret name from environment variable
        secret_name = os.environ.get("DB_SECRET_NAME")

        if not secret_name:
            raise ValueError("Missing DB_SECRET_NAME environment variable")

        # Initialize Secrets Manager client
        session = boto3.session.Session()
        client = session.client("secretsmanager")

        try:
            get_secret_value_response = client.get_secret_value(SecretId=secret_name)
            secret = json.loads(get_secret_value_response["SecretString"])

            # Set connection parameters from the secret
            self.host = secret.get("host")
            self.dbname = secret.get("dbname")
            self.user = secret.get("username")
            self.password = secret.get("password")

            if not all([self.host, self.dbname, self.user, self.password]):
                raise ValueError("Database secret is missing required fields")

        except Exception as e:
            raise RuntimeError(f"Error retrieving database secret: {e}")

    def connect(self):
        """Establish a connection to the database"""
        if self.conn is None:
            import ssl

            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            try:
                self.conn = pg8000.connect(
                    host=self.host,
                    database=self.dbname,
                    user=self.user,
                    password=self.password,
                    ssl_context=ssl_context,
                )
                self.conn.autocommit = False
            except Exception as e:
                raise RuntimeError(f"Failed to connect to database: {e}")

        return self.conn

    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def get_unsigned_batch(self, batch_size):
        """Get a batch of unsigned records"""
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, data
                FROM records
                WHERE signature IS NULL
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            """,
                (batch_size,),
            )

            records = cursor.fetchall()
            conn.commit()
            return records
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

    def update_signatures(self, signature_data):
        """Update signatures for a batch of records

        Args:
            signature_data: List of tuples (signature, signed_at, signed_by, record_id)
        """
        conn = self.connect()
        cursor = conn.cursor()

        try:
            for record in signature_data:
                cursor.execute(
                    """
                    UPDATE records
                    SET signature = %s, signed_at = %s, signed_by = %s
                    WHERE id = %s
                """,
                    record,
                )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

    def count_remaining_records(self):
        """Count unsigned records"""
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM records WHERE signature IS NULL")
            count = cursor.fetchone()[0]
            return count
        finally:
            cursor.close()

    def initialize_records(self, num_records):
        """Initialize the database with random records for testing"""
        import random
        import string

        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    id SERIAL PRIMARY KEY,
                    data TEXT NOT NULL,
                    signature TEXT,
                    signed_at TIMESTAMP,
                    signed_by TEXT
                )
            """
            )

            # Generate random data for records
            # Break it into batches for better performance
            batch_size = 1000
            for i in range(0, num_records, batch_size):
                batch_count = min(batch_size, num_records - i)
                batch_data = []

                for _ in range(batch_count):
                    random_data = "".join(random.choices(string.ascii_letters + string.digits, k=50))
                    batch_data.append((random_data,))

                cursor.executemany("INSERT INTO records (data) VALUES (%s)", batch_data)

            conn.commit()
            return num_records
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
