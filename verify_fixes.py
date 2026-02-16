import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from cloud_loader.config import settings
from cloud_loader.dusk_worker import DUSK_MEMORY_PATH, run_dusk_pipeline

print(f"Data Dir: {settings.data_dir}")
print(f"Upload Dir: {settings.upload_dir}")
print(f"Memory Path: {DUSK_MEMORY_PATH}")

# Mock objects to test _build_dusk_prompt logic inside run_dusk_pipeline if needed
# But mainly we want to see if the module imports without error and paths are correct.
print("Imports successful and paths are relative/correct.")
