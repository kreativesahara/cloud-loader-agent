# Quick Start Checklist for Cloud-Loader

This is a step-by-step checklist to set up, configure, and run the Cloud-Loader project on your machine.

## 1. Prerequisites
- [ ] Ensure **Python 3.12+** is installed on your system.
- [ ] Install the **[uv](https://docs.astral.sh/uv/)** package manager (e.g., `curl -LsSf https://astral.sh/uv/install.sh | sh` for Mac/Linux, or `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` for Windows).

## 2. Installation
- [ ] Open a terminal and navigate to the root directory of the project: `cd cloud-loader-agent`.
- [ ] Run `uv sync` to install standard dependencies.
- [ ] *(Optional)* If you plan to do development, run `uv sync --group dev` instead to install testing and formatting tools.

## 3. Configuration
- [ ] Copy the example environment file: `cp .env.example .env`.
- [ ] Open the new `.env` file in your editor.
- [ ] Set your basic server settings (e.g., `HOST=127.0.0.1`, `PORT=8080`).
- [ ] Set your API keys if you plan to use Concept Tracking:
  - `TAVILY_API_KEY=...`
  - `ANTHROPIC_API_KEY=...`

## 4. Running the Project
- [ ] **Production Mode**: Run `uv run cloud-loader` to start the server.
- [ ] **Development Mode**: Run `uv run uvicorn cloud_loader.main:app --reload` to start the server with auto-reload enabled.
- [ ] Open your browser and navigate to `http://127.0.0.1:8080` (or whatever `PORT` you configured).

## 5. Testing (Optional)
- [ ] Run `uv run pytest` to ensure all tests are passing.
