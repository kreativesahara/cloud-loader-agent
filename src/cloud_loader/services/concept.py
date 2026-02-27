"""Service logic for Concept Tracking."""

import json
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlmodel import Session, select

from cloud_loader.models import Concept, ConceptSnapshot
from cloud_loader.schemas import ConceptCreateRequest, ConceptUpdateRequest


def create_concept(session: Session, user_id: str, request: ConceptCreateRequest) -> Concept:
    """Create a new concept."""
    concept = Concept(
        user_id=user_id,
        name=request.name,
        description=request.description,
        keywords=json.dumps(request.keywords),
        search_interval_hours=request.search_interval_hours,
    )
    session.add(concept)
    session.commit()
    session.refresh(concept)
    return concept


def get_concept(session: Session, concept_id: int, user_id: str) -> Optional[Concept]:
    """Get a concept by ID and user ID."""
    return session.exec(
        select(Concept).where(Concept.id == concept_id).where(Concept.user_id == user_id)
    ).first()


def list_concepts(session: Session, user_id: str, limit: int = 50, offset: int = 0) -> Tuple[list[Concept], int]:
    """List concepts for a user with pagination."""
    query = select(Concept).where(Concept.user_id == user_id)
    
    # Get total count
    total = len(session.exec(query).all())
    
    # Get paginated results
    concepts = session.exec(query.order_by(Concept.created_at.desc()).offset(offset).limit(limit)).all()
    
    return list(concepts), total


def update_concept(session: Session, concept: Concept, request: ConceptUpdateRequest) -> Concept:
    """Update an existing concept."""
    if request.name is not None:
        concept.name = request.name
    if request.description is not None:
        concept.description = request.description
    if request.keywords is not None:
        concept.keywords = json.dumps(request.keywords)
    if request.search_interval_hours is not None:
        concept.search_interval_hours = request.search_interval_hours
        
    concept.updated_at = datetime.now(timezone.utc)
    
    session.add(concept)
    session.commit()
    session.refresh(concept)
    return concept


def delete_concept(session: Session, concept: Concept) -> None:
    """Delete a concept and its snapshots."""
    # Delete associated snapshots
    snapshots = session.exec(select(ConceptSnapshot).where(ConceptSnapshot.concept_id == concept.id)).all()
    for snapshot in snapshots:
        session.delete(snapshot)
        
    session.delete(concept)
    session.commit()


def get_latest_snapshot(session: Session, concept_id: int) -> Optional[ConceptSnapshot]:
    """Get the most recent snapshot for a concept."""
    return session.exec(
        select(ConceptSnapshot)
        .where(ConceptSnapshot.concept_id == concept_id)
        .order_by(ConceptSnapshot.created_at.desc())
    ).first()


def list_snapshots(session: Session, concept_id: int, limit: int = 20, offset: int = 0) -> Tuple[list[ConceptSnapshot], int]:
    """List snapshots for a concept with pagination."""
    query = select(ConceptSnapshot).where(ConceptSnapshot.concept_id == concept_id)
    
    total = len(session.exec(query).all())
    snapshots = session.exec(query.order_by(ConceptSnapshot.created_at.desc()).offset(offset).limit(limit)).all()
    
    return list(snapshots), total


def run_concept_search(session: Session, concept: Concept) -> ConceptSnapshot:
    """
    Mock implementation of a search run.
    In a real implementation, this would use Tavily API and OpenAI/Anthropic 
    to fetch data and generate a knowledge graph.
    """
    # Create a mock graph based on keywords
    keywords = json.loads(concept.keywords)
    nodes = [{"id": kw, "label": kw} for kw in keywords]
    edges = []
    if len(nodes) > 1:
        edges = [{"source": nodes[0]["id"], "target": nodes[i]["id"], "relationship": "related"} for i in range(1, len(nodes))]
        
    graph = {"nodes": nodes, "edges": edges}
    
    snapshot = ConceptSnapshot(
        concept_id=concept.id,
        knowledge_graph=json.dumps(graph),
        summary=f"Automated insights for {concept.name}",
        source_urls=json.dumps(["https://example.com/mock-source"]),
        content_drafts=json.dumps({"tweet": f"Check out the latest trends in {concept.name}! #AI", "blog_intro": f"Welcome to our deep dive on {concept.name}..."})
    )
    
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot
