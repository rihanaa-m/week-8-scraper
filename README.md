# Medical Telegram Data Warehouse

This project builds a data warehouse for Ethiopian medical and pharmaceutical products by scraping Telegram channels, transforming the data with dbt, enriching it with YOLO object detection, and exposing it via a FastAPI API.

## Project Structure

```
medical-telegram-warehouse/
├── .env                    # API credentials (DO NOT COMMIT)
├── .gitignore
├── requirements.txt
├── README.md
├── data/
│   └── raw/
│       ├── telegram_messages/  # JSON files by date
│       └── images/              # Downloaded images by channel
├── logs/                     # Scraping logs
├── src/
│   └── scraper.py           # Telegram scraper
├── medical_warehouse/       # dbt project
├── api/                     # FastAPI application
├── notebooks/               # Analysis notebooks
└── tests/                   # Unit tests
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your Telegram API credentials
```

3. Run the scraper:
```bash
python src/scraper.py
```

## Tasks

- **Task 1**: Data Scraping and Collection (Extract & Load)
- **Task 2**: Data Modeling and Transformation with dbt
- **Task 3**: Data Enrichment with YOLO Object Detection
- **Task 4**: Analytical API with FastAPI
- **Task 5**: Pipeline Orchestration with Dagster
