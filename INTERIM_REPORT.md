# Interim Report: Medical Telegram Data Warehouse

## Project Overview

This project builds a data warehouse for Ethiopian medical and pharmaceutical products by scraping Telegram channels, transforming the data with dbt, enriching it with YOLO object detection, and exposing it via a FastAPI API.

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

## Next Steps

1. Complete Task 2: Set up PostgreSQL and implement dbt transformation pipeline
2. Implement star schema with dimension and fact tables
3. Add comprehensive data quality tests
4. Proceed to Task 3: YOLO object detection integration
5. Build FastAPI API for data access
6. Implement Dagster orchestration for end-to-end pipeline

## Conclusion

The data lake structure is designed for scalability and efficiency, using partitioned storage and organized file naming conventions. The star schema follows dimensional modeling best practices to optimize for analytical queries. Data quality issues have been proactively addressed through error handling, logging, and planned validation in the transformation layer. The project is on track for successful completion of all tasks.
