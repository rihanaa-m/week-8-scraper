# Interim Report: Medical Telegram Data Warehouse

## Project Overview

This project builds a data warehouse for Ethiopian medical and pharmaceutical products by scraping Telegram channels, transforming the data with dbt, enriching it with YOLO object detection, and exposing it via a FastAPI API.

## Business Objectives

The primary business objectives this data warehouse addresses are:

1. **Market Intelligence**: Understand product trends, pricing patterns, and demand for medical and pharmaceutical products in Ethiopia through Telegram channel analysis
2. **Product Availability Tracking**: Monitor which products are being advertised and promoted across different channels to identify supply chain insights
3. **Channel Performance Analysis**: Compare engagement metrics (views, forwards) across different channels to understand which platforms are most effective for product promotion
4. **Content Effectiveness**: Analyze message characteristics (length, image presence) to determine what content drives higher engagement
5. **Temporal Patterns**: Identify seasonal trends, optimal posting times, and posting frequency patterns to inform marketing strategies

## Business Questions the Architecture Enables

The star schema and data lake architecture directly support answering these critical business questions:

- **Which product categories are most frequently promoted?** → Analyzed through message text classification and channel_type dimension
- **What are the peak engagement times for medical product promotions?** → Enabled through dim_date attributes (day_of_week, is_weekend, hour) joined with fct_messages view_count
- **Which channels have the highest audience engagement?** → Calculated via dim_channels.avg_views and total_posts metrics
- **How does image content affect message engagement?** → Measured through has_image_flag in fct_messages correlated with view_count and forward_count
- **What are the temporal trends in product availability?** → Tracked through date dimension analysis of message posting frequency
- **Which product descriptions drive the most forwards?** → Analyzed through message_length and message_text patterns in fct_messages

## Data Lake Structure

### Directory Organization

```
data/
└── raw/
    ├── telegram_messages/
    │   └── YYYY-MM-DD/
    │       ├── channel_name.json
    │       └── ...
    └── images/
        ├── channel_name/
        │   ├── {message_id}.jpg
        │   └── ...
        └── ...
```

### Data Lake Design Decisions

**Partitioned Storage by Date**
- Messages are partitioned by date (`YYYY-MM-DD`) to optimize query performance for time-based analysis
- Each date partition contains JSON files for each channel scraped on that date
- This structure allows efficient data loading and querying for specific time periods

**Organized Image Storage**
- Images are stored in a channel-specific directory structure
- Each image is named by its message ID for easy reference back to the message data
- This separation of text and binary data improves storage efficiency and access patterns

**JSON Format for Raw Data**
- Raw data is stored in JSON format to preserve the original structure from the Telegram API
- JSON is human-readable and easily parsable for downstream processing
- Maintains flexibility for schema evolution as API responses may change

### Data Fields Collected

| Field | Description | Type |
|-------|-------------|------|
| message_id | Unique identifier for each message | Integer |
| channel_name | Name of the Telegram channel | String |
| message_date | Timestamp of the message | ISO 8601 datetime |
| message_text | Full text content (product names, prices, descriptions) | String |
| has_media | Whether the message contains media | Boolean |
| image_path | Path to downloaded image (if applicable) | String |
| views | Number of views on the message | Integer |
| forwards | Number of times the message was forwarded | Integer |

## Star Schema Design

### Overview

The star schema follows dimensional modeling best practices to optimize for analytical queries. It separates descriptive attributes (dimensions) from quantitative metrics (facts).

### Star Schema Diagram

```
                    dim_channels
                    ------------
                    channel_key (PK)
                    channel_name
                    channel_type
                    first_post_date
                    last_post_date
                    total_posts
                    avg_views
                          |
                          |
                    fct_messages
                    ------------
                    message_id (PK)
                    channel_key (FK) ----+
                    date_key (FK) ------+|
                    message_text        ||
                    message_length       ||
                    view_count          ||
                    forward_count       ||
                    has_image_flag      ||
                          |             |
                          |             |
                    dim_dates      dim_channels
                    ---------      -----------
                    date_key (PK)  channel_key (PK)
                    full_date      channel_name
                    day_of_week    channel_type
                    day_name       first_post_date
                    week_of_year   last_post_date
                    month          total_posts
                    month_name     avg_views
                    quarter
                    year
                    is_weekend
```

### Business Value of Star Schema Design

The star schema architecture directly enables the business objectives through:

- **Fast Channel Performance Queries**: dim_channels pre-aggregates metrics (avg_views, total_posts) for instant channel comparison without complex joins
- **Temporal Analysis Efficiency**: dim_dates provides pre-calculated date attributes (weekend flags, quarters) for quick trend analysis without date manipulation
- **Scalable Message Analysis**: fct_messages stores individual message metrics that can be aggregated by any dimension (channel, date, or future dimensions like product category)
- **Flexible Schema Evolution**: New dimensions (e.g., dim_products, dim_locations) can be added without disrupting existing fact table structure
- **Optimized for BI Tools**: Star schema structure is compatible with most BI and visualization tools for business user self-service analytics

### Dimension Tables

#### dim_channels
Stores channel-level metadata and aggregated statistics.

- **channel_key**: Surrogate key for unique channel identification
- **channel_name**: Original Telegram channel name
- **channel_type**: Classification (Pharmaceutical/Cosmetics/Medical)
- **first_post_date**: Date of first message from this channel
- **last_post_date**: Date of most recent message from this channel
- **total_posts**: Count of all messages from this channel
- **avg_views**: Average view count across all messages

#### dim_dates
Stores date attributes for time-based analysis.

- **date_key**: Surrogate key (YYYYMMDD format)
- **full_date**: Complete date value
- **day_of_week**: Numeric day of week (1-7)
- **day_name**: Day name (Monday, Tuesday, etc.)
- **week_of_year**: Week number within the year
- **month**: Numeric month (1-12)
- **month_name**: Month name
- **quarter**: Quarter of year (Q1-Q4)
- **year**: Year value
- **is_weekend**: Boolean flag for weekend days

### Fact Table

#### fct_messages
Stores individual message-level metrics with foreign keys to dimensions.

- **message_id**: Unique message identifier (natural key)
- **channel_key**: Foreign key to dim_channels
- **date_key**: Foreign key to dim_dates
- **message_text**: Full message content
- **message_length**: Character count of message text
- **view_count**: Number of views
- **forward_count**: Number of forwards
- **has_image_flag**: Boolean indicating image presence

### Star Schema Benefits

1. **Query Performance**: Simple joins with fewer tables compared to normalized schemas
2. **Understandability**: Intuitive structure that matches business thinking
3. **Flexibility**: Easy to add new dimensions or facts without disrupting existing structure
4. **Aggregation**: Efficient for aggregating metrics across dimensions
5. **Maintenance**: Clear separation between descriptive data and metrics

## Data Quality Issues and Solutions

### Issue 1: API Rate Limiting

**Problem**: Telegram API has rate limits that can cause scraping to fail or be delayed.

**Solution**:
- Implemented error handling in the scraper to catch rate limit exceptions
- Added logging to track when rate limits are encountered
- Structured the scraper to be resumable - can be run multiple times without duplicating data
- Used async/await pattern to handle network delays gracefully

### Issue 2: Private/Inaccessible Channels

**Problem**: Some channels may be private or not accessible due to permissions.

**Solution**:
- Added specific error handling for `ChannelPrivateError` and `ChannelInvalidError`
- Implemented graceful degradation - if one channel fails, others continue to be scraped
- Logged which channels are inaccessible for later review
- Configurable channel list in `.env` allows easy removal of problematic channels

### Issue 3: Incomplete Message Data

**Problem**: Some messages may have missing fields (null views, empty text, etc.).

**Solution**:
- Implemented default values for missing numeric fields (0 for views/forwards)
- Empty strings for missing text fields
- Boolean flags to indicate presence/absence of media
- All data quality issues are logged for review
- Staging layer in dbt will apply additional validation and cleaning

### Issue 4: Image Download Failures

**Problem**: Network issues or corrupted media can cause image downloads to fail.

**Solution**:
- Individual try-catch blocks for each image download
- Failed image downloads don't stop the overall scraping process
- Image path set to null if download fails
- Detailed error logging for troubleshooting

### Issue 5: Date Consistency

**Problem**: Message dates from Telegram may be in different time zones or formats.

**Solution**:
- Telegram API returns ISO 8601 format which is standardized
- All dates stored in UTC for consistency
- Date dimension table will provide localized date attributes in the transformation layer
- Staging models will validate date ranges and identify anomalies

### Issue 6: Duplicate Messages

**Problem**: Running the scraper multiple times could create duplicate records.

**Solution**:
- Data lake partitioned by date prevents accidental overwrites
- Each JSON file contains messages for a specific date and channel
- Future implementation will include deduplication logic in the staging layer
- Natural keys (message_id + channel_name + date) will be used to identify duplicates

## Current Progress

### Completed (Task 1)
- ✅ Project structure and environment setup
- ✅ Telegram API integration with Telethon
- ✅ Data scraper implementation
- ✅ Image download functionality
- ✅ Data lake storage with partitioned structure
- ✅ Logging and error handling
- ✅ Git repository initialization and code push

### In Progress (Task 2)
- ⏳ PostgreSQL database setup
- ⏳ Raw data loading script
- ⏳ dbt project initialization
- ⏳ Staging models development
- ⏳ Star schema implementation
- ⏳ Data quality tests

### Pending (Tasks 3-5)
- ⏳ YOLO object detection for image enrichment
- ⏳ FastAPI analytical API development
- ⏳ Dagster pipeline orchestration

## Technical Stack

- **Scraping**: Python, Telethon
- **Storage**: JSON files (data lake), PostgreSQL (data warehouse)
- **Transformation**: dbt (Data Build Tool)
- **Enrichment**: YOLOv8 (object detection)
- **API**: FastAPI
- **Orchestration**: Dagster
- **Version Control**: Git, GitHub

## Detailed Next Steps and Anticipated Challenges

### Task 2: Data Modeling and Transformation with dbt

**Phase 1: PostgreSQL Setup and Raw Data Loading**
- Install and configure PostgreSQL database
- Create raw schema and telegram_messages table
- Develop Python script to load JSON files from data lake to PostgreSQL
- **Anticipated Challenges**:
  - Large JSON file sizes may cause memory issues during bulk loading
  - Data type mismatches between JSON and PostgreSQL schema
  - Network connectivity issues if PostgreSQL is hosted remotely
  - **Mitigation**: Implement batch loading, add data type validation, use connection pooling

**Phase 2: dbt Project Initialization**
- Install dbt-postgres and initialize dbt project
- Configure profiles.yml for PostgreSQL connection
- Set up project structure (models/staging, models/marts, tests/)
- **Anticipated Challenges**:
  - dbt profile configuration errors on Windows
  - PostgreSQL driver compatibility issues
  - **Mitigation**: Use official dbt documentation, test connection with simple query first

**Phase 3: Staging Models Development**
- Create stg_telegram_messages.sql model
- Implement data type casting (dates, integers)
- Add calculated fields (message_length, has_image_flag)
- Filter invalid records (empty messages, nulls)
- **Anticipated Challenges**:
  - Complex date parsing from ISO 8601 format
  - Handling inconsistent text encoding
  - Determining appropriate null handling strategies
  - **Mitigation**: Use dbt built-in date functions, add encoding detection, document null handling rules

**Phase 4: Star Schema Implementation**
- Create dim_channels dimension table
- Create dim_dates dimension table with comprehensive date attributes
- Create fct_messages fact table with foreign keys
- Implement surrogate key generation
- **Anticipated Challenges**:
  - Surrogate key generation complexity in dbt
  - Handling slowly changing dimensions (SCD) for channels
  - Date dimension population for future dates
  - **Mitigation**: Use dbt-utils for surrogate keys, implement SCD Type 2 for channels, pre-populate date dimension

**Phase 5: Data Quality Tests**
- Add unique and not_null tests on primary keys
- Implement relationships tests on foreign keys
- Create custom data tests (assert_no_future_messages, assert_positive_views)
- **Anticipated Challenges**:
  - Test performance on large datasets
  - False positives in custom tests
  - Test maintenance as schema evolves
  - **Mitigation**: Use incremental testing, document test logic, version control test definitions

### Task 3: Data Enrichment with YOLO Object Detection

**Phase 1: YOLO Environment Setup**
- Install ultralytics library
- Download YOLOv8 nano model (yolov8n.pt)
- Test object detection on sample images
- **Anticipated Challenges**:
  - Model download size and network bandwidth
  - GPU availability for faster inference
  - Model accuracy on medical product images
  - **Mitigation**: Use smaller nano model, implement CPU fallback, validate detection results manually

**Phase 2: Object Detection Script Development**
- Create src/yolo_detect.py script
- Scan downloaded images in data/raw/images/
- Run YOLO detection on each image
- Record detected objects with confidence scores
- Save results to CSV file
- **Anticipated Challenges**:
  - Large number of images causing long processing time
  - Low confidence detections requiring threshold tuning
  - Memory usage during batch processing
  - **Mitigation**: Implement batch processing, add progress logging, use confidence threshold of 0.5

**Phase 3: Integration with Data Warehouse**
- Load YOLO detection results into PostgreSQL
- Create dim_objects dimension table
- Add object detection results to fact table or create bridge table
- Update dbt models to include enriched data
- **Anticipated Challenges**:
  - Schema design for multiple objects per image
  - Join complexity between messages and detected objects
  - Data freshness (detection vs message timestamp)
  - **Mitigation**: Use bridge table design, document join logic, add detection timestamp

### Task 4: Analytical API Development with FastAPI

**Phase 1: FastAPI Project Setup**
- Install FastAPI, uvicorn, and dependencies
- Create project structure (api/main.py, api/database.py, api/schemas.py)
- Implement database connection pooling
- **Anticipated Challenges**:
  - Async database connection management
  - SQL injection prevention
  - API authentication and security
  - **Mitigation**: Use SQLAlchemy async, parameterized queries, implement JWT authentication

**Phase 2: API Endpoint Development**
- Create endpoints for channel metrics
- Create endpoints for temporal analysis
- Create endpoints for message search
- Implement pagination and filtering
- **Anticipated Challenges**:
  - Query performance on large datasets
  - API rate limiting and abuse prevention
  - Response format consistency
  - **Mitigation**: Add database indexes, implement rate limiting, use Pydantic schemas

**Phase 3: API Documentation and Testing**
- Generate OpenAPI documentation
- Add example requests/responses
- Implement unit tests for endpoints
- Add logging and monitoring
- **Anticipated Challenges**:
  - Documentation completeness
  - Test data management
  - Error handling consistency
  - **Mitigation**: Use auto-documentation features, create test fixtures, standardize error responses

### Task 5: Pipeline Orchestration with Dagster

**Phase 1: Dagster Project Setup**
- Install Dagster and dependencies
- Initialize Dagster project
- Configure Dagster UI
- **Anticipated Challenges**:
  - Dagster installation complexity
  - Local vs production configuration
  - Resource management (CPU, memory)
  - **Mitigation**: Follow official installation guide, use environment variables, monitor resource usage

**Phase 2: Pipeline Definition**
- Define assets for scraping, transformation, enrichment
- Create job dependencies and schedules
- Implement error handling and retries
- **Anticipated Challenges**:
  - Complex dependency management
  - Failure recovery strategies
  - Schedule configuration for different time zones
  - **Mitigation**: Use asset-based approach, implement checkpointing, use UTC for schedules

**Phase 3: Deployment and Monitoring**
- Deploy Dagster to production environment
- Set up monitoring and alerting
- Implement backfill strategies
- **Anticipated Challenges**:
  - Production environment differences
  - Long-running job monitoring
  - Backfill performance on historical data
  - **Mitigation**: Use Docker for consistency, implement health checks, use incremental backfill

### Cross-Cutting Considerations

**Documentation**
- Maintain comprehensive code comments
- Keep README files updated for each component
- Document API endpoints and data schemas
- Create architecture diagrams

**Testing Strategy**
- Unit tests for transformation logic
- Integration tests for API endpoints
- End-to-end tests for complete pipeline
- Data quality tests in dbt

**Performance Optimization**
- Database indexing for frequently queried columns
- Caching strategies for API responses
- Batch processing for large datasets
- Query optimization for complex joins

**Security**
- Secure credential management (environment variables, secrets)
- API authentication and authorization
- Data encryption at rest and in transit
- Regular security audits

## Conclusion

The data lake structure is designed for scalability and efficiency, using partitioned storage and organized file naming conventions. The star schema follows dimensional modeling best practices to optimize for analytical queries while directly supporting key business objectives including market intelligence, channel performance analysis, and content effectiveness measurement. Data quality issues have been proactively addressed through error handling, logging, and planned validation in the transformation layer.

The detailed roadmap for remaining tasks identifies specific challenges and mitigation strategies for each phase, ensuring the project can navigate technical complexities while maintaining data quality and system reliability. The architecture is designed to be flexible and extensible, allowing for future enhancements such as additional dimensions, new data sources, and advanced analytics capabilities.

The project is on track for successful completion of all tasks, with a clear understanding of both technical requirements and business value delivery.
