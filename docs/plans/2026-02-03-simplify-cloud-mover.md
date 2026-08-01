# Simplify Cloud-Mover Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify Cloud-Mover to a single verification code flow, user sets zip password, installation instructions inside zip.

**Architecture:** Remove User table and OTP mechanism, Backup table directly uses code as main identifier. Upload generates code, download only needs code. API docs split into upload/download scenarios to teach Claude Code the operation flow.

**Tech Stack:** FastAPI, SQLModel, SQLite, pydantic-settings

---

### Task 1: Update config.py add BASE_URL

**Files:**
- Modify: `src/cloud_mover/config.py`

**Step 1: Modify config.py**

```python
"""Application configuration."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    host: str = "0.0.0.0"
    port: int = 8080
    base_url: str = "http://localhost:8080"  # Added
    upload_dir: Path = Path("./uploads")
    data_dir: Path = Path("./data")
    max_file_size_mb: int = 59
    expiry_hours: int = 24  #  otp_expiry_hours

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def max_file_size_bytes(self) -> int:
        """Return max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def database_url(self) -> str:
        """Return SQLite database URL."""
        return f"sqlite:///{self.data_dir}/cloud_mover.db"


settings = Settings()
```

**Step 2: Commit**

Run: `git add src/cloud_mover/config.py && git commit -m "feat: add base_url config, rename otp_expiry_hours to expiry_hours"`

---

### Task 2: Simplify models.py - Remove User 

**Files:**
- Modify: `src/cloud_mover/models.py`

**Step 1: Rewrite models.py**

```python
"""Database models using SQLModel."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class Backup(SQLModel, table=True):
    """Backup table for storing upload metadata."""

    __tablename__ = "backups"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=6)
    file_path: str
    file_size: int
    uploaded_at: datetime = Field(default_factory=_utc_now)
    expires_at: datetime
```

**Step 2: Commit**

Run: `git add src/cloud_mover/models.py && git commit -m "feat: simplify models - remove User table, add code to Backup"`

---

### Task 3: Simplify schemas.py

**Files:**
- Modify: `src/cloud_mover/schemas.py`

**Step 1: Rewrite schemas.py**

```python
"""Pydantic schemas for API request/response."""

from datetime import datetime

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response for upload endpoint."""

    code: str = Field(min_length=6, max_length=6)
    expires_at: datetime
    message: str = "Upload successful, please remember the verification code"


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
```

**Step 2: Commit**

Run: `git add src/cloud_mover/schemas.py && git commit -m "feat: simplify schemas - remove register/status/download schemas"`

---

### Task 4: Simplify auth.py - Remove OTP 

**Files:**
- Modify: `src/cloud_mover/services/auth.py`

**Step 1: Rewrite auth.py**

```python
"""Authentication service for code generation."""

import secrets
import string


def generate_code() -> str:
    """Generate a 6-character alphanumeric lowercase code."""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def is_valid_code(code: str) -> bool:
    """Validate code format: 6 alphanumeric lowercase characters."""
    if len(code) != 6:
        return False
    return code.isalnum() and code.islower()
```

**Step 2: Commit**

Run: `git add src/cloud_mover/services/auth.py && git commit -m "feat: simplify auth - remove OTP generation"`

---

### Task 5: Rewrite backup.py 

**Files:**
- Modify: `src/cloud_mover/services/backup.py`

**Step 1: Rewrite backup.py**

```python
"""Backup service for file operations."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel import Session, select

from cloud_mover.config import settings
from cloud_mover.models import Backup
from cloud_mover.services.auth import generate_code

MAX_CODE_GENERATION_ATTEMPTS = 100


def create_backup(
    session: Session,
    file_path: str,
    file_size: int,
) -> Backup:
    """Create a new backup record with unique code."""
    # Generate unique code
    for _ in range(MAX_CODE_GENERATION_ATTEMPTS):
        code = generate_code()
        existing = session.exec(select(Backup).where(Backup.code == code)).first()
        if not existing:
            break
    else:
        raise RuntimeError("Failed to generate unique code after max attempts")

    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.expiry_hours)

    backup = Backup(
        code=code,
        file_path=file_path,
        file_size=file_size,
        expires_at=expires_at,
    )
    session.add(backup)
    session.commit()
    session.refresh(backup)

    return backup


def get_backup_by_code(session: Session, code: str) -> Optional[Backup]:
    """Get backup by code if not expired."""
    return session.exec(
        select(Backup).where(
            Backup.code == code,
            Backup.expires_at > datetime.now(timezone.utc),
        )
    ).first()
```

**Step 2: Commit**

Run: `git add src/cloud_mover/services/backup.py && git commit -m "feat: simplify backup service - remove user dependency"`

---

### Task 6: Rewrite cleanup.py

**Files:**
- Modify: `src/cloud_mover/services/cleanup.py`

**Step 1: Rewrite cleanup.py**

```python
"""Cleanup service for expired backups."""

import os
from datetime import datetime, timezone

from sqlmodel import Session, select

from cloud_mover.models import Backup


def cleanup_expired_backups(session: Session) -> int:
    """Delete expired backups and their files. Returns count of deleted items."""
    now = datetime.now(timezone.utc)

    expired = session.exec(select(Backup).where(Backup.expires_at < now)).all()

    count = 0
    for backup in expired:
        if os.path.exists(backup.file_path):
            try:
                os.remove(backup.file_path)
            except OSError:
                pass
        session.delete(backup)
        count += 1

    if count > 0:
        session.commit()

    return count
```

**Step 2: Commit**

Run: `git add src/cloud_mover/services/cleanup.py && git commit -m "feat: simplify cleanup - remove ActionLog"`

---

### Task 7: Rewrite API 

**Files:**
- Modify: `src/cloud_mover/routers/api.py`

**Step 1: Rewrite api.py**

```python
"""API routes for Cloud-Mover."""

import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session

from cloud_mover.config import settings
from cloud_mover.database import get_session
from cloud_mover.schemas import ErrorResponse, UploadResponse
from cloud_mover.services.auth import is_valid_code
from cloud_mover.services.backup import create_backup, get_backup_by_code

router = APIRouter()


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={400: {"model": ErrorResponse}},
)
async def upload(
    file: Annotated[UploadFile, File()],
    session: Annotated[Session, Depends(get_session)],
):
    """Upload a backup file and get a verification code."""
    contents = await file.read()
    if len(contents) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds limit ({settings.max_file_size_mb}MB)",
        )

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.zip"
    file_path = str(settings.upload_dir / filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    backup = create_backup(session, file_path, len(contents))

    return UploadResponse(code=backup.code, expires_at=backup.expires_at)


@router.get(
    "/download/{code}",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def download(
    code: str,
    session: Annotated[Session, Depends(get_session)],
):
    """Download a backup file using verification code."""
    if not is_valid_code(code):
        raise HTTPException(status_code=400, detail="Invalid verification code format")

    backup = get_backup_by_code(session, code)
    if not backup:
        raise HTTPException(status_code=404, detail="Verification code does not exist or has expired")

    if not os.path.exists(backup.file_path):
        raise HTTPException(status_code=404, detail="Backup file does not exist")

    return FileResponse(
        backup.file_path,
        media_type="application/zip",
        filename=f"claude-backup-{code}.zip",
    )
```

**Step 2: Commit**

Run: `git add src/cloud_mover/routers/api.py && git commit -m "feat: simplify API - remove register/status, simplify upload/download"`

---

### Task 8: Rewrite main.py  API 

**Files:**
- Modify: `src/cloud_mover/main.py`

**Step 1: Rewrite main.py**

```python
"""Cloud-Mover FastAPI application."""

import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

from cloud_mover.config import settings
from cloud_mover.database import engine, init_db
from cloud_mover.routers import api
from cloud_mover.services.cleanup import cleanup_expired_backups


def get_api_documentation() -> str:
    """Generate API documentation with current base_url."""
    return f"""# Cloud-Mover API

Claude Code Migration Helper. Migrate Claude Code settings between different computers.

Service URL: {settings.base_url}

---

## Upload endpoint (Source computer)

You are helping the user move Claude Code settings to a new computer.

### Step 1: Prepare installation instructions

Create `INSTALL.md` file, containing:
- Which settings this backup contains (settings.json, keybindings.json, plugins, etc.)
- Where each file should be placed
- Extra installation steps needed for plugins (if any)

Example INSTALL.md:
```markdown
# Claude Code Migration Installation Instructions

## Included content
- settings.json - User settings
- keybindings.json - Keybinding settings
- plugins/ - Installed plugins

## Installation steps
1. Extract to ~/.claude/
2. Restart Claude Code

## Plugins instructions
- my-plugin: Need to run `npm install` install dependencies
```

### Step 2: Package files

Package the following into a zip (based on actual files present):
- `~/.claude/settings.json`
- `~/.claude/keybindings.json`
- `~/.claude/plugins/`
- `INSTALL.md`（You just created）

**Important**：User settingsZip password。

### Step 3: Upload

```
POST {settings.base_url}/upload
Content-Type: multipart/form-data
file: <zip file>
```

Response:
```json
{{{{
  "code": "a7x9k2",
  "expires_at": "2026-02-04T12:00:00Z",
  "message": "Upload successful, please remember the verification code"
}}}}
```

### Step 4: Inform user

Please tell the user:
- Verification code: `a7x9k2`（6 ）
- Zip password: user self-set
- Validity: 24 hours

User needs to provide these two pieces of info on the new computer.

---

## Download endpoint (Target computer)

You are helping the user receive Claude Code settings from the old computer.

### Step 1: Get information

Ask user for:
1. **Verification code**（6 alphanumeric characters）
2. **Zip password**（set by user on the old computer）

### Step 2: Download

```
GET {settings.base_url}/download/{{{{code}}}}
```

Response:zip file

### Step 3: Unzip

Zip password。

### Step 4: Install according to INSTALL.md

Read the extracted `INSTALL.md`, follow the instructions:
1. Place files in the correct locations (usually `~/.claude/`）
2. Execute necessary extra steps (like plugin dependency installation)
3. Restart Claude Code

---

## API Reference

### POST /upload

，Verification code。

**Request:** multipart/form-data
- `file`: zip file（Max {settings.max_file_size_mb}MB）

**Response:**
```json
{{{{
  "code": "a7x9k2",
  "expires_at": "2026-02-04T12:00:00Z",
  "message": "Upload successful, please remember the verification code"
}}}}
```

### GET /download/{{{{code}}}}

Verification code。

**Response:** application/zip

**Errors:**
- 400: Invalid verification code format
- 404: Verification code does not exist or has expired
""".strip()


async def periodic_cleanup():
    """Run cleanup every hour."""
    while True:
        await asyncio.sleep(3600)
        with Session(engine) as session:
            count = cleanup_expired_backups(session)
            if count > 0:
                print(f"Cleaned up {{count}} expired backups")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    init_db()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    with Session(engine) as session:
        cleanup_expired_backups(session)

    cleanup_task = asyncio.create_task(periodic_cleanup())

    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Cloud-Mover",
    description="Claude Code Migration Helper API",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(api.router)


@app.get("/", response_class=PlainTextResponse)
def root():
    """Return API documentation for Claude Code to read."""
    return get_api_documentation()


def main():
    """Run the application."""
    uvicorn.run(
        "cloud_mover.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

Run: `git add src/cloud_mover/main.py && git commit -m "feat: rewrite API docs for upload/download scenarios"`

---

### Task 9: Rewrite

**Files:**
- Modify: `tests/test_auth.py`
- Modify: `tests/test_api.py`

**Step 1: Rewrite test_auth.py**

```python
"""Tests for auth service."""

from cloud_mover.services.auth import generate_code, is_valid_code


def test_generate_code_length():
    """Generated code should be 6 characters."""
    code = generate_code()
    assert len(code) == 6


def test_generate_code_alphanumeric():
    """Generated code should be alphanumeric lowercase."""
    code = generate_code()
    assert code.isalnum()
    assert code.islower()


def test_generate_code_unique():
    """Generated codes should be unique."""
    codes = {generate_code() for _ in range(100)}
    assert len(codes) == 100


def test_is_valid_code_correct():
    """Valid code should pass validation."""
    assert is_valid_code("abc123") is True
    assert is_valid_code("xyz789") is True


def test_is_valid_code_wrong_length():
    """Code with wrong length should fail."""
    assert is_valid_code("abc") is False
    assert is_valid_code("abc12345") is False


def test_is_valid_code_invalid_chars():
    """Code with invalid characters should fail."""
    assert is_valid_code("ABC123") is False
    assert is_valid_code("abc-12") is False
```

**Step 2: Rewrite test_api.py**

```python
"""Integration tests for API endpoints."""

import io

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from cloud_mover.database import get_session
from cloud_mover.main import app


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
def client_fixture(session: Session, tmp_path):
    """Create a test client with dependency overrides."""
    from cloud_mover import config

    original_upload_dir = config.settings.upload_dir
    config.settings.upload_dir = tmp_path / "uploads"
    config.settings.upload_dir.mkdir(parents=True, exist_ok=True)

    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    config.settings.upload_dir = original_upload_dir


def test_root_returns_documentation(client: TestClient):
    """Root endpoint should return API documentation."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Cloud-Mover API" in response.text
    assert "POST /upload" in response.text
    assert "GET /download" in response.text


def test_upload_returns_code(client: TestClient):
    """Upload should return a 6-character code."""
    file_content = b"test backup content"
    response = client.post(
        "/upload",
        files={"file": ("backup.zip", io.BytesIO(file_content), "application/zip")},
    )
    assert response.status_code == 200

    data = response.json()
    assert "code" in data
    assert len(data["code"]) == 6
    assert data["code"].isalnum()
    assert "expires_at" in data


def test_upload_rejects_large_file(client: TestClient):
    """Upload should reject files exceeding size limit."""
    from cloud_mover import config

    original_max = config.settings.max_file_size_mb
    config.settings.max_file_size_mb = 0  # Set to 0 MB for test

    file_content = b"x" * 1024  # 1KB file
    response = client.post(
        "/upload",
        files={"file": ("backup.zip", io.BytesIO(file_content), "application/zip")},
    )
    assert response.status_code == 400

    config.settings.max_file_size_mb = original_max


def test_full_upload_download_flow(client: TestClient):
    """Test complete upload and download flow."""
    file_content = b"this is a test backup file content"

    # Upload
    upload_response = client.post(
        "/upload",
        files={"file": ("backup.zip", io.BytesIO(file_content), "application/zip")},
    )
    assert upload_response.status_code == 200
    code = upload_response.json()["code"]

    # Download
    download_response = client.get(f"/download/{code}")
    assert download_response.status_code == 200
    assert download_response.content == file_content


def test_download_invalid_code_format(client: TestClient):
    """Download should reject invalid code format."""
    response = client.get("/download/invalid")
    assert response.status_code == 400


def test_download_nonexistent_code(client: TestClient):
    """Download should return 404 for nonexistent code."""
    response = client.get("/download/abc123")
    assert response.status_code == 404
```

**Step 3: Run tests**

Run: `uv run pytest -v`

**Step 4: Commit**

Run: `git add tests/test_auth.py tests/test_api.py && git commit -m "test: rewrite tests for simplified API"`

---

### Task 10: Update README.md  CLAUDE.md

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

**Step 1: Rewrite README.md**

```markdown
# Cloud-Mover

Claude Code  API 。

## Features

- ， 6 Verification code
- Verification code
- Auto-delete after 24 hours (file + record)

## Privacy Protection

- Zip password，
- ，
- Verification code，

## 

```bash
uv sync
```

## 

 `.env` ：

```env
HOST=0.0.0.0
PORT=8080
BASE_URL=https://your-domain.com
MAX_FILE_SIZE_MB=59
EXPIRY_HOURS=24
```

## 

```bash
uv run cloud-mover
```

## API 

|  |  |  |
|------|------|------|
| `/` | GET | API （ Claude Code ） |
| `/upload` | POST | ，Verification code |
| `/download/{code}` | GET | Verification code |
```

**Step 2: Rewrite CLAUDE.md**

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Commands

```bash
uv run cloud-mover          # Start API server
uv run pytest               # Run all tests
uv run pytest tests/test_api.py::test_full_upload_download_flow  # Run single test
```

## Architecture

Cloud-Mover is a file transfer API for migrating Claude Code settings between machines.

### Flow

```
Upload(file) → code (6 chars, 24hr expiry)
Download(code) → file
```

User sets their own zip password for content protection. Server only stores code + file path.

### Module Structure

- `main.py` - FastAPI app, API documentation (context-aware for upload/download scenarios)
- `routers/api.py` - Endpoints: `/upload`, `/download/{code}`
- `services/auth.py` - Code generation and validation
- `services/backup.py` - Backup CRUD operations
- `services/cleanup.py` - Expired backup deletion
- `models.py` - SQLModel: Backup table only
- `schemas.py` - Pydantic response models
- `config.py` - Settings via pydantic-settings
- `database.py` - SQLite engine and session

### Key Behaviors

- Backups expire after 24 hours (configurable via `EXPIRY_HOURS`)
- File limit: 59MB (configurable via `MAX_FILE_SIZE_MB`)
- Expired backups fully deleted (file + DB record) for privacy
- `BASE_URL` in .env for API documentation
```

**Step 3: Commit**

Run: `git add README.md CLAUDE.md && git commit -m "docs: update README and CLAUDE.md for simplified API"`

---

### Task 11:  .env.example

**Files:**
- Create: `.env.example`

**Step 1:  .env.example**

```env
HOST=0.0.0.0
PORT=8080
BASE_URL=https://your-domain.com
MAX_FILE_SIZE_MB=59
EXPIRY_HOURS=24
```

**Step 2: Commit**

Run: `git add .env.example && git commit -m "chore: add .env.example"`

---

### Task 12: 

**Step 1: **

Run: `rm -rf data/ uploads/`

**Step 2: **

Run: `uv run pytest -v`

Expected: All tests pass

**Step 3: Final commit**

Run: `git add -A && git commit -m "chore: cleanup and verify simplified Cloud-Mover" --allow-empty`
