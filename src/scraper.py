import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from telethon import TelegramClient, errors
from telethon.tl.types import MessageMediaPhoto
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')
CHANNELS = os.getenv('CHANNELS', 'CheMed,Lobelia4cosmetics,TikvahPharma').split(',')

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data' / 'raw'
MESSAGES_DIR = DATA_DIR / 'telegram_messages'
IMAGES_DIR = DATA_DIR / 'images'
LOGS_DIR = BASE_DIR / 'logs'

# Create directories
MESSAGES_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
log_file = LOGS_DIR / f'scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TelegramScraper:
    def __init__(self, api_id: int, api_hash: str, phone_number: str):
        self.client = TelegramClient('session_name', api_id, api_hash)
        self.phone_number = phone_number

    async def scrape_channel(self, channel_name: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Scrape messages from a single Telegram channel."""
        logger.info(f"Starting to scrape channel: {channel_name}")
        messages_data = []
        
        try:
            await self.client.start(self.phone_number)
            entity = await self.client.get_entity(channel_name)
            
            # Create channel-specific image directory
            channel_image_dir = IMAGES_DIR / channel_name
            channel_image_dir.mkdir(parents=True, exist_ok=True)
            
            async for message in self.client.iter_messages(entity, limit=limit):
                try:
                    message_data = {
                        'message_id': message.id,
                        'channel_name': channel_name,
                        'message_date': message.date.isoformat() if message.date else None,
                        'message_text': message.text or '',
                        'has_media': message.media is not None,
                        'image_path': None,
                        'views': message.views if hasattr(message, 'views') else 0,
                        'forwards': message.forwards if hasattr(message, 'forwards') else 0
                    }
                    
                    # Download image if present
                    if message.media and isinstance(message.media, MessageMediaPhoto):
                        image_path = channel_image_dir / f"{message.id}.jpg"
                        try:
                            await self.client.download_media(message, str(image_path))
                            message_data['image_path'] = str(image_path)
                            logger.info(f"Downloaded image for message {message.id}")
                        except Exception as e:
                            logger.error(f"Failed to download image for message {message.id}: {e}")
                    
                    messages_data.append(message_data)
                    
                except Exception as e:
                    logger.error(f"Error processing message {message.id}: {e}")
                    continue
            
            logger.info(f"Scraped {len(messages_data)} messages from {channel_name}")
            return messages_data
            
        except errors.ChannelPrivateError:
            logger.error(f"Channel {channel_name} is private or not accessible")
            return []
        except errors.ChannelInvalidError:
            logger.error(f"Channel {channel_name} is invalid")
            return []
        except Exception as e:
            logger.error(f"Error scraping channel {channel_name}: {e}")
            return []

    def save_messages_to_json(self, messages: List[Dict[str, Any]], channel_name: str) -> None:
        """Save messages to JSON file in partitioned directory structure."""
        if not messages:
            logger.warning(f"No messages to save for channel {channel_name}")
            return
        
        # Get date from first message for partitioning
        first_message_date = datetime.fromisoformat(messages[0]['message_date'])
        date_partition = first_message_date.strftime('%Y-%m-%d')
        
        # Create date-specific directory
        date_dir = MESSAGES_DIR / date_partition
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to JSON file
        output_file = date_dir / f"{channel_name}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(messages)} messages to {output_file}")

    async def scrape_all_channels(self, channels: List[str], limit: int = 1000) -> None:
        """Scrape all configured channels."""
        logger.info(f"Starting to scrape {len(channels)} channels")
        
        await self.client.start(self.phone_number)
        
        for channel in channels:
            try:
                messages = await self.scrape_channel(channel, limit)
                if messages:
                    self.save_messages_to_json(messages, channel)
            except Exception as e:
                logger.error(f"Failed to scrape channel {channel}: {e}")
                continue
        
        logger.info("Scraping completed for all channels")


async def main():
    """Main function to run the scraper."""
    logger.info("=" * 50)
    logger.info("Telegram Scraper Started")
    logger.info("=" * 50)
    
    # Validate environment variables
    if not API_ID or not API_HASH or not PHONE_NUMBER:
        logger.error("Missing required environment variables. Please check .env file")
        return
    
    scraper = TelegramScraper(API_ID, API_HASH, PHONE_NUMBER)
    
    try:
        await scraper.scrape_all_channels(CHANNELS)
    except Exception as e:
        logger.error(f"Fatal error during scraping: {e}")
    finally:
        await scraper.client.disconnect()
    
    logger.info("=" * 50)
    logger.info("Telegram Scraper Finished")
    logger.info("=" * 50)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
