#!/usr/bin/env python3
"""
Example: Backup save file and modify gold amount
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration
SAVE_PATH = Path.home() / "AppData/Local/TeamMeowFork/MewGenics/save_file.sav"
BACKUP_DIR = Path("./backups")

# Create backup directory
BACKUP_DIR.mkdir(exist_ok=True)

# Generate backup filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = BACKUP_DIR / f"save_{timestamp}.sav"

# Backup save file
print(f"Creating backup: {backup_path}")
shutil.copy2(SAVE_PATH, backup_path)

# Modify gold to 9999
print("Modifying gold to 9999...")
result = subprocess.run(
    [sys.executable, "../mewgenics_save_tool.py", "modify", str(SAVE_PATH), "--gold", "9999"],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print("Success! Gold modified to 9999")
    print(f"Backup saved at: {backup_path}")
else:
    print(f"Error: {result.stderr}")
