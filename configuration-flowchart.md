# Cloud-Loader Configuration Flowchart

## Project Configuration Architecture

```mermaid
flowchart TB
    subgraph ENV["📄 .env File"]
        direction TB
        E1["HOST / PORT / BASE_URL"]
        E2["UPLOAD_DIR / DATA_DIR"]
        E3["MAX_FILE_SIZE_MB / EXPIRY_HOURS"]
        E4["TEMPLATE_EXPIRY_DAYS / MAX_TEMPLATE_SIZE_KB"]
        E5["TAVILY_API_KEY"]
        E6["OPENAI_API_KEY / ANTHROPIC_API_KEY"]
        E7["X_API_KEY / X_API_SECRET\nX_ACCESS_TOKEN / X_ACCESS_TOKEN_SECRET\nX_BEARER_TOKEN"]
    end

    subgraph CONFIG["⚙️ config.py — Settings (pydantic-settings)"]
        direction TB
        C_SERVER["🖥️ Server\nhost · port · base_url"]
        C_STORAGE["📂 Storage\nupload_dir · data_dir"]
        C_LIMITS["📏 Limits\nmax_file_size_mb · expiry_hours\ntemplate_expiry_days · max_template_size_kb"]
        C_KEYS["🔑 API Keys\ntavily · openai · anthropic · X/Twitter"]
        C_PROPS["🔧 Computed Properties\nmax_file_size_bytes\nmax_template_size_bytes\ndatabase_url → sqlite:///data_dir/cloud_loader.db"]
    end

    ENV -->|"pydantic-settings\nenv_file='.env'"| CONFIG

    subgraph DATABASE["🗄️ database.py"]
        DB_ENGINE["SQLModel Engine\nsqlite:/// + data_dir"]
        DB_INIT["init_db()\n· create tables\n· seed DuskConfig"]
        DB_SESSION["get_session()\nDependency Injection"]
    end

    CONFIG -->|"settings.database_url"| DB_ENGINE
    CONFIG -->|"settings.data_dir"| DB_INIT

    subgraph MODELS["📊 models.py — 6 DB Tables"]
        M_BACKUP["Backup\ncode · file_path · expires_at"]
        M_USER["User\nuser_id · api_key"]
        M_MD["MdStorage\ncode · content · filename · purpose"]
        M_BRAIN["BrainstormEntry\ntitle · summary · content"]
        M_DRUN["DuskRun\ntitle · status · duration"]
        M_DASK["DuskAskWake\nquestion · answer · is_answered"]
        M_DCFG["DuskConfig\ninterval_hours · enabled"]
    end

    DB_INIT -->|"SQLModel.metadata.create_all"| MODELS

    subgraph APP["🚀 main.py — FastAPI App (v0.5.0)"]
        direction TB
        LIFESPAN["Lifespan\n· init_db()\n· mkdir upload_dir\n· cleanup expired\n· start Dusk worker"]
        ROUTERS["Routers\n· api.router → /upload, /download, /md\n· auth.router → /register, /verify"]
        PAGES["Pages & Templates (Jinja2)\n· / → docs or redirect\n· /hub → Agent Hub\n· /human → Landing\n· /gallery → CLAUDE.md Gallery\n· /agent-brainstorm → Timeline"]
        CLEANUP["⏰ periodic_cleanup()\nEvery 1 hour"]
    end

    CONFIG -->|"settings.host\nsettings.port"| APP
    DATABASE --> APP

    subgraph DUSK["🌙 dusk_worker.py — Dusk Agent"]
        SCHED["APScheduler (AsyncIO)\nCron: 02,06,10,14,18,22 GMT+8"]
        SDK["Claude Agent SDK\nmodel: claude-opus-4-6\nmax_turns: 60"]
        MCP_TOOLS["MCP Servers\n· dusk-tools (dusk-mcp)\n· codex (codex-mcp)"]
        MEMORY["DUSK-MEMORY.md\n/home/wake/DUSK-MEMORY.md"]
    end

    CONFIG -->|"settings.data_dir\nAPI keys via os.environ"| DUSK
    LIFESPAN -->|"start_dusk_worker()"| SCHED
    SCHED -->|"run_dusk_pipeline()"| SDK
    SDK --> MCP_TOOLS
    SDK --> MEMORY

    subgraph SERVICES["🛠️ services/"]
        SVC_CLEAN["cleanup.py\nExpired backup removal"]
        SVC_TMPL["template.py\nMD storage CRUD"]
        SVC_AUTH["auth.py\nCode validation"]
        SVC_BACKUP["backup.py\nFile upload/download"]
        SVC_XPOST["x_poster.py\nTwitter/X posting (Tweepy)"]
    end

    APP --> SERVICES
    DUSK -->|"via MCP tools"| SVC_XPOST

    subgraph DEPS["📦 pyproject.toml — Dependencies"]
        D1["fastapi + uvicorn"]
        D2["sqlmodel + pydantic-settings"]
        D3["apscheduler"]
        D4["claude-agent-sdk"]
        D5["tavily-python + httpx"]
        D6["tweepy + jinja2"]
    end

    DEPS -.->|"Python ≥3.12\nuv package manager"| APP

    style ENV fill:#2d2d2d,stroke:#f5c542,color:#f5c542
    style CONFIG fill:#1e3a5f,stroke:#5ba3e6,color:#a8d8ff
    style DATABASE fill:#1e3a5f,stroke:#5ba3e6,color:#a8d8ff
    style MODELS fill:#3b1f5e,stroke:#b07de8,color:#d4b5f7
    style APP fill:#1a4332,stroke:#52c77f,color:#a3f0c4
    style DUSK fill:#3d2b1f,stroke:#e89b5c,color:#f5d4b3
    style SERVICES fill:#1a4332,stroke:#52c77f,color:#a3f0c4
    style DEPS fill:#2d2d2d,stroke:#999,color:#ccc
```

## Configuration Data Flow Summary

| Layer | Source | Key Responsibility |
|-------|--------|--------------------|
| `.env` | Environment file | Raw key-value pairs for all secrets & settings |
| `config.py` | `pydantic-settings` | Type-safe settings with defaults + computed properties |
| `database.py` | SQLModel + SQLite | Engine creation, table init, session injection |
| `models.py` | SQLModel ORM | 6 tables: Backup, User, MdStorage, BrainstormEntry, DuskRun/Ask/Config |
| `main.py` | FastAPI | App lifespan, route registration, periodic cleanup |
| `dusk_worker.py` | APScheduler + Claude SDK | Autonomous agent on cron schedule with MCP tools |
| `services/` | Business logic | Cleanup, auth, backup, templates, X/Twitter posting |
| `pyproject.toml` | uv / hatch | Dependency declarations, build config, entry point |

## Configuration Lifecycle State Machine

This state diagram illustrates the lifecycle of the application configuration, from environment loading to runtime state management.

```mermaid
stateDiagram-v2
    direction TB

    %% Phase 1: Configuration Loading (Import Time)
    state "1. Configuration Loading" as ConfigPhase {
        direction LR
        [*] --> LoadEnv : Import cloud_loader.config
        
        state "Load Environment" as LoadEnv {
            [*] --> ReadEnv : .env file
            ReadEnv --> ReadOs : os.environ
        }
        
        LoadEnv --> Validate : Pydantic BaseSettings
        
        state "Validation & Parsing" as Validate {
            [*] --> TypeCheck : Check types (int, path)
            TypeCheck --> ApplyDefaults : Apply default values
        }
        
        Validate --> Compute : @property methods
        
        state "Computed Properties" as Compute {
            [*] --> CalcBytes : max_file_size_bytes
            CalcBytes --> CalcDB : database_url
        }
        
        Compute --> Ready : settings object immutable
        Ready --> [*]
    }

    ConfigPhase --> StartupPhase : settings module imported

    %% Phase 2: Application Startup (Lifespan)
    state "2. Application Startup (Lifespan)" as StartupPhase {
        direction TB
        [*] --> InitDB : SQLModel create_all
        InitDB --> SetupFS : mkdir upload_dir
        SetupFS --> Prune : cleanup_expired_backups
        Prune --> LaunchWorker : start_dusk_worker
        LaunchWorker --> Serving : Yield
    }

    %% Phase 3: Runtime
    state "3. Runtime State" as RuntimePhase {
        direction LR
        
        state "FastAPI Server" as Server {
            [*] --> Idle
            Idle --> HandlingRequest : HTTP Request
            HandlingRequest --> Idle : Response
            
            note right of HandlingRequest
                Uses settings.base_url
                Uses settings.upload_dir
            end note
        }
        
        state "Dusk Worker (Background)" as Worker {
            [*] --> Scheduled : Cron (GMT+8 02,06,10,14,18,22)
            Scheduled --> Running : Trigger time reached
            
            state "Agent Pipeline" as Running {
                [*] --> LoadState : Read DB & Memory
                LoadState --> BuildContext : Prompt Construction
                BuildContext --> AgentExec : Claude SDK (Loop)
                AgentExec --> SaveState : Update DB & Memory
                SaveState --> [*]
            }
            
            Running --> Scheduled : Completion
        }
        
        state "Periodic Cleanup" as Cleanup {
            [*] --> Sleeping : 1 hour
            Sleeping --> Cleaning : Wake up
            Cleaning --> Sleeping : Done
        }
    }

    StartupPhase --> RuntimePhase : App Ready
    RuntimePhase --> ShutdownPhase : SIGTERM / SIGINT

    %% Phase 4: Shutdown
    state "4. Shutdown" as ShutdownPhase {
        [*] --> StopWorker : stop_dusk_worker
        StopWorker --> CancelTasks : cancel cleanup_task
        CancelTasks --> [*] : Process Exit
    }
```
