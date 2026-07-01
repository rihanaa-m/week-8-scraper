# Building a Medical Data Warehouse: From Telegram Scraping to AI-Powered Analytics

## Introduction

In the rapidly evolving landscape of Ethiopian healthcare and pharmaceutical markets, data-driven insights are becoming increasingly crucial for understanding market dynamics, product availability, and consumer behavior. This project documents the end-to-end development of a comprehensive data warehouse that scrapes medical product information from Telegram channels, transforms it using modern data engineering practices, enriches it with AI-powered object detection, and exposes it through a RESTful API for analytical consumption.

## The Business Problem

Ethiopian medical and pharmaceutical products are heavily promoted through Telegram channels, creating a rich but unstructured data source. Key business challenges include:

- **Market Intelligence Gap**: Limited visibility into product trends, pricing patterns, and demand signals
- **Channel Performance Uncertainty**: Unknown effectiveness of different promotional channels
- **Content Effectiveness Questions**: Unclear what content drives engagement and conversions
- **Temporal Pattern Blindness**: Missing insights into seasonal trends and optimal posting times

## Technical Architecture Overview

The solution implements a modern data engineering stack with the following components:

```
Telegram Channels → Data Lake → PostgreSQL → dbt → YOLO → FastAPI → Dagster
```

### Phase 1: Data Ingestion (Task 1)

**Technology Stack**: Python, Telethon, JSON

The foundation of our data warehouse is a robust Telegram scraper built with Telethon, a Python library for interacting with Telegram's API. The scraper:

- Extracts messages with comprehensive metadata (message_id, channel_name, message_date, message_text, views, forwards)
- Downloads associated images with organized storage by channel and message ID
- Implements graceful error handling for API rate limits and inaccessible channels
- Stores raw data in a partitioned data lake structure organized by date and channel

**Key Design Decisions**:

1. **Partitioned Storage**: Messages are stored in `data/raw/telegram_messages/YYYY-MM-DD/channel_name.json` for efficient time-based queries
2. **Image Organization**: Images stored as `data/raw/images/{channel_name}/{message_id}.jpg` for easy reference
3. **Logging**: Comprehensive logging tracks scraping activity and errors for debugging
4. **Resumability**: The scraper can be run multiple times without duplicating data

### Phase 2: Data Modeling and Transformation (Task 2)

**Technology Stack**: PostgreSQL, dbt, dbt-postgres

The raw data is loaded into PostgreSQL and transformed using dbt (Data Build Tool), implementing a star schema optimized for analytical queries.

#### Star Schema Implementation

**Dimension Tables**:

- **dim_channels**: Stores channel-level metadata and aggregated statistics (total_posts, avg_views, media_percentage)
- **dim_dates**: Comprehensive date dimension with attributes for time-based analysis (day_of_week, is_weekend, quarter, year)

**Fact Table**:

- **fct_messages**: Individual message-level metrics with foreign keys to dimensions (view_count, forward_count, has_image_flag, message_length)

**Business Value of Star Schema**:

The star schema directly enables key business questions:

- **Channel Performance**: Pre-aggregated metrics in dim_channels allow instant comparison without complex joins
- **Temporal Analysis**: dim_dates provides pre-calculated attributes for quick trend analysis
- **Scalable Querying**: Fact table structure supports aggregation by any dimension
- **BI Tool Compatibility**: Star schema structure works with most visualization tools

#### Data Quality Implementation

Comprehensive data quality tests ensure data reliability:

- **Unique and Not Null Tests**: Primary keys and critical fields
- **Relationship Tests**: Foreign key integrity between fact and dimension tables
- **Custom Tests**: 
  - `assert_no_future_messages`: Ensures data integrity
  - `assert_no_empty_messages`: Validates meaningful content
  - `assert_channel_activity`: Monitors channel freshness

### Phase 3: AI-Powered Data Enrichment (Task 3)

**Technology Stack**: YOLOv8, ultralytics, Python

To extract additional insights from image content, we implemented YOLO (You Only Look Once) object detection:

- **Model Selection**: YOLOv8 nano for efficient inference on CPU
- **Detection Process**: Scans downloaded images and identifies objects with confidence scores
- **Integration**: Results loaded into database with bridge table design for many-to-many relationships
- **Schema**: dim_objects (object metadata) + fct_message_objects (message-object relationships)

**Business Impact**:

- **Product Category Classification**: Automatically identify product types from images
- **Content Analysis**: Understand which visual elements drive engagement
- **Enriched Search**: Enable image-based product discovery

### Phase 4: Analytical API Development (Task 4)

**Technology Stack**: FastAPI, SQLAlchemy, Pydantic

A RESTful API exposes the data warehouse for analytical consumption:

**Key Endpoints**:

1. **`/api/channels`**: Channel performance metrics with pagination
2. **`/api/messages`**: Message search with filtering (channel, date range, views, image presence)
3. **`/api/temporal`**: Time-series analysis with daily/weekly/monthly granularity
4. **`/api/objects`**: Detected objects statistics from YOLO analysis
5. **`/api/search`**: Full-text search across message content

**API Features**:

- **Auto-documentation**: OpenAPI/Swagger documentation generated automatically
- **Type Safety**: Pydantic schemas ensure request/response validation
- **Performance**: Connection pooling and query optimization
- **CORS Support**: Cross-origin resource sharing for web integration

### Phase 5: Pipeline Orchestration (Task 5)

**Technology Stack**: Dagster

Dagster orchestrates the end-to-end data pipeline:

**Asset-Based Architecture**:

1. **telegram_scrape_data**: Scrapes Telegram channels
2. **load_raw_data**: Loads JSON into PostgreSQL
3. **dbt_transform**: Runs dbt transformations
4. **yolo_object_detection**: Runs YOLO on images
5. **load_yolo_results**: Loads detection results
6. **data_pipeline_complete**: Final completion indicator

**Benefits**:

- **Dependency Management**: Automatic asset dependency resolution
- **Observability**: Built-in logging and monitoring
- **Scalability**: Asset-based approach supports incremental updates
- **Recovery**: Checkpointing enables failure recovery

## Technical Challenges and Solutions

### Challenge 1: API Rate Limiting

**Problem**: Telegram API has strict rate limits that can cause scraping failures.

**Solution**: 
- Implemented async/await pattern for graceful delay handling
- Added specific error handling for rate limit exceptions
- Structured scraper for resumability with partitioned storage

### Challenge 2: Data Quality Variability

**Problem**: Incomplete message data, missing fields, and inconsistent formats.

**Solution**:
- Default values for missing numeric fields (0 for views/forwards)
- Empty strings for missing text fields
- Boolean flags for media presence
- Staging layer with additional validation and cleaning

### Challenge 3: YOLO Model Performance

**Problem**: Large image datasets and CPU-only inference.

**Solution**:
- Used YOLOv8 nano model for faster inference
- Implemented batch processing with progress logging
- Added confidence threshold (0.5) to filter low-confidence detections

### Challenge 4: Database Schema Evolution

**Problem**: Need to support future enhancements without breaking existing queries.

**Solution**:
- Star schema with clear separation of dimensions and facts
- Surrogate keys for stable references
- Bridge table design for many-to-many relationships
- Comprehensive documentation for schema changes

## Business Insights Enabled

The data warehouse enables answering critical business questions:

### 1. Channel Performance Analysis

**Query**: Which channels have the highest audience engagement?

**Implementation**: Join dim_channels with fct_messages, aggregate by channel, sort by avg_views

**Business Value**: Identify most effective promotional channels for resource allocation

### 2. Temporal Pattern Analysis

**Query**: What are the peak engagement times for medical product promotions?

**Implementation**: Join fct_messages with dim_dates, aggregate by day_of_week and hour

**Business Value**: Optimize posting schedules for maximum reach

### 3. Content Effectiveness

**Query**: How does image content affect message engagement?

**Implementation**: Correlate has_image_flag with view_count and forward_count

**Business Value**: Understand visual content impact on engagement

### 4. Product Category Trends

**Query**: Which product categories are most frequently promoted?

**Implementation**: Analyze dim_objects detection counts over time

**Business Value**: Identify trending product categories for inventory planning

## Performance Considerations

### Database Optimization

- **Indexing**: Primary keys and foreign keys indexed for join performance
- **Partitioning**: Date-based partitioning for efficient time-range queries
- **Connection Pooling**: SQLAlchemy connection pooling for API performance

### API Performance

- **Pagination**: All list endpoints support pagination for large datasets
- **Query Optimization**: Efficient SQL with proper joins and filtering
- **Caching**: Potential for Redis caching of frequently accessed data

### Pipeline Performance

- **Incremental Processing**: Dagster assets support incremental updates
- **Parallel Processing**: YOLO detection can be parallelized across images
- **Batch Loading**: PostgreSQL batch inserts for efficient data loading

## Security Considerations

- **Credential Management**: Environment variables for sensitive data (API keys, database credentials)
- **API Authentication**: JWT authentication ready for production deployment
- **Data Encryption**: SSL/TLS for database connections
- **Access Control**: Role-based access control for database users

## Future Enhancements

### Short-term

1. **Real-time Processing**: Stream processing for near real-time insights
2. **Advanced Analytics**: Machine learning models for demand forecasting
3. **Visualization Dashboard**: Grafana or Tableau integration for business users
4. **Alerting System**: Automated alerts for unusual patterns

### Long-term

1. **Multi-source Integration**: Additional data sources (social media, e-commerce platforms)
2. **Natural Language Processing**: Text analysis for sentiment and product classification
3. **Geospatial Analysis**: Location-based insights if geographic data available
4. **Predictive Analytics**: ML models for predicting product demand and pricing

## Lessons Learned

### Technical Insights

1. **Start Simple**: Begin with basic functionality, then add complexity incrementally
2. **Data Quality First**: Invest in data quality early to avoid downstream issues
3. **Documentation Matters**: Comprehensive documentation saves time in long run
4. **Testing is Critical**: Automated tests prevent regressions and ensure reliability

### Project Management

1. **Iterative Development**: Break large tasks into smaller, manageable phases
2. **Regular Integration**: Commit and push frequently to avoid merge conflicts
3. **Business Alignment**: Keep business objectives in focus throughout development
4. **Flexibility**: Be prepared to adapt to changing requirements

## Conclusion

This project demonstrates the complete data engineering lifecycle from data ingestion to analytical consumption. By leveraging modern tools and best practices, we built a scalable, maintainable data warehouse that directly addresses business needs while providing a foundation for future enhancements.

The integration of traditional data engineering (ETL, data modeling) with modern AI capabilities (object detection) showcases how data teams can deliver enhanced value through technology. The API-first approach ensures that data insights are accessible to stakeholders across the organization.

The project is production-ready with comprehensive error handling, logging, testing, and documentation. The modular architecture allows for easy extension and adaptation to changing business requirements.

## Technical Stack Summary

- **Scraping**: Python, Telethon
- **Storage**: JSON (data lake), PostgreSQL (data warehouse)
- **Transformation**: dbt, dbt-postgres
- **Enrichment**: YOLOv8, ultralytics
- **API**: FastAPI, SQLAlchemy, Pydantic
- **Orchestration**: Dagster
- **Version Control**: Git, GitHub

## Repository Structure

```
week-8-scraper/
├── api/
│   ├── database.py          # Database connection and session management
│   ├── main.py              # FastAPI application and endpoints
│   └── schemas.py           # Pydantic schemas for API validation
├── dagster/
│   ├── __init__.py
│   ├── assets.py            # Dagster asset definitions
│   └── dagster.yaml         # Dagster configuration
├── data/
│   ├── raw/
│   │   ├── telegram_messages/  # Partitioned JSON data
│   │   └── images/            # Downloaded images
│   └── processed/
│       └── yolo_results/      # YOLO detection results
├── logs/                     # Application logs
├── medical_warehouse/
│   ├── dbt_project.yml       # dbt project configuration
│   ├── profiles.yml.example  # Database profile template
│   ├── packages.yml          # dbt package dependencies
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_telegram_messages.sql
│   │   │   └── schema.yml
│   │   └── marts/
│   │       ├── dim_channels.sql
│   │       ├── dim_dates.sql
│   │       ├── fct_messages.sql
│   │       └── schema.yml
│   └── tests/
│       ├── assert_no_future_messages.sql
│       ├── assert_no_empty_messages.sql
│       └── assert_channel_activity.sql
├── scripts/
│   ├── load_raw_data.py      # Load JSON to PostgreSQL
│   └── load_yolo_results.py  # Load YOLO results to PostgreSQL
├── src/
│   ├── scraper.py            # Telegram scraper
│   └── yolo_detect.py        # YOLO object detection
├── .env                      # Environment variables (not committed)
├── .env.example              # Environment variables template
├── .gitignore
├── requirements.txt          # Python dependencies
├── README.md
├── INTERIM_REPORT.md
└── FINAL_REPORT.md           # This document
```

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Telegram API credentials

### Installation

1. Clone the repository:
```bash
git clone https://github.com/rihanaa-m/week-8-scraper.git
cd week-8-scraper
```

2. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. Set up PostgreSQL:
```bash
createdb medical_warehouse
```

6. Run the pipeline:
```bash
# Scrape data
python src/scraper.py

# Load to database
python scripts/load_raw_data.py

# Run dbt transformations
cd medical_warehouse
dbt run

# Run YOLO detection
python src/yolo_detect.py

# Load YOLO results
python scripts/load_yolo_results.py

# Start API
cd ..
uvicorn api.main:app --reload
```

## Acknowledgments

This project was completed as part of the 10 Academy Kaim 9 - Week 8 challenge. The challenge provided an excellent opportunity to apply modern data engineering practices to real-world business problems.

---

**Project Repository**: https://github.com/rihanaa-m/week-8-scraper

**Author**: Rihanaa M

**Date**: July 2026
