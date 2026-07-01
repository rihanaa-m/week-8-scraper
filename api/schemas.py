from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# Channel schemas
class ChannelMetrics(BaseModel):
    channel_name: str
    total_posts: int
    avg_views: float
    total_views: int
    total_forwards: int
    media_percentage: float
    first_post_date: Optional[datetime]
    last_post_date: Optional[datetime]


class ChannelListResponse(BaseModel):
    channels: List[ChannelMetrics]
    total: int


# Message schemas
class MessageMetrics(BaseModel):
    message_id: int
    channel_name: str
    message_date: datetime
    message_length: int
    view_count: int
    forward_count: int
    has_image_flag: bool


class MessageListResponse(BaseModel):
    messages: List[MessageMetrics]
    total: int
    page: int
    page_size: int


# Temporal analysis schemas
class DailyMetrics(BaseModel):
    date: str
    message_count: int
    total_views: int
    avg_views: float
    total_forwards: int


class TemporalAnalysisResponse(BaseModel):
    metrics: List[DailyMetrics]
    start_date: str
    end_date: str


# Object detection schemas
class DetectedObject(BaseModel):
    object_name: str
    detection_count: int
    first_detected: Optional[datetime]
    last_detected: Optional[datetime]


class ObjectListResponse(BaseModel):
    objects: List[DetectedObject]
    total: int


# Search schemas
class MessageSearchResponse(BaseModel):
    message_id: int
    channel_name: str
    message_date: datetime
    message_text: str
    view_count: int
    forward_count: int
    has_image_flag: bool
    detected_objects: Optional[List[str]] = None
