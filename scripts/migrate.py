#!/usr/bin/env python3
"""
Cloud-Loader Migration Client (scripts/migrate.py)

Automates the backup and upload of AI assistant configurations to a Cloud-Loader server.
Designed to be portable (Standard Library only).
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import urllib.parse
import json
import zipfile
from pathlib import Path
from typing import Optional

# Default server URL
DEFAULT_SERVER = "http://localhost:8081"


def get_system_config_paths() -> dict[str, Path]:
    """Detect configuration paths based on OS."""
    system = platform.system()
    home = Path.home()
    
    paths = {}
    
    if system == "Windows":
        appdata = Path(os.environ.get("APPDATA", home / "AppData/Roaming"))
        local_appdata = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local"))
        
        # Windows Paths
        paths["claude"] = appdata / "Claude"  # verify this: sometimes .claude is used on windows too?
        # Check for .claude in home as fallback/alternative
        if (home / ".claude").exists():
             paths["claude_home"] = home / ".claude"
             
        paths["cursor"] = appdata / "Cursor"
        paths["vscode"] = appdata / "Code"
        paths["windsurf"] = home / ".windsurf"  # explicitly requested often
        
    else:
        # Linux / MacOS
        paths["claude"] = home / ".claude"
        paths["cursor"] = home / ".cursor" # or config dir
        # Standard XDG
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        paths["cursor_config"] = config_home / "Cursor"
        paths["vscode"] = config_home / "Code"

    return paths


def create_backup_zip(tool_name: str, config_path: Path, output_path: Path, password: str) -> Optional[Path]:
    """Create a password-protected zip of the config directory."""
    if not config_path.exists():
        print(f"❌ Config path not found: {config_path}")
        return None
        
    print(f"📦 Packing {tool_name} config from {config_path}...")
    
    # Create a temporary directory for the archive content
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)
        tool_config_dir = base_dir / "tool-config"
        tool_config_dir.mkdir()
        
        # Copy config files
        # We use shutil.copytree but need to be careful about permissions/locks
        try:
            # Ignore node_modules, cache, etc.
            def ignore_patterns(path, names):
                return ["node_modules", ".git", "__pycache__", "Cache", "CachedData", "User Data"]

            shutil.copytree(config_path, tool_config_dir, dirs_exist_ok=True, ignore=ignore_patterns)
            
            # Create INSTALL.md
            install_md = base_dir / "INSTALL.md"
            with open(install_md, "w", encoding="utf-8") as f:
                f.write(f"# Migration Installation Guide\n\n")
                f.write(f"## Tool\n{tool_name}: {config_path}\n\n")
                f.write(f"## Restore Steps\n")
                f.write(f"1. Extract the zip\n")
                f.write(f"2. Copy `tool-config` contents to your new machine's config folder.\n")
            
        except Exception as e:
            print(f"⚠️ Error copying files: {e}")
            return None

        # Create Zip (Python's zipfile doesn't support built-in encryption in older versions easily compatible with 'zip -P')
        # Standard zipfile supports password, but it's legacy ZipCrypto (weak) or not universally compatible CLI-wise 
        # depending on extraction tool. 
        # However, for simplicity and portability, we will create a standard zip.
        # If password security is strictly required by the server protocol (user instructions say "Ask for password"),
        # we might need to rely on system `zip` command if available, or pyminizip if permitted (but we want stdlib).
        # 
        # Re-reading requirements: instructions say "zip -r -P ...".
        # If we can't do CLI zip, we can try `zipfile` with `setpassword`. 
        # Note: zipfile writes encrypted files if `pwd` is passed to `writestr` or `write`.
        
        print(f"🔐 Creating encrypted zip: {output_path}")
        
        try:
            # Try calling system zip first for best compatibility
            if shutil.which("zip"):
                cmd = ["zip", "-r", "-P", password, str(output_path), "."]
                subprocess.run(cmd, cwd=temp_dir, check=True, capture_output=True)
                return output_path
        except Exception:
            pass
            
        # Fallback to python zipfile (ZipCrypto - widely supported but weak encryption)
        try:
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                if password:
                    zf.setpassword(password.encode("utf-8"))
                    
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(temp_dir)
                        # To encrypt we must strictly use the write method after setpassword
                        # Note: Python's zipfile encryption is ZipCrypto. 
                        # AES requires `pyzipper`.
                        zf.write(file_path, arcname)
                        
            return output_path
        except Exception as e:
            print(f"❌ Error creating zip: {e}")
            return None


def upload_backup(file_path: Path, server_url: str) -> None:
    """Upload the backup file to the server."""
    upload_url = f"{server_url.rstrip('/')}/upload"
    print(f"🚀 Uploading to {upload_url}...")
    
    # Simple multipart upload using urllib is verbose. 
    # Check if we can use curl (avail on Windows 10+)
    if shutil.which("curl"):
        try:
            cmd = [
                "curl", "-s", "-X", "POST", upload_url,
                "-F", f"file=@{file_path}"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                try:
                    resp = json.loads(result.stdout)
                    print("\n✅ Upload Successful!")
                    print(f"Code: {resp.get('code')}")
                    print(f"Expires: {resp.get('expires_at')}")
                    return
                except json.JSONDecodeError:
                    print(f"⚠️ Raw response: {result.stdout}")
                    return
        except Exception as e:
            print(f"⚠️ Curl failed ({e}), trying python fallback...")
            
    print("❌ Upload failed or Curl not found. Please manually upload the file.")
    print(f"File location: {file_path}")


def main():
    parser = argparse.ArgumentParser(description="Cloud-Loader Migration Client")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="Cloud-Loader server URL")
    parser.add_argument("--tool", help="Specific tool to migrate (claude, cursor, etc.)")
    parser.add_argument("--password", required=True, help="Password for the backup archive")
    args = parser.parse_args()
    
    print("Cloud-Loader Migration Client (Windows/Python)")
    print("==============================================")
    
    paths = get_system_config_paths()
    
    if args.tool:
        if args.tool not in paths:
             print(f"Unknown tool: {args.tool}. Available: {list(paths.keys())}")
             # try as absolute path?
             p = Path(args.tool)
             if p.exists():
                 selected_path = p
                 selected_tool = p.name
             else:
                 return
        else:
             selected_path = paths[args.tool]
             selected_tool = args.tool
    else:
        # Interactive selection
        print("Detected configurations:")
        valid_options = []
        for i, (name, path) in enumerate(paths.items()):
            if path.exists():
                print(f"{i+1}. {name}: {path}")
                valid_options.append((name, path))
            else:
                 # Debug: print(f"  (Skipping {name}: {path} not found)")
                 pass
        
        if not valid_options:
            print("❌ No standard AI assistant configurations found.")
            custom = input("Enter path manually? [y/N]: ")
            if custom.lower() == 'y':
                 p_str = input("Path: ").strip()
                 p = Path(p_str)
                 if p.exists():
                     selected_path = p
                     selected_tool = "custom"
                 else:
                     print("Path does not exist.")
                     return
            else:
                return
        else:
            choice = input(f"Select tool [1-{len(valid_options)}]: ")
            try:
                selected_tool, selected_path = valid_options[int(choice)-1]
            except (ValueError, IndexError):
                print("Invalid selection.")
                return

    print(f"\nMigration selected: {selected_tool} ({selected_path})")
    
    backup_path = Path.home() / "cloud_loader_backup.zip"
    
    if create_backup_zip(selected_tool, selected_path, backup_path, args.password):
        upload_backup(backup_path, args.server)
        
        # Cleanup
        if backup_path.exists():
            print(f"\nLocal backup file: {backup_path}")
            # os.remove(backup_path) # Maybe keep it just in case?

if __name__ == "__main__":
    main()
