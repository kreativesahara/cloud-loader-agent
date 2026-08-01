# Waterfall Model Checklist for Cloud-Loader

This checklist adapts the traditional Waterfall methodology for running and developing the Cloud-Loader project. Each phase must be completed and reviewed before moving to the next.

## 1. Requirements Analysis
- [ ] Define new features, API endpoints, or modifications to the Cloud-Loader system.
- [ ] Document all requirements for file transfer, concept tracking, and authentication.
- [ ] Review `.env` configuration needs (e.g., Anthropic, Tavily keys).
- [ ] Finalize the Requirements Specification document.
- [ ] Obtain stakeholder approval for requirements.

## 2. System Design
- [ ] Design the API architecture (e.g., FastAPI routing for new endpoints).
- [ ] Plan the data models and storage mechanisms (e.g., changes to `./data` or `./uploads`).
- [ ] Define the interaction between the worker scripts (e.g. `dusk_worker.py`) and the main application.
- [ ] Review system security (password protection, 24-hour auto-deletion policy).
- [ ] Finalize the Design Specification document.

## 3. Implementation (Coding)
- [ ] Ensure Python 3.12+ and `uv` package manager are installed.
- [ ] Run `uv sync --group dev` to install development dependencies.
- [ ] Implement features as defined in the Design document.
- [ ] Create or update the `.env` configuration file from `.env.example`.
- [ ] Implement new endpoints and logic in `src/cloud_loader/`.
- [ ] Perform code reviews to ensure adherence to standards.

## 4. Testing
- [ ] Run unit and integration tests using `uv run pytest`.
- [ ] Test the application locally by running `uv run uvicorn cloud_loader.main:app --reload`.
- [ ] Verify file upload/download flows with the 6-character code.
- [ ] Verify concept tracking features and API key authentication.
- [ ] Log any defects and return to the Implementation phase to fix them.
- [ ] Obtain sign-off that all tests pass.

## 5. Deployment
- [ ] Prepare the production environment (e.g., a Linux server).
- [ ] Clone the repository or pull the latest changes on the production server.
- [ ] Run `uv sync` to install production dependencies.
- [ ] Configure the production `.env` file with appropriate API keys and domain settings.
- [ ] Deploy the application using systemd (`uv run cloud-loader`).
- [ ] Setup and verify the reverse proxy (e.g., Caddy on port 8080).
- [ ] Perform post-deployment smoke tests.

## 6. Maintenance
- [ ] Monitor application logs for errors or crashes.
- [ ] Verify that auto-deletion tasks for expired files and templates are running properly.
- [ ] Apply security patches or dependency updates as needed.
- [ ] Gather user feedback and report any bugs for the next development cycle.
