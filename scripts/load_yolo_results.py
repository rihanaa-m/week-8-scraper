import os
import csv
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
YOLO_RESULTS_DIR = BASE_DIR / 'data' / 'processed' / 'yolo_results'
LOGS_DIR = BASE_DIR / 'logs'

# Setup logging
log_file = LOGS_DIR / f'load_yolo_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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


def create_yolo_tables(conn):
    """Create tables for YOLO detection results."""
    try:
        with conn.cursor() as cur:
            # Create dim_objects dimension table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.dim_objects (
                    object_key SERIAL PRIMARY KEY,
                    object_name VARCHAR(100) UNIQUE NOT NULL,
                    object_category VARCHAR(50),
                    first_detected TIMESTAMP,
                    last_detected TIMESTAMP,
                    detection_count INTEGER DEFAULT 0
                );
            """)
            
            # Create bridge table for message-object relationships
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.fct_message_objects (
                    message_id INTEGER,
                    channel_name VARCHAR(255),
                    object_key INTEGER,
                    confidence FLOAT,
                    detected_at TIMESTAMP,
                    PRIMARY KEY (message_id, channel_name, object_key),
                    FOREIGN KEY (object_key) REFERENCES public.dim_objects(object_key)
                );
            """)
            
            conn.commit()
            logger.info("Created YOLO result tables")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        conn.rollback()
        raise


def load_yolo_csv(conn, csv_file):
    """Load YOLO detection results from CSV file."""
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            detections = list(reader)
        
        logger.info(f"Loading {len(detections)} detections from {csv_file.name}")
        
        # First, update dim_objects
        with conn.cursor() as cur:
            for det in detections:
                object_name = det['detected_object']
                
                # Insert or update object dimension
                cur.execute("""
                    INSERT INTO public.dim_objects (object_name, first_detected, last_detected, detection_count)
                    VALUES (%s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                    ON CONFLICT (object_name) 
                    DO UPDATE SET 
                        last_detected = CURRENT_TIMESTAMP,
                        detection_count = dim_objects.detection_count + 1
                """, (object_name,))
        
        # Then, load bridge table
        with conn.cursor() as cur:
            for det in detections:
                object_name = det['detected_object']
                message_id = int(det['message_id'])
                channel_name = det['channel_name']
                confidence = float(det['confidence'])
                detected_at = datetime.fromisoformat(det['detected_at'])
                
                # Get object_key
                cur.execute("""
                    SELECT object_key FROM public.dim_objects WHERE object_name = %s
                """, (object_name,))
                result = cur.fetchone()
                
                if result:
                    object_key = result[0]
                    
                    # Insert into bridge table
                    cur.execute("""
                        INSERT INTO public.fct_message_objects 
                        (message_id, channel_name, object_key, confidence, detected_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (message_id, channel_name, object_key) DO NOTHING
                    """, (message_id, channel_name, object_key, confidence, detected_at))
        
        conn.commit()
        logger.info(f"Successfully loaded detections from {csv_file.name}")
        
    except Exception as e:
        logger.error(f"Error loading {csv_file}: {e}")
        conn.rollback()
        raise


def main():
    """Main function to load YOLO results into database."""
    logger.info("=" * 50)
    logger.info("Starting YOLO results load")
    logger.info("=" * 50)
    
    try:
        conn = create_database_connection()
        create_yolo_tables(conn)
        
        # Find the most recent YOLO results CSV
        if not YOLO_RESULTS_DIR.exists():
            logger.warning(f"YOLO results directory does not exist: {YOLO_RESULTS_DIR}")
            return
        
        csv_files = list(YOLO_RESULTS_DIR.glob('yolo_detections_*.csv'))
        
        if not csv_files:
            logger.warning("No YOLO results CSV files found")
            return
        
        # Load the most recent file
        latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"Loading most recent file: {latest_file.name}")
        
        load_yolo_csv(conn, latest_file)
        
        logger.info("=" * 50)
        logger.info("YOLO results load completed successfully")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"Fatal error during YOLO results load: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
            logger.info("Database connection closed")


if __name__ == '__main__':
    main()
