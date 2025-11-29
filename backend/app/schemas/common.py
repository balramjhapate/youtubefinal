"""
Common Pydantic schemas for shared operations
"""
from pydantic import BaseModel, Field
from typing import List


class BulkDeleteRequest(BaseModel):
    """Bulk delete request"""
    video_ids: List[int] = Field(..., description="List of video IDs to delete")


class BulkDeleteResponse(BaseModel):
    """Bulk delete response"""
    status: str
    message: str
    deleted_count: int


class RetryResponse(BaseModel):
    """Retry operation response"""
    status: str
    message: str

