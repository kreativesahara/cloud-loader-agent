"""Tests for Concept Tracking API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from cloud_loader.database import get_session
from cloud_loader.main import app
from cloud_loader.models import User
from cloud_loader.services.auth import generate_api_key, generate_user_id


@pytest.fixture(name="session")
def session_fixture():
    """Create a test database session."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a test client with dependency overrides."""
    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Create a test user and return API key block."""
    user = User(user_id=generate_user_id(), api_key=generate_api_key())
    session.add(user)
    session.commit()
    return user


def test_create_concept(client: TestClient, test_user: User):
    """Test creating a new concept."""
    headers = {"Authorization": f"Bearer {test_user.api_key}"}
    payload = {
        "name": "Vehicle Buying Guide",
        "description": "Information on buying vehicles in Kenya",
        "keywords": ["vehicle", "buying", "kenya", "cars"],
        "search_interval_hours": 12
    }
    
    response = client.post("/api/concepts", json=payload, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "Vehicle Buying Guide"
    assert data["keywords"] == ["vehicle", "buying", "kenya", "cars"]
    assert data["search_interval_hours"] == 12
    assert "id" in data


def test_list_concepts(client: TestClient, test_user: User):
    """Test listing concepts."""
    headers = {"Authorization": f"Bearer {test_user.api_key}"}
    
    # Create two concepts
    client.post("/api/concepts", json={"name": "C1"}, headers=headers)
    client.post("/api/concepts", json={"name": "C2"}, headers=headers)
    
    response = client.get("/api/concepts", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "C2"  # Sorted by created_at desc
    assert data[1]["name"] == "C1"


def test_update_concept(client: TestClient, test_user: User):
    """Test updating a concept."""
    headers = {"Authorization": f"Bearer {test_user.api_key}"}
    
    # Create concept
    create_resp = client.post("/api/concepts", json={"name": "Old Name"}, headers=headers)
    concept_id = create_resp.json()["id"]
    
    # Update concept
    update_resp = client.put(f"/api/concepts/{concept_id}", json={"name": "New Name"}, headers=headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "New Name"
    
    
def test_concept_run(client: TestClient, test_user: User):
    """Test triggering a concept run."""
    headers = {"Authorization": f"Bearer {test_user.api_key}"}
    
    # Create concept
    create_resp = client.post(
        "/api/concepts", 
        json={"name": "Car renting", "keywords": ["rent", "car"]}, 
        headers=headers
    )
    concept_id = create_resp.json()["id"]
    
    # Run
    run_resp = client.post(f"/api/concepts/{concept_id}/run", headers=headers)
    assert run_resp.status_code == 200
    
    data = run_resp.json()
    assert data["concept_id"] == concept_id
    assert "summary" in data
    assert "Automated insights for Car renting" in data["summary"]
    
    # Check latest snapshot
    latest_resp = client.get(f"/api/concepts/{concept_id}/snapshots/latest", headers=headers)
    assert latest_resp.status_code == 200
    assert latest_resp.json()["id"] == data["id"]
