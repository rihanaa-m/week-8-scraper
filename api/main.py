from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from datetime import datetime, timedelta
import os

from database import get_db, engine
from schemas import (
    ChannelMetrics, ChannelListResponse,
    MessageMetrics, MessageListResponse,
    DailyMetrics, TemporalAnalysisResponse,
    DetectedObject, ObjectListResponse,
    MessageSearchResponse
)

# Create FastAPI app
app = FastAPI(
    title="Medical Telegram Data Warehouse API",
    description="Analytical API for Ethiopian medical and pharmaceutical products data",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": "Medical Telegram Data Warehouse API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "channels": "/api/channels",
            "messages": "/api/messages",
            "temporal": "/api/temporal",
            "objects": "/api/objects",
            "search": "/api/search"
        }
    }


@app.get("/api/channels", response_model=ChannelListResponse)
def get_channels(
    skip: int = Query(0, ge=0, description="Number of channels to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of channels to return"),
    db: Session = Depends(get_db)
):
    """
    Get channel performance metrics.
    
    Returns aggregated statistics for each Telegram channel including:
    - Total posts
    - Average views
    - Total views and forwards
    - Media percentage
    """
    try:
        query = text("""
            SELECT 
                channel_name,
                total_posts,
                avg_views,
                total_views,
                total_forwards,
                media_percentage,
                first_post_date,
                last_post_date
            FROM dim_channels
            ORDER BY total_posts DESC
            LIMIT :limit OFFSET :skip
        """)
        
        result = db.execute(query, {"limit": limit, "skip": skip})
        channels = []
        
        for row in result:
            channels.append(ChannelMetrics(
                channel_name=row.channel_name,
                total_posts=row.total_posts,
                avg_views=float(row.avg_views),
                total_views=row.total_views,
                total_forwards=row.total_forwards,
                media_percentage=float(row.media_percentage),
                first_post_date=row.first_post_date,
                last_post_date=row.last_post_date
            ))
        
        # Get total count
        count_query = text("SELECT COUNT(*) FROM dim_channels")
        total = db.execute(count_query).scalar()
        
        return ChannelListResponse(channels=channels, total=total)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/messages", response_model=MessageListResponse)
def get_messages(
    channel_name: Optional[str] = Query(None, description="Filter by channel name"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    min_views: Optional[int] = Query(None, ge=0, description="Minimum view count"),
    has_image: Optional[bool] = Query(None, description="Filter by image presence"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get messages with filtering and pagination.
    
    Supports filtering by:
    - Channel name
    - Date range
    - Minimum views
    - Image presence
    """
    try:
        # Build WHERE clause
        conditions = []
        params = {}
        
        if channel_name:
            conditions.append("c.channel_name = :channel_name")
            params["channel_name"] = channel_name
        
        if start_date:
            conditions.append("d.full_date >= :start_date")
            params["start_date"] = start_date
        
        if end_date:
            conditions.append("d.full_date <= :end_date")
            params["end_date"] = end_date
        
        if min_views:
            conditions.append("f.view_count >= :min_views")
            params["min_views"] = min_views
        
        if has_image is not None:
            conditions.append("f.has_image_flag = :has_image")
            params["has_image"] = has_image
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        query = text(f"""
            SELECT 
                f.message_id,
                c.channel_name,
                d.full_date as message_date,
                f.message_length,
                f.view_count,
                f.forward_count,
                f.has_image_flag
            FROM fct_messages f
            JOIN dim_channels c ON f.channel_key = c.channel_key
            JOIN dim_dates d ON f.date_key = d.date_key
            WHERE {where_clause}
            ORDER BY d.full_date DESC, f.view_count DESC
            LIMIT :page_size OFFSET :offset
        """)
        
        params["page_size"] = page_size
        params["offset"] = offset
        
        result = db.execute(query, params)
        messages = []
        
        for row in result:
            messages.append(MessageMetrics(
                message_id=row.message_id,
                channel_name=row.channel_name,
                message_date=row.message_date,
                message_length=row.message_length,
                view_count=row.view_count,
                forward_count=row.forward_count,
                has_image_flag=row.has_image_flag
            ))
        
        # Get total count
        count_query = text(f"""
            SELECT COUNT(*)
            FROM fct_messages f
            JOIN dim_channels c ON f.channel_key = c.channel_key
            JOIN dim_dates d ON f.date_key = d.date_key
            WHERE {where_clause}
        """)
        total = db.execute(count_query, params).scalar()
        
        return MessageListResponse(
            messages=messages,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/temporal", response_model=TemporalAnalysisResponse)
def get_temporal_analysis(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    granularity: str = Query("daily", regex="^(daily|weekly|monthly)$", description="Time granularity"),
    db: Session = Depends(get_db)
):
    """
    Get temporal analysis metrics.
    
    Returns message statistics grouped by time period.
    Supports daily, weekly, and monthly granularity.
    """
    try:
        if granularity == "daily":
            date_format = "YYYY-MM-DD"
            group_by = "d.full_date"
        elif granularity == "weekly":
            date_format = "YYYY-'W'WW"
            group_by = "to_char(d.full_date, 'YYYY-\"W\"WW')"
        else:  # monthly
            date_format = "YYYY-MM"
            group_by = "to_char(d.full_date, 'YYYY-MM')"
        
        query = text(f"""
            SELECT 
                {group_by} as date,
                COUNT(*) as message_count,
                SUM(f.view_count) as total_views,
                AVG(f.view_count) as avg_views,
                SUM(f.forward_count) as total_forwards
            FROM fct_messages f
            JOIN dim_dates d ON f.date_key = d.date_key
            WHERE d.full_date BETWEEN :start_date AND :end_date
            GROUP BY {group_by}
            ORDER BY date
        """)
        
        result = db.execute(query, {"start_date": start_date, "end_date": end_date})
        metrics = []
        
        for row in result:
            metrics.append(DailyMetrics(
                date=row.date,
                message_count=row.message_count,
                total_views=row.total_views,
                avg_views=float(row.avg_views),
                total_forwards=row.total_forwards
            ))
        
        return TemporalAnalysisResponse(
            metrics=metrics,
            start_date=start_date,
            end_date=end_date
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/objects", response_model=ObjectListResponse)
def get_detected_objects(
    min_detections: int = Query(1, ge=1, description="Minimum detection count"),
    skip: int = Query(0, ge=0, description="Number of objects to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of objects to return"),
    db: Session = Depends(get_db)
):
    """
    Get detected objects from YOLO analysis.
    
    Returns objects detected in images with their statistics.
    """
    try:
        query = text("""
            SELECT 
                object_name,
                detection_count,
                first_detected,
                last_detected
            FROM dim_objects
            WHERE detection_count >= :min_detections
            ORDER BY detection_count DESC
            LIMIT :limit OFFSET :skip
        """)
        
        result = db.execute(query, {
            "min_detections": min_detections,
            "limit": limit,
            "skip": skip
        })
        
        objects = []
        
        for row in result:
            objects.append(DetectedObject(
                object_name=row.object_name,
                detection_count=row.detection_count,
                first_detected=row.first_detected,
                last_detected=row.last_detected
            ))
        
        # Get total count
        count_query = text("""
            SELECT COUNT(*) FROM dim_objects 
            WHERE detection_count >= :min_detections
        """)
        total = db.execute(count_query, {"min_detections": min_detections}).scalar()
        
        return ObjectListResponse(objects=objects, total=total)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search", response_model=List[MessageSearchResponse])
def search_messages(
    query: str = Query(..., min_length=1, description="Search query for message text"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return"),
    db: Session = Depends(get_db)
):
    """
    Search messages by text content.
    
    Performs full-text search on message content.
    """
    try:
        search_query = text("""
            SELECT 
                f.message_id,
                c.channel_name,
                d.full_date as message_date,
                f.message_text,
                f.view_count,
                f.forward_count,
                f.has_image_flag
            FROM fct_messages f
            JOIN dim_channels c ON f.channel_key = c.channel_key
            JOIN dim_dates d ON f.date_key = d.date_key
            WHERE f.message_text ILIKE :query
            ORDER BY f.view_count DESC
            LIMIT :limit
        """)
        
        result = db.execute(search_query, {
            "query": f"%{query}%",
            "limit": limit
        })
        
        messages = []
        
        for row in result:
            # Get detected objects for this message if available
            objects_query = text("""
                SELECT DISTINCT o.object_name
                FROM fct_message_objects mo
                JOIN dim_objects o ON mo.object_key = o.object_key
                WHERE mo.message_id = :message_id AND mo.channel_name = :channel_name
            """)
            
            objects_result = db.execute(objects_query, {
                "message_id": row.message_id,
                "channel_name": row.channel_name
            })
            
            detected_objects = [obj.object_name for obj in objects_result]
            
            messages.append(MessageSearchResponse(
                message_id=row.message_id,
                channel_name=row.channel_name,
                message_date=row.message_date,
                message_text=row.message_text,
                view_count=row.view_count,
                forward_count=row.forward_count,
                has_image_flag=row.has_image_flag,
                detected_objects=detected_objects if detected_objects else None
            ))
        
        return messages
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
