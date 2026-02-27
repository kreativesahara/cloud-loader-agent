"""API routes for Concept Tracking."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from cloud_loader.database import get_session
from cloud_loader.models import Concept, ConceptSnapshot, User
from cloud_loader.routers.auth import require_auth
from cloud_loader.schemas import (
    ConceptCreateRequest,
    ConceptResponse,
    ConceptSnapshotResponse,
    ConceptUpdateRequest,
    ErrorResponse,
)
from cloud_loader.services import concept as concept_service

router = APIRouter(prefix="/api/concepts", tags=["concepts"])


def _to_response(c: Concept) -> ConceptResponse:
    try:
        keywords = json.loads(c.keywords)
    except:
        keywords = []
        
    return ConceptResponse(
        id=c.id,
        name=c.name,
        description=c.description,
        keywords=keywords,
        search_interval_hours=c.search_interval_hours,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _to_snapshot_response(s: ConceptSnapshot) -> ConceptSnapshotResponse:
    try:
        kg = json.loads(s.knowledge_graph)
    except:
        kg = {"nodes": [], "edges": []}
        
    try:
        urls = json.loads(s.source_urls)
    except:
        urls = []
        
    try:
        drafts = json.loads(s.content_drafts)
    except:
        drafts = {}
        
    return ConceptSnapshotResponse(
        id=s.id,
        concept_id=s.concept_id,
        knowledge_graph=kg,
        summary=s.summary,
        source_urls=urls,
        content_drafts=drafts,
        created_at=s.created_at,
    )


@router.post("", response_model=ConceptResponse)
def create_concept(
    request: ConceptCreateRequest,
    user: Annotated[User, Depends(require_auth)],
    session: Annotated[Session, Depends(get_session)],
):
    """Create a new concept to track."""
    c = concept_service.create_concept(session, user.user_id, request)
    return _to_response(c)


@router.get("", response_model=list[ConceptResponse])
def list_concepts(
    user: Annotated[User, Depends(require_auth)],
    session: Annotated[Session, Depends(get_session)],
    limit: int = 50,
    offset: int = 0,
):
    """List all concepts for the current user."""
    concepts, _ = concept_service.list_concepts(session, user.user_id, limit, offset)
    return [_to_response(c) for c in concepts]


@router.get("/{concept_id}", response_model=ConceptResponse)
def get_concept(
    concept_id: int,
    user: Annotated[User, Depends(require_auth)],
    session: Annotated[Session, Depends(get_session)],
):
    """Get a specific concept."""
    c = concept_service.get_concept(session, concept_id, user.user_id)
    if not c:
        raise HTTPException(status_code=404, detail="Concept not found")
    return _to_response(c)


@router.put("/{concept_id}", response_model=ConceptResponse)
def update_concept(
    concept_id: int,
    request: ConceptUpdateRequest,
    user: Annotated[User, Depends(require_auth)],
    session: Annotated[Session, Depends(get_session)],
):
    """Update a specific concept."""
    c = concept_service.get_concept(session, concept_id, user.user_id)
    if not c:
        raise HTTPException(status_code=404, detail="Concept not found")
        
    updated = concept_service.update_concept(session, c, request)
    return _to_response(updated)


@router.delete("/{concept_id}")
def delete_concept(
    concept_id: int,
    user: Annotated[User, Depends(require_auth)],
    session: Annotated[Session, Depends(get_session)],
):
    """Delete a concept and all its snapshots."""
    c = concept_service.get_concept(session, concept_id, user.user_id)
    if not c:
        raise HTTPException(status_code=404, detail="Concept not found")
        
    concept_service.delete_concept(session, c)
    return {"status": "success"}


@router.post("/{concept_id}/run", response_model=ConceptSnapshotResponse)
def run_concept_search(
    concept_id: int,
    user: Annotated[User, Depends(require_auth)],
    session: Annotated[Session, Depends(get_session)],
):
    """Trigger a manual search run for a concept."""
    c = concept_service.get_concept(session, concept_id, user.user_id)
    if not c:
        raise HTTPException(status_code=404, detail="Concept not found")
        
    snapshot = concept_service.run_concept_search(session, c)
    return _to_snapshot_response(snapshot)


@router.get("/{concept_id}/snapshots", response_model=list[ConceptSnapshotResponse])
def list_snapshots(
    concept_id: int,
    user: Annotated[User, Depends(require_auth)],
    session: Annotated[Session, Depends(get_session)],
    limit: int = 20,
    offset: int = 0,
):
    """List all snapshots for a concept."""
    c = concept_service.get_concept(session, concept_id, user.user_id)
    if not c:
        raise HTTPException(status_code=404, detail="Concept not found")
        
    snapshots, _ = concept_service.list_snapshots(session, concept_id, limit, offset)
    return [_to_snapshot_response(s) for s in snapshots]


@router.get("/{concept_id}/snapshots/latest", response_model=ConceptSnapshotResponse)
def get_latest_snapshot(
    concept_id: int,
    user: Annotated[User, Depends(require_auth)],
    session: Annotated[Session, Depends(get_session)],
):
    """Get the latest snapshot for a concept."""
    c = concept_service.get_concept(session, concept_id, user.user_id)
    if not c:
        raise HTTPException(status_code=404, detail="Concept not found")
        
    s = concept_service.get_latest_snapshot(session, concept_id)
    if not s:
        raise HTTPException(status_code=404, detail="No snapshots found for this concept")
        
    return _to_snapshot_response(s)
