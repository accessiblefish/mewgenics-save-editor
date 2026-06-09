# Mewgenics Save Tool — Technical Reference

> This document is the original technical deep-dive for the save-file parser.  
> For the current user-facing CLI guide, see `README.md`.

---

A Python command-line tool for parsing, editing, and analyzing Mewgenics save files.

## Features

- **Parse**: Display save file information (gold, food, cats, etc.)
- **List**: List all cats with their stats and abilities
- **Verify**: Check save file integrity
- **Compare**: Compare two save files to see changes
- **Modify**: Edit cat age, gold, food, and other data
- **Export**: Export save data to JSON format
- **Interactive**: Interactive shell for editing
- **Extract**: Extract cat binary data for analysis

## Installation

### Requirements

- Python 3.7+
- `lz4` library

```bash
pip install lz4
```

### Download

```bash
# Clone the repository
git clone https://github.com/yourusername/mewgenics-save-tool.git
cd mewgenics-save-tool

# Or download just the script
wget https://raw.githubusercontent.com/yourusername/mewgenics-save-tool/main/mewgenics_save_tool_en.py
```

## Usage

```bash
python mewgenics_save_tool_en.py <command> [options]
```

### Commands

#### Parse Save File

Display basic information about the save file:

```bash
python mewgenics_save_tool_en.py parse save_file.sav
```

Output:
```
======================================================================
[BASIC DATA]
  Gold:        1,170
  Food:        362
  Current Day: 252
  Save %:      80%
  Version:     19
  Total Cats:  21
======================================================================
```

#### List Cats

List all cats in the save file:

```bash
# Full information
python mewgenics_save_tool_en.py list save_file.sav

# Compact format
python mewgenics_save_tool_en.py list save_file.sav --compact
```

Output:
```
[CATS] (21 total)

  Key 608: Xilson | Room: Floor2_Large
    Class: Colorless, Lv0, Male, Age: 14 days
    Status: Active
    Stats: STR7 DEX7 CON7 INT7 SPD7 CHA7 LUCK7

  Key 633: Alyosha | Room: Floor2_Small
    ...
```

#### Verify Save File

Check save file integrity:

```bash
python mewgenics_save_tool_en.py verify save_file.sav
```

Output:
```
Verification PASSED - Save file looks good!
```

#### Compare Save Files

Compare two save files to see differences:

```bash
python mewgenics_save_tool_en.py compare old.sav new.sav
```

Output:
```
======================================================================
[BASIC DATA COMPARISON]
  Gold:    1,000 -> 1,500 (+500)
  Food:    300 -> 250 (-50)
  Day:     100 -> 105

[CAT COMPARISON]
  New cats: 2
    + Key 701: NewCat1
    + Key 702: NewCat2
  Removed cats: 1
    - Key 500: OldCat
======================================================================
```

#### Modify Save Data

Modify gold, food, or cat age:

```bash
# Modify basic data
python mewgenics_save_tool_en.py modify save_file.sav --gold 9999 --food 999

# Modify cat age
python mewgenics_save_tool_en.py modify save_file.sav --cat 123 --age 50

# Modify multiple values
python mewgenics_save_tool_en.py modify save_file.sav --gold 5000 --day 100 --cat 456 --age 30
```

#### Export to JSON

Export all save data to JSON format:

```bash
python mewgenics_save_tool_en.py export save_file.sav --output data.json

# Or print to stdout
python mewgenics_save_tool_en.py export save_file.sav
```

#### Interactive Mode

Interactive shell for editing:

```bash
python mewgenics_save_tool_en.py interactive save_file.sav
```

Commands in interactive mode:
- `list` - List all cats
- `cat <key>` - Show cat details
- `age <key> <days>` - Change cat age
- `gold <amount>` - Change gold
- `food <amount>` - Change food
- `save` - Save changes
- `quit` - Exit

#### Show Cat Details

Display detailed information about a specific cat:

```bash
python mewgenics_save_tool_en.py cat save_file.sav --key 123
```

Output:
```
======================================================================
[CAT 123]
  Name:     Xilson
  ID64:     1234567890
  Class:    Fighter
  Level:    12
  Sex:      Male
  Age:      45 days (born day 207)
  Room:     Floor1_Large
  Status:   Active

  [STATS]
    STR: 8
    DEX: 6
    CON: 7
    INT: 5
    SPD: 9
    CHA: 4
    LUCK: 6

  [ABILITIES]
    Move: DefaultMove
    Basic: Dash
    Active2: Big Punch
    Active3: Fire Punch
    ...

  [MUTATIONS]
    Body: Rock Bod (ID: 300)
    Tail: Scorpion Tail (ID: 302)
======================================================================
```

#### Extract Binary Data

Extract cat binary data for analysis:

```bash
# Extract all cats
python mewgenics_save_tool_en.py extract save_file.sav --output ./cats

# Extract specific cat
python mewgenics_save_tool_en.py extract save_file.sav --key 123 --output ./cats
```

## Save File Format

Mewgenics save files are **SQLite databases** with the following structure:

### Tables

#### `basic_data`
Stores basic game data:
- `house_gold` - Gold amount
- `house_food` - Food amount
- `current_day` - Current game day
- `save_file_percent` - Save completion percentage
- `save_version` - Save format version
- `save_file_cat` - Currently selected cat

#### `cats`
Stores cat data:
- `key` - Unique cat identifier (integer)
- `data` - Compressed cat BLOB (LZ4)

#### `files`
Stores additional game state:
- `house_state` - Room assignments for cats
- `adventure_state` - Cats currently on adventure
- `furniture` - Placed furniture data

### Cat BLOB Format

Cat data is stored as LZ4-compressed binary with the following structure:

```
[u32 uncompressed_size][lz4_compressed_data]
```

Or variant B:
```
[u32 uncompressed_size][u32 compressed_size][lz4_compressed_data]
```

#### Decompressed Cat Structure

| Offset | Type | Description |
|--------|------|-------------|
| 0x00 | u64 | Unknown |
| 0x04 | u64 | Cat ID64 |
| 0x0C | u32 | Name length (variant A) |
| 0x10 | u32 | Name length (variant B) |
| 0x14 | utf-16le | Cat name |
| ... | ... | Gender, class, level, stats |

### Abilities Storage

Abilities are stored as **u64-run format**:
```
[u64 length][ASCII string]...
```

Slots in order:
1. Move (DefaultMove)
2. Basic Attack
3. Active 2
4. Active 3
5. Active 4
6. Active 5
7. Passive 1
8. Passive 2
9. Disorder 1
10. Disorder 2

### Mutations Storage

Mutations are stored in a **T-array** at fixed offsets from base 0x44:

| T-Index | Body Part |
|---------|-----------|
| T[0] | Body |
| T[5] | Head |
| T[10] | Tail |
| T[15] | Left Leg |
| T[20] | Right Leg |
| T[25] | Left Arm |
| T[30] | Right Arm |
| T[35] | Left Eye |
| T[40] | Right Eye |
| T[45] | Left Eyebrow |
| T[50] | Right Eyebrow |
| T[55] | Left Ear |
| T[60] | Right Ear |
| T[65] | Mouth |

## Save File Locations

### Windows (Steam)
```
C:\Users\<Username>\AppData\Local\TeamMeowFork\MewGenics\save_file.sav
```

### macOS
```
~/Library/Application Support/TeamMeowFork/MewGenics/save_file.sav
```

### Linux (Steam/Proton)
```
~/.local/share/Steam/steamapps/compatdata/<appid>/pfx/drive_c/users/steamuser/AppData/Local/TeamMeowFork/MewGenics/save_file.sav
```

## Data Types Reference

### Classes

| ID | Class Name |
|----|------------|
| 0 | Colorless |
| 1 | Mage |
| 2 | Fighter |
| 3 | Hunter |
| 4 | Thief |
| 5 | Tank |
| 6 | Medic |
| 7 | Monk |
| 8 | Butcher |
| 9 | Druid |
| 10 | Tinkerer |
| 11 | Necromancer |
| 12 | Psychic |
| 13 | Jester |

### Sex/Gender

| ID | Sex |
|----|-----|
| 0 | Male |
| 1 | Female |
| 2 | Ditto |

### Stats

- **STR** - Strength
- **DEX** - Dexterity
- **CON** - Constitution
- **INT** - Intelligence
- **SPD** - Speed
- **CHA** - Charisma
- **LUCK** - Luck

## Example Scripts

### Batch Export All Cats

```bash
#!/bin/bash
SAVE_DIR="$HOME/AppData/Local/TeamMeowFork/MewGenics"
OUTPUT_DIR="./cat_exports"

mkdir -p "$OUTPUT_DIR"

for save in "$SAVE_DIR"/*.sav; do
    name=$(basename "$save" .sav)
    python mewgenics_save_tool_en.py export "$save" --output "$OUTPUT_DIR/$name.json"
done
```

### Find Cats with Specific Mutation

```python
import json

with open('export.json') as f:
    data = json.load(f)

# Find cats with "Rock Bod" mutation
for key, cat in data['cats'].items():
    for mut in cat.get('mutations', []):
        if 'Rock Bod' in mut.get('body_part', ''):
            print(f"Cat {key}: {cat['name']} has Rock Bod")
```

### Backup and Modify

```bash
#!/bin/bash
SAVE="$HOME/AppData/Local/TeamMeowFork/MewGenics/save_file.sav"
BACKUP="./backups/save_$(date +%Y%m%d_%H%M%S).sav"

# Create backup
mkdir -p ./backups
cp "$SAVE" "$BACKUP"

# Modify gold to 9999
python mewgenics_save_tool_en.py modify "$SAVE" --gold 9999

echo "Modified! Backup at: $BACKUP"
```

## Troubleshooting

### "Blob too small" Error

This usually means the cat data is corrupted or uses an unknown format. Try:
1. Loading the save in game and re-saving
2. Using the `extract` command to analyze the raw data

### Missing Cats

If cats are missing from the list:
1. Check if they are on adventure (`list` shows location)
2. Use `verify` command to check for parse errors
3. Some cats may be using a new compression variant

### Changes Not Appearing In-Game

1. Make sure the game is completely closed
2. Verify you're editing the correct save file
3. Some values (like level) may be calculated from other data

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

GNU Affero General Public License v3.0 - See LICENSE file for details

## Disclaimer

This tool is not affiliated with or endorsed by Team Meat. Use at your own risk - always backup your save files before editing.

## Acknowledgments

- Team Meat for creating Mewgenics
- The Mewgenics community for reverse engineering efforts
