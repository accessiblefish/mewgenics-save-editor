#!/usr/bin/env python3
"""
Example: Find all cats with specific mutations
"""

import json
import subprocess
import sys
from pathlib import Path

SAVE_PATH = Path.home() / "AppData/Local/TeamMeowFork/MewGenics/save_file.sav"

# Export save to JSON
print("Exporting save file...")
result = subprocess.run(
    [sys.executable, "../mewgenics_save_tool.py", "export", str(SAVE_PATH)],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print(f"Error: {result.stderr}")
    sys.exit(1)

# Parse JSON
data = json.loads(result.stdout)

# Find cats with "Rock Bod" mutation
print("\n=== Cats with 'Rock Bod' mutation ===")
for key, cat in data['cats'].items():
    mutations = cat.get('mutations', [])
    for mut in mutations:
        body_part = mut.get('body_part', '')
        mut_id = mut.get('id', 0)
        if 'Body' in body_part and mut_id == 300:  # 300 = Rock Bod
            print(f"Cat {key}: {cat['name']} (Lv{cat['level']} {cat['cat_class']})")

# Find cats with high STR (>15)
print("\n=== Cats with STR > 15 ===")
for key, cat in data['cats'].items():
    stats = cat.get('stats', {})
    str_val = next((s['value'] for s in stats if s['name'] == 'STR'), 0)
    if str_val > 15:
        print(f"Cat {key}: {cat['name']} - STR: {str_val}")

# Find retired cats
print("\n=== Retired Cats ===")
for key, cat in data['cats'].items():
    if cat.get('retired', False):
        print(f"Cat {key}: {cat['name']} - {cat['cat_class']} Lv{cat['level']}")
