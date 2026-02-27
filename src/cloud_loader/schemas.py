"""Pydantic schemas for API request/response."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response for upload endpoint."""

    code: str = Field(min_length=6, max_length=6)
    expires_at: datetime
    message: str = "Upload successful, please remember your verification code"


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str


# MD Storage schemas


class MdMetadata(BaseModel):
    """Metadata about the MD file."""

    filename: str = Field(
        min_length=1,
        max_length=100,
        description="Filename, e.g., CLAUDE.md, DEVELOPMENT.md, my-skill.md",
    )
    purpose: str = Field(
        min_length=1,
        max_length=500,
        description="What this file does, e.g., 'Project instructions for Claude Code'",
    )
    install_path: str = Field(
        min_length=1,
        max_length=200,
        description="Where to install, e.g., 'project root', '~/.claude/commands/'",
    )


class MdStorageCreateRequest(BaseModel):
    """Request for storing an MD file."""

    content: str = Field(min_length=1, description="MD file content")
    metadata: MdMetadata = Field(description="Information about the MD file")


class MdStorageCreateResponse(BaseModel):
    """Response for MD storage creation."""

    code: str = Field(min_length=6, max_length=6)
    message: str = "MD file stored successfully. This file is now publicly accessible."


class MdStorageGetResponse(BaseModel):
    """Response for getting a stored MD file."""

    code: str
    content: str
    content_size: int
    metadata: MdMetadata
    created_at: datetime
    download_count: int


class MdStorageListItem(BaseModel):
    """Item in MD storage list."""

    code: str
    filename: str
    purpose: str
    content_size: int
    created_at: datetime
    download_count: int


class MdStorageListResponse(BaseModel):
    """Response for listing MD files."""

    files: list[MdStorageListItem]
    total: int


# Backward compatibility aliases
TemplateCreateRequest = MdStorageCreateRequest
TemplateCreateResponse = MdStorageCreateResponse
TemplateGetResponse = MdStorageGetResponse


# Concept Tracking schemas

class ConceptCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    keywords: list[str] = Field(default_factory=list)
    search_interval_hours: int = Field(default=24)

class ConceptUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    keywords: Optional[list[str]] = Field(default=None)
    search_interval_hours: Optional[int] = Field(default=None)

class ConceptResponse(BaseModel):
    id: int
    name: str
    description: str
    keywords: list[str]
    search_interval_hours: int
    created_at: datetime
    updated_at: datetime

class ConceptSnapshotResponse(BaseModel):
    id: int
    concept_id: int
    knowledge_graph: dict
    summary: str
    source_urls: list[str]
    content_drafts: dict
    created_at: datetime
