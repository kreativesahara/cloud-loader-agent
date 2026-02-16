import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path.cwd() / "src"))

try:
    from cloud_loader import dusk_worker
    print("Successfully imported dusk_worker")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)
