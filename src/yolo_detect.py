import os
import logging
from pathlib import Path
from datetime import datetime
import csv
from ultralytics import YOLO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_DIR = Path(__file__).parent.parent
IMAGES_DIR = BASE_DIR / 'data' / 'raw' / 'images'
OUTPUT_DIR = BASE_DIR / 'data' / 'processed' / 'yolo_results'
LOGS_DIR = BASE_DIR / 'logs'

# Setup logging
log_file = LOGS_DIR / f'yolo_detection_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_yolo_model():
    """Load YOLOv8 model for object detection."""
    try:
        # Use the smallest model for faster inference
        model = YOLO('yolov8n.pt')
        logger.info("YOLOv8 nano model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Failed to load YOLO model: {e}")
        # Try to download if not available
        try:
            logger.info("Attempting to download YOLOv8n model...")
            model = YOLO('yolov8n.pt')
            logger.info("YOLOv8 nano model downloaded and loaded successfully")
            return model
        except Exception as download_error:
            logger.error(f"Failed to download YOLO model: {download_error}")
            raise


def process_image(model, image_path, channel_name, message_id):
    """Process a single image with YOLO object detection."""
    try:
        # Run inference
        results = model(image_path, conf=0.5, verbose=False)
        
        # Extract detected objects
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    class_id = int(box.cls[0])
                    class_name = model.names[class_id]
                    confidence = float(box.conf[0])
                    
                    detections.append({
                        'class_name': class_name,
                        'confidence': confidence
                    })
        
        return detections
    except Exception as e:
        logger.warning(f"Error processing image {image_path}: {e}")
        return []


def process_channel_images(model, channel_dir):
    """Process all images for a specific channel."""
    channel_name = channel_dir.name
    image_files = list(channel_dir.glob('*.jpg')) + list(channel_dir.glob('*.png'))
    
    if not image_files:
        logger.info(f"No images found for channel {channel_name}")
        return []
    
    logger.info(f"Processing {len(image_files)} images for channel {channel_name}")
    
    results = []
    processed_count = 0
    error_count = 0
    
    for image_file in image_files:
        try:
            # Extract message_id from filename (format: {message_id}.jpg)
            message_id = image_file.stem
            
            # Run object detection
            detections = process_image(model, image_file, channel_name, message_id)
            
            if detections:
                for det in detections:
                    results.append({
                        'channel_name': channel_name,
                        'message_id': message_id,
                        'image_path': str(image_file),
                        'detected_object': det['class_name'],
                        'confidence': det['confidence'],
                        'detected_at': datetime.now().isoformat()
                    })
            
            processed_count += 1
            
            # Log progress every 10 images
            if processed_count % 10 == 0:
                logger.info(f"Processed {processed_count}/{len(image_files)} images for {channel_name}")
                
        except Exception as e:
            logger.error(f"Error processing {image_file}: {e}")
            error_count += 1
            continue
    
    logger.info(f"Channel {channel_name} complete: {processed_count} processed, {error_count} errors")
    return results


def save_results(results, output_file):
    """Save detection results to CSV file."""
    try:
        os.makedirs(output_file.parent, exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if results:
                fieldnames = results[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
        
        logger.info(f"Results saved to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        raise


def main():
    """Main function to run YOLO object detection on all images."""
    logger.info("=" * 50)
    logger.info("Starting YOLO object detection")
    logger.info("=" * 50)
    
    try:
        # Check if images directory exists
        if not IMAGES_DIR.exists():
            logger.warning(f"Images directory does not exist: {IMAGES_DIR}")
            return
        
        # Load YOLO model
        model = load_yolo_model()
        
        # Process all channels
        all_results = []
        channel_dirs = [d for d in IMAGES_DIR.iterdir() if d.is_dir()]
        
        logger.info(f"Found {len(channel_dirs)} channels to process")
        
        for channel_dir in channel_dirs:
            channel_results = process_channel_images(model, channel_dir)
            all_results.extend(channel_results)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f'yolo_detections_{timestamp}.csv'
        save_results(all_results, output_file)
        
        # Summary
        logger.info("=" * 50)
        logger.info("YOLO detection completed")
        logger.info(f"Total detections: {len(all_results)}")
        logger.info(f"Results saved to: {output_file}")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"Fatal error during YOLO detection: {e}")
        raise


if __name__ == '__main__':
    main()
