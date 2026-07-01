import os
import json
import logging
from pathlib import Path
from datetime import datetime
import psycopg2
from psycopg2 import sql, extras
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'medical_warehouse')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data' / 'raw'
MESSAGES_DIR = DATA_DIR / 'telegram_messages'
LOGS_DIR = BASE_DIR / 'logs'

# Setup logging
log_file = LOGS_DIR / f'load_raw_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def create_database_connection():
    """Create connection to PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logger.info("Successfully connected to PostgreSQL database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


def create_raw_schema(conn):
    """Create raw schema and telegram_messages table if they don't exist."""
    try:
        with conn.cursor() as cur:
            # Create raw schema
            cur.execute("""
                CREATE SCHEMA IF NOT EXISTS raw;
            """)
            
            # Create telegram_messages table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS raw.telegram_messages (
                    message_id INTEGER,
                    channel_name VARCHAR(255),
                    message_date TIMESTAMP,
                    message_text TEXT,
                    has_media BOOLEAN,
                    image_path VARCHAR(500),
                    views INTEGER DEFAULT 0,
                    forwards INTEGER DEFAULT 0,
                    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (message_id, channel_name, message_date)
                );
            """)
            
            conn.commit()
            logger.info("Created raw schema and telegram_messages table")
    except Exception as e:
        logger.error(f"Failed to create schema/table: {e}")
        conn.rollback()
        raise


def load_json_files(conn):
    """Load all JSON files from the data lake into PostgreSQL."""
    if not MESSAGES_DIR.exists():
        logger.warning(f"Messages directory does not exist: {MESSAGES_DIR}")
        return
    
    json_files = list(MESSAGES_DIR.rglob('*.json'))
    logger.info(f"Found {len(json_files)} JSON files to load")
    
    total_messages = 0
    loaded_count = 0
    error_count = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            if not isinstance(messages, list):
                logger.warning(f"Skipping {json_file}: not a list of messages")
                continue
            
            total_messages += len(messages)
            
            # Prepare data for insertion
            records = []
            for msg in messages:
                try:
                    message_date = msg.get('message_date')
                    if message_date:
                        message_date = datetime.fromisoformat(message_date.replace('Z', '+00:00'))
                    
                    record = (
                        msg.get('message_id'),
                        msg.get('channel_name'),
                        message_date,
                        msg.get('message_text'),
                        msg.get('has_media', False),
                        msg.get('image_path'),
                        msg.get('views', 0),
                        msg.get('forwards', 0)
                    )
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Error processing message in {json_file}: {e}")
                    continue
            
            if records:
                # Insert records using execute_batch for better performance
                with conn.cursor() as cur:
                    query = sql.SQL("""
                        INSERT INTO raw.telegram_messages 
                        (message_id, channel_name, message_date, message_text, has_media, image_path, views, forwards)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (message_id, channel_name, message_date) 
                        DO NOTHING
                    """)
                    
                    extras.execute_batch(cur, query, records, page_size=100)
                    conn.commit()
                    loaded_count += len(records)
                    logger.info(f"Loaded {len(records)} messages from {json_file.name}")
            
        except Exception as e:
            logger.error(f"Error loading {json_file}: {e}")
            error_count += 1
            continue
    
    logger.info(f"Loading complete: {loaded_count}/{total_messages} messages loaded, {error_count} errors")


def main():
    """Main function to load raw data into PostgreSQL."""
    logger.info("=" * 50)
    logger.info("Starting raw data load")
    logger.info("=" * 50)
    
    try:
        conn = create_database_connection()
        create_raw_schema(conn)
        load_json_files(conn)
        
        logger.info("=" * 50)
        logger.info("Raw data load completed successfully")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"Fatal error during data load: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
            logger.info("Database connection closed")


if __name__ == '__main__':
    main()
