#!/usr/bin/env python3
"""
mewgenics_save_tool.py - Mewgenics Save File Editor

A command-line tool for parsing, editing, and analyzing Mewgenics save files.
Mewgenics save files are SQLite databases with LZ4-compressed cat data.

Commands:
    parse       Parse and display save file information
    list        List all cats in the save
    verify      Verify save file integrity
    compare     Compare two save files
    modify      Modify save data (age, gold, food, etc.)
    export      Export save data to JSON
    interactive Interactive editing mode
    cat         Show detailed info for a specific cat
    extract     Extract cat binary data for analysis

Usage:
    python mewgenics_save_tool.py parse save.sav
    python mewgenics_save_tool.py list save.sav --compact
    python mewgenics_save_tool.py verify save.sav
    python mewgenics_save_tool.py compare old.sav new.sav
    python mewgenics_save_tool.py modify save.sav --cat 123 --age 50
    python mewgenics_save_tool.py export save.sav --output data.json
    python mewgenics_save_tool.py interactive save.sav
    python mewgenics_save_tool.py cat save.sav --key 123
    python mewgenics_save_tool.py extract save.sav --output ./cats

Author: accessiblefish
License: MIT
"""

import sqlite3
import struct
import json
import sys
import argparse
import shutil
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict, field

try:
    import lz4.block
except ImportError:
    raise SystemExit("Missing dependency: lz4. Install with: pip install lz4")


# ==================== Constants ====================

SEX_MAP = {0: "Male", 1: "Female", 2: "Ditto"}
CAT_CLASSES = [
    "Colorless", "Mage", "Fighter", "Hunter", "Thief", "Tank",
    "Medic", "Monk", "Butcher", "Druid", "Tinkerer", "Necromancer",
    "Psychic", "Jester"
]
STAT_NAMES = ["STR", "DEX", "CON", "INT", "SPD", "CHA", "LUCK"]

# Mutation slot mapping: T-array index -> (display name, part_key)
MUTATION_SLOT_MAP = {
    0: ("Body", "body"),
    5: ("Head", "head"),
    10: ("Tail", "tail"),
    15: ("Leg-L", "leg"),
    20: ("Leg-R", "leg"),
    25: ("Arm-L", "arm"),
    30: ("Arm-R", "arm"),
    35: ("Eye-L", "eye"),
    40: ("Eye-R", "eye"),
    45: ("Eyebrow-L", "eyebrow"),
    50: ("Eyebrow-R", "eyebrow"),
    55: ("Ear-L", "ear"),
    60: ("Ear-R", "ear"),
    65: ("Mouth", "mouth"),
}

# Known mutation names database
MUTATION_NAMES = {
    "body": {
        300: "Rock Bod", 301: "Cactus Bod", 302: "Turtle Bod", 303: "Snail Bod",
        304: "Robot Body", 305: "Conjoined Bod", 306: "Skin & Bones", 307: "Udders",
        308: "Beach Bod", 309: "Maggot Bod", 310: "Puffball Bod", 311: "Square Bod",
        312: "Money Bag Bod", 313: "Spike Bod", 314: "Porcupine", 315: "Carapace",
        316: "Pangolin", 317: "Camel Hump", 318: "Egg Sack Back", 319: "Fractured Bod",
        320: "Brick Bod", 321: "Kitten Bod", 322: "Backpack", 323: "Fatty",
        324: "Eyeball", 700: "Gastroschisis", 701: "Deformed Ribcage", 702: "Malnurished",
        703: "Body Welts", 704: "Conjoined Body", 750: "spike body", 753: "mermaid body",
        758: "human head body", 900: "slender",
    },
    "head": {
        302: "Big brain", 311: "Money Bag head", 312: "Magnet Head", 314: "Pyramid Head",
        321: "Button Head",
    },
    "tail": {
        302: "Scorpion Tail", 311: "Thorn Tail", 312: "Holy Tail", 314: "Bone Tail",
        321: "Extra Head", 337: "Tail Feather",
    },
    "leg": {
        302: "Tentacles", 311: "Square Legs", 312: "Balloon Legs", 314: "Knife Legs",
        321: "Flippers", 337: "Floating Legs",
    },
    "arm": {},
    "eye": {
        302: "Pop Eyes", 311: "gecko eye", 312: "Metal Eyes", 314: "Dead Eyes",
        337: "Ice Eyes", 346: "Rock Eyes",
    },
    "eyebrow": {
        302: "Metal Brows", 311: "Stacked Brows", 314: "Holy Brows",
    },
    "ear": {
        302: "fishy",
    },
    "mouth": {
        302: "Flesh Kid", 310: "Lip Fillers", 311: "Leech Mouth", 312: "Bear Trap Mouth",
        314: "Gold Tooth", 321: "Zipper Mouth", 327: "Clown Lips",
    },
}


def get_mutation_name(mutation_id: int, part_key: str) -> str:
    """Get human-readable mutation name by ID and body part."""
    if mutation_id == 0:
        return "None"
    part_names = MUTATION_NAMES.get(part_key, {})
    return part_names.get(mutation_id, f"Mutation-{mutation_id}")


# ==================== Binary Utility Functions ====================

def u16_le(b: bytes, off: int) -> int:
    """Read unsigned 16-bit integer (little-endian)."""
    return struct.unpack_from("<H", b, off)[0]


def u32_le(b: bytes, off: int) -> int:
    """Read unsigned 32-bit integer (little-endian)."""
    return struct.unpack_from("<I", b, off)[0]


def u64_le(b: bytes, off: int) -> int:
    """Read unsigned 64-bit integer (little-endian)."""
    return struct.unpack_from("<Q", b, off)[0]


def i32_le(b: bytes, off: int) -> int:
    """Read signed 32-bit integer (little-endian)."""
    return struct.unpack_from("<i", b, off)[0]


def f64_le(b: bytes, off: int) -> float:
    """Read 64-bit float (little-endian)."""
    return struct.unpack_from("<d", b, off)[0]


# ==================== LZ4 Compression/Decompression ====================

def decompress_cat_blob(wrapped: bytes) -> Tuple[bytes, str]:
    """
    Decompress cat BLOB data.
    
    Save files use two variants:
    - Variant A: [u32 uncompressed_len][lz4_stream...]
    - Variant B: [u32 uncompressed_len][u32 compressed_len][lz4_stream]
    
    Returns:
        Tuple of (decompressed_data, variant)
    """
    if len(wrapped) < 4:
        raise ValueError("Blob too small")

    uncomp = u32_le(wrapped, 0)

    # Try Variant B first
    if len(wrapped) >= 8:
        comp_len = u32_le(wrapped, 4)
        if 0 < comp_len <= len(wrapped) - 8:
            stream = wrapped[8:8 + comp_len]
            try:
                dec = lz4.block.decompress(stream, uncompressed_size=uncomp)
                return dec, "B"
            except Exception:
                pass

    # Fall back to Variant A
    stream = wrapped[4:]
    dec = lz4.block.decompress(stream, uncompressed_size=uncomp)
    return dec, "A"


def recompress_cat_blob(dec: bytes, variant: str) -> bytes:
    """Recompress cat BLOB data."""
    comp = lz4.block.compress(dec, store_size=False)
    if variant == "A":
        return struct.pack("<I", len(dec)) + comp
    return struct.pack("<I", len(dec)) + struct.pack("<I", len(comp)) + comp


# ==================== Data Structures ====================

@dataclass
class StatInfo:
    """Cat stat information."""
    name: str
    value: int
    offset: int


@dataclass
class AbilityInfo:
    """Cat ability information."""
    slot: str
    name: str
    offset: int
    byte_len: int
    is_string_rec: bool = False


@dataclass
class MutationInfo:
    """Cat mutation information."""
    mutation_id: int
    body_part: int
    offset: int


@dataclass
class CatData:
    """Complete cat data structure."""
    key: int
    id64: int
    name: str
    sex: str
    age: int
    birth_day: int
    level: int
    cat_class: str
    retired: bool
    dead: bool
    donated: bool
    stats: List[StatInfo] = field(default_factory=list)
    abilities: List[AbilityInfo] = field(default_factory=list)
    mutations: List[MutationInfo] = field(default_factory=list)
    blob_size: int = 0
    variant: str = "A"
    location: str = ""
    room: str = ""
    raw_data: bytes = field(default_factory=bytes)

    # Raw offset information for saving modifications
    name_end: int = 0
    stats_offset: int = -1
    ability_run_start: int = -1
    ability_run_end: int = -1
    level_offset: int = -1
    birth_day_offset: int = -1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "key": self.key,
            "id64": self.id64,
            "name": self.name,
            "sex": self.sex,
            "age": self.age,
            "birth_day": self.birth_day,
            "level": self.level,
            "cat_class": self.cat_class,
            "retired": self.retired,
            "dead": self.dead,
            "donated": self.donated,
            "stats": [{"name": s.name, "value": s.value} for s in self.stats],
            "abilities": [{"slot": a.slot, "name": a.name} for a in self.abilities],
            "mutations": [{"id": m.mutation_id, "body_part": MUTATION_SLOT_MAP.get(m.body_part, (f"T[{m.body_part}]", ""))[0]} for m in self.mutations],
            "location": self.location,
            "room": self.room,
        }


@dataclass
class BasicData:
    """Save file basic data."""
    gold: int = 0
    food: int = 0
    current_day: int = 0
    save_percent: int = 0
    save_version: str = ""
    save_file_cat: str = ""


# ==================== Parsing Functions ====================

def detect_name_end_and_sex(dec: bytes) -> Tuple[int, int, str, str]:
    """
    Detect name end position and sex from cat data.
    
    Returns:
        Tuple of (name_length, name_end_offset, name_string, sex)
    """
    best = None

    for off_len in (0x0C, 0x10):
        if off_len + 4 > len(dec):
            continue
        nl = u32_le(dec, off_len)
        if not (0 <= nl <= 128):
            continue
        start = 0x14
        end = start + nl * 2
        if end > len(dec):
            continue

        name = dec[start:end].decode("utf-16le", errors="replace").rstrip("\x00")
        sex = "Unknown"
        score = 0
        off_a = end + 8
        off_b = end + 12
        if off_b + 2 <= len(dec):
            a = u16_le(dec, off_a)
            b = u16_le(dec, off_b)
            if a == b and a in SEX_MAP:
                sex = SEX_MAP[a]
                score += 4
            elif a in SEX_MAP or b in SEX_MAP:
                sex = SEX_MAP.get(a) or SEX_MAP.get(b) or "Unknown"
                score += 2

        if name:
            score += 1

        cand = (score, int(nl), int(end), name, sex)
        if best is None or cand[0] > best[0]:
            best = cand

    if best:
        return best[1], best[2], best[3], best[4]
    return 0, 0x14, "", "Unknown"


def read_status_flags(dec: bytes, name_end: int) -> Tuple[bool, bool, bool]:
    """
    Read cat status flags (retired, dead, donated).
    
    Returns:
        Tuple of (retired, dead, donated)
    """
    retired = dead = donated = False
    
    # Pattern 1: Check at offset 0x08
    if name_end + 4 <= len(dec):
        val = u32_le(dec, 0x08)
        if val in (0, 1, 2, 3):
            retired = bool(val & 1)
            dead = bool(val & 2)
    
    # Pattern 2: Check after name
    if name_end + 8 <= len(dec):
        marker = u32_le(dec, name_end + 4)
        if marker == 0x00000080:
            flags_off = name_end + 20
            if flags_off + 4 <= len(dec):
                flags = u32_le(dec, flags_off)
                retired = bool(flags & 1)
                dead = bool(flags & 2)
                donated = bool(flags & 4)
    
    return retired, dead, donated


def find_class_and_level(dec: bytes, name_end: int) -> Tuple[str, int, int, int, int]:
    """
    Find cat class, level and birth day.
    
    Returns:
        Tuple of (class_name, level, birth_day, level_offset, birth_day_offset)
    """
    cat_class = "Unknown"
    level = 0
    birth_day = 0
    level_off = -1
    birth_day_off = -1

    # Search pattern: 00 00 00 00 XX 00 00 00 YY 00 00 00
    # XX = class_id, YY = level
    pattern = re.compile(rb'\x00{4}(.{4})\x00{4}(.{4})')
    for m in pattern.finditer(dec):
        off = m.start()
        if 100 <= off <= 600:
            cls = u32_le(dec, off + 4)
            lvl = u32_le(dec, off + 12)
            if 0 <= cls < len(CAT_CLASSES) and 0 <= lvl <= 99:
                cat_class = CAT_CLASSES[cls]
                level = lvl
                level_off = off + 12
                birth_day_off = off - 4
                if birth_day_off >= 0:
                    birth_day = u32_le(dec, birth_day_off)
                break

    return cat_class, level, birth_day, level_off, birth_day_off


def find_stats(dec: bytes) -> Optional[Tuple[int, List[int]]]:
    """
    Find stats (STR, DEX, CON, INT, SPD, CHA, LUCK).
    
    Returns:
        Tuple of (offset, [stat_values]) or None if not found
    """
    n = len(dec)
    for off in range(0x80, min(n - 28, 0x200)):
        vals = [u32_le(dec, off + i * 4) for i in range(7)]
        if all(1 <= v <= 20 for v in vals):
            return off, vals
    return None


def parse_abilities_and_mutations(dec: bytes, name_end: int) -> Tuple[List[AbilityInfo], List[MutationInfo]]:
    """
    Parse abilities and mutations from cat data.
    
    Abilities are stored as u64-run format:
    [u64 length][ASCII string]...
    
    Mutations are stored in T-array at specific offsets.
    
    Returns:
        Tuple of (abilities_list, mutations_list)
    """
    abilities = []
    mutations = []
    n = len(dec)

    # Parse abilities from u64-run
    for start in range(name_end, min(n - 16, name_end + 512)):
        if dec[start:start + 12] == b'DefaultMove':
            break
    else:
        start = name_end

    if start < n - 8:
        items = []
        i = start
        while i + 8 <= n:
            ln = u64_le(dec, i)
            if ln < 0 or ln > 96 or i + 8 + ln > n:
                break
            if ln == 0:
                i += 8
                continue
            val = dec[i + 8:i + 8 + ln].decode("ascii", errors="replace")
            items.append((i, ln, val))
            i += 8 + ln
            if len(items) >= 14:
                break

        # Map items to ability slots
        ability_slots = [
            "Move", "Basic", "Active2", "Active3", "Active4", "Active5",
            "Passive1", "Passive2", "Disorder1", "Disorder2"
        ]
        for idx, (pos, ln, val) in enumerate(items[:10]):
            if idx < len(ability_slots):
                abilities.append(AbilityInfo(
                    slot=ability_slots[idx],
                    name=val,
                    offset=pos,
                    byte_len=ln
                ))

    # Parse mutations from T-array
    for idx, (slot_name, part_key) in MUTATION_SLOT_MAP.items():
        off = 0x44 + idx * 4
        if off + 4 <= len(dec):
            val = u32_le(dec, off)
            if val != 0:
                mutations.append(MutationInfo(
                    mutation_id=val,
                    body_part=idx,
                    offset=off
                ))

    return abilities, mutations


def parse_house_state(blob: bytes) -> List[Tuple[int, str]]:
    """
    Parse house_state table to get cats and their room assignments.
    
    Returns:
        List of (cat_key, room_name) tuples
    """
    if len(blob) < 8:
        return []

    ver = u32_le(blob, 0)
    cnt = u32_le(blob, 4)

    if ver != 0 or cnt > 512:
        return []

    off = 8
    cats = []
    for _ in range(cnt):
        if off + 16 > len(blob):
            break
        key = u32_le(blob, off)
        room_len = u64_le(blob, off + 8)
        name_off = off + 16
        if name_off + room_len > len(blob):
            break
        room = blob[name_off:name_off + room_len].decode("ascii", errors="replace")
        d_off = name_off + room_len
        if d_off + 24 > len(blob):
            break
        cats.append((key, room))
        off = d_off + 24

    return cats


def parse_adventure_state(blob: bytes) -> List[int]:
    """
    Parse adventure_state table to get cats on adventure.
    
    Returns:
        List of cat keys
    """
    if not blob or len(blob) < 8:
        return []

    ver = u32_le(blob, 0)
    cnt = u32_le(blob, 4)

    if cnt > 8:
        return []

    off = 8
    keys = []
    for _ in range(cnt):
        if off + 8 > len(blob):
            break
        v = u64_le(blob, off)
        off += 8
        hi = (v >> 32) & 0xFFFFFFFF
        lo = v & 0xFFFFFFFF
        key = int(hi if hi != 0 else lo)
        if 0 < key <= 1000000:
            keys.append(key)

    return keys


# ==================== Save File Operations ====================

class SaveFile:
    """Main class for handling Mewgenics save files."""

    def __init__(self, path: str):
        """Load save file from path."""
        self.path = Path(path)
        self.conn = sqlite3.connect(str(self.path))
        self.cats: Dict[int, CatData] = {}
        self.basic = BasicData()
        self._load_basic_data()
        self._load_cats()

    def _load_basic_data(self):
        """Load basic save data (gold, food, day, etc.)."""
        cursor = self.conn.execute("SELECT key, value FROM basic_data")
        for row in cursor:
            key, val = row
            if key == 'house_gold':
                self.basic.gold = int(val)
            elif key == 'house_food':
                self.basic.food = int(val)
            elif key == 'current_day':
                self.basic.current_day = int(val)
            elif key == 'save_file_percent':
                self.basic.save_percent = int(val)
            elif key == 'save_version':
                self.basic.save_version = val
            elif key == 'save_file_cat':
                self.basic.save_file_cat = val

    def _load_cats(self):
        """Load all cats from save file."""
        # Get cat locations
        hs_row = self.conn.execute("SELECT data FROM files WHERE key='house_state'").fetchone()
        house_cats = parse_house_state(bytes(hs_row[0])) if hs_row and hs_row[0] else []
        
        adv_row = self.conn.execute("SELECT data FROM files WHERE key='adventure_state'").fetchone()
        adv_keys = parse_adventure_state(bytes(adv_row[0])) if adv_row and adv_row[0] else []

        # Build location map
        location_map = {key: room for key, room in house_cats}
        for key in adv_keys:
            if key not in location_map:
                location_map[key] = "(Adventure)"

        # Load each cat
        cursor = self.conn.execute("SELECT key, data FROM cats")
        for row in cursor:
            key, blob = row
            try:
                cat = self._parse_cat(key, bytes(blob))
                cat.location = location_map.get(key, "(None)")
                cat.room = cat.location
                self.cats[key] = cat
            except Exception as e:
                print(f"Warning: Failed to parse cat {key}: {e}")

    def _parse_cat(self, key: int, blob: bytes) -> CatData:
        """Parse a single cat from BLOB data."""
        dec, variant = decompress_cat_blob(blob)
        
        name_len, name_end, name, sex = detect_name_end_and_sex(dec)
        retired, dead, donated = read_status_flags(dec, name_end)
        cat_class, level, birth_day, level_off, birth_day_off = find_class_and_level(dec, name_end)
        
        age = max(0, self.basic.current_day - birth_day) if birth_day > 0 else 0
        
        stats_result = find_stats(dec)
        stats = []
        if stats_result:
            stats_off, stat_values = stats_result
            for i, val in enumerate(stat_values):
                stats.append(StatInfo(name=STAT_NAMES[i], value=val, offset=stats_off + i * 4))
        
        abilities, mutations = parse_abilities_and_mutations(dec, name_end)

        return CatData(
            key=key,
            id64=u64_le(dec, 4),
            name=name,
            sex=sex,
            age=age,
            birth_day=birth_day,
            level=level,
            cat_class=cat_class,
            retired=retired,
            dead=dead,
            donated=donated,
            stats=stats,
            abilities=abilities,
            mutations=mutations,
            blob_size=len(blob),
            variant=variant,
            raw_data=dec,
            name_end=name_end,
            level_offset=level_off,
            birth_day_offset=birth_day_off,
        )

    def modify_cat_age(self, key: int, new_age: int) -> bool:
        """Modify a cat's age by changing its birth day."""
        if key not in self.cats:
            return False
        
        cat = self.cats[key]
        if cat.birth_day_offset < 0:
            return False

        new_birth_day = self.basic.current_day - new_age
        
        # Modify raw data
        dec = bytearray(cat.raw_data)
        struct.pack_into("<I", dec, cat.birth_day_offset, new_birth_day)
        
        # Recompress
        new_blob = recompress_cat_blob(bytes(dec), cat.variant)
        
        # Update database
        self.conn.execute("UPDATE cats SET data = ? WHERE key = ?", (new_blob, key))
        self.conn.commit()
        
        # Update cached data
        cat.birth_day = new_birth_day
        cat.age = new_age
        cat.raw_data = bytes(dec)
        
        return True

    def modify_basic_data(self, gold: Optional[int] = None, food: Optional[int] = None,
                          day: Optional[int] = None, percent: Optional[int] = None):
        """Modify basic save data."""
        if gold is not None:
            self.conn.execute("INSERT OR REPLACE INTO basic_data VALUES (?, ?)",
                            ('house_gold', str(gold)))
            self.basic.gold = gold
        if food is not None:
            self.conn.execute("INSERT OR REPLACE INTO basic_data VALUES (?, ?)",
                            ('house_food', str(food)))
            self.basic.food = food
        if day is not None:
            self.conn.execute("INSERT OR REPLACE INTO basic_data VALUES (?, ?)",
                            ('current_day', str(day)))
            self.basic.current_day = day
        if percent is not None:
            self.conn.execute("INSERT OR REPLACE INTO basic_data VALUES (?, ?)",
                            ('save_file_percent', str(percent)))
            self.basic.save_percent = percent
        self.conn.commit()

    def save_copy(self, output_path: str):
        """Save a copy of the current database to a new file."""
        # Close connection before copying
        self.conn.close()
        shutil.copy2(self.path, output_path)
        # Reopen connection
        self.conn = sqlite3.connect(str(self.path))

    def export_json(self) -> Dict[str, Any]:
        """Export all save data to a dictionary."""
        return {
            "basic": asdict(self.basic),
            "cats": {k: v.to_dict() for k, v in self.cats.items()}
        }

    def close(self):
        """Close the database connection."""
        self.conn.close()


# ==================== Command Implementations ====================

def cmd_parse(args):
    """Parse and display save file information."""
    save = SaveFile(args.sav_path)
    
    print("=" * 70)
    print("[BASIC DATA]")
    print(f"  Gold:        {save.basic.gold:,}")
    print(f"  Food:        {save.basic.food:,}")
    print(f"  Current Day: {save.basic.current_day}")
    print(f"  Save %:      {save.basic.save_percent}%")
    print(f"  Version:     {save.basic.save_version}")
    print(f"  Total Cats:  {len(save.cats)}")
    print("=" * 70)
    
    save.close()


def cmd_list(args):
    """List all cats in the save file."""
    save = SaveFile(args.sav_path)
    
    print(f"\n[CATS] ({len(save.cats)} total)\n")
    
    for key, cat in sorted(save.cats.items()):
        status = []
        if cat.retired:
            status.append("Retired")
        if cat.dead:
            status.append("Dead")
        if cat.donated:
            status.append("Donated")
        
        status_str = ",".join(status) if status else "Active"
        
        if args.compact:
            print(f"  Key {key}: {cat.name or '(Unnamed)'} | {cat.cat_class} Lv{cat.level}")
        else:
            print(f"  Key {key}: {cat.name or '(Unnamed)'} | Room: {cat.room}")
            print(f"    Class: {cat.cat_class}, Lv{cat.level}, {cat.sex}, Age: {cat.age} days")
            print(f"    Status: {status_str}")
            if cat.stats:
                stats_str = " ".join(f"{s.name}{s.value}" for s in cat.stats)
                print(f"    Stats: {stats_str}")
            print()
    
    save.close()


def cmd_verify(args):
    """Verify save file integrity."""
    save = SaveFile(args.sav_path)
    
    errors = []
    
    # Check for cats that failed to parse
    cursor = save.conn.execute("SELECT key FROM cats")
    all_keys = {row[0] for row in cursor}
    parsed_keys = set(save.cats.keys())
    missing = all_keys - parsed_keys
    
    if missing:
        errors.append(f"Failed to parse {len(missing)} cats: {sorted(missing)[:5]}...")
    
    # Check for invalid data
    for key, cat in save.cats.items():
        if not cat.name and cat.level == 0:
            errors.append(f"Cat {key}: Possibly corrupted (no name, level 0)")
    
    if errors:
        print("Verification FAILED:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("Verification PASSED - Save file looks good!")
    
    save.close()


def cmd_compare(args):
    """Compare two save files."""
    save1 = SaveFile(args.path1)
    save2 = SaveFile(args.path2)
    
    print("=" * 70)
    print("[BASIC DATA COMPARISON]")
    print(f"  Gold:    {save1.basic.gold:,} -> {save2.basic.gold:,} ({save2.basic.gold - save1.basic.gold:+})")
    print(f"  Food:    {save1.basic.food:,} -> {save2.basic.food:,} ({save2.basic.food - save1.basic.food:+})")
    print(f"  Day:     {save1.basic.current_day} -> {save2.basic.current_day}")
    
    print("\n[CAT COMPARISON]")
    keys1 = set(save1.cats.keys())
    keys2 = set(save2.cats.keys())
    
    added = keys2 - keys1
    removed = keys1 - keys2
    
    if added:
        print(f"  New cats: {len(added)}")
        for k in sorted(added)[:5]:
            print(f"    + Key {k}: {save2.cats[k].name}")
    
    if removed:
        print(f"  Removed cats: {len(removed)}")
        for k in sorted(removed)[:5]:
            print(f"    - Key {k}: {save1.cats[k].name}")
    
    print("=" * 70)
    
    save1.close()
    save2.close()


def cmd_modify(args):
    """Modify save file data."""
    save = SaveFile(args.sav_path)
    
    modified = False
    
    # Modify basic data
    if any([args.gold is not None, args.food is not None, 
            args.day is not None, args.percent is not None]):
        save.modify_basic_data(
            gold=args.gold,
            food=args.food,
            day=args.day,
            percent=args.percent
        )
        modified = True
        print("Modified basic data")
    
    # Modify cat
    if args.cat_key is not None:
        if args.cat_key not in save.cats:
            print(f"Error: Cat {args.cat_key} not found")
            save.close()
            return
        
        if args.age is not None:
            if save.modify_cat_age(args.cat_key, args.age):
                print(f"Modified cat {args.cat_key} age to {args.age}")
                modified = True
            else:
                print(f"Failed to modify cat {args.cat_key} age")
    
    if modified:
        print(f"Changes saved to: {args.sav_path}")
    else:
        print("No changes made")
    
    save.close()


def cmd_export(args):
    """Export save data to JSON."""
    save = SaveFile(args.sav_path)
    
    data = save.export_json()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Exported to: {args.output}")
    else:
        print(json.dumps(data, indent=2))
    
    save.close()


def cmd_interactive(args):
    """Interactive editing mode."""
    save = SaveFile(args.sav_path)
    
    print("=" * 70)
    print("Interactive Mewgenics Save Editor")
    print("=" * 70)
    print(f"\nSave file: {args.sav_path}")
    print(f"Cats: {len(save.cats)}")
    print("\nCommands:")
    print("  list              - List all cats")
    print("  cat <key>         - Show cat details")
    print("  age <key> <days>  - Change cat age")
    print("  gold <amount>     - Change gold")
    print("  food <amount>     - Change food")
    print("  save              - Save changes")
    print("  quit              - Exit")
    print()
    
    modified = False
    
    while True:
        try:
            cmd = input("> ").strip().split()
            if not cmd:
                continue
            
            if cmd[0] == "quit":
                break
            elif cmd[0] == "list":
                for key, cat in sorted(save.cats.items()):
                    print(f"  {key}: {cat.name or '(Unnamed)'} (Lv{cat.level} {cat.cat_class})")
            elif cmd[0] == "cat" and len(cmd) > 1:
                key = int(cmd[1])
                if key in save.cats:
                    cat = save.cats[key]
                    print(f"\nKey: {cat.key}")
                    print(f"Name: {cat.name}")
                    print(f"Class: {cat.cat_class} Lv{cat.level}")
                    print(f"Sex: {cat.sex}")
                    print(f"Age: {cat.age} days")
                    print(f"Room: {cat.room}")
                else:
                    print(f"Cat {key} not found")
            elif cmd[0] == "age" and len(cmd) > 2:
                key = int(cmd[1])
                age = int(cmd[2])
                if save.modify_cat_age(key, age):
                    print(f"Changed cat {key} age to {age}")
                    modified = True
                else:
                    print("Failed to change age")
            elif cmd[0] == "gold" and len(cmd) > 1:
                gold = int(cmd[1])
                save.modify_basic_data(gold=gold)
                print(f"Changed gold to {gold}")
                modified = True
            elif cmd[0] == "food" and len(cmd) > 1:
                food = int(cmd[1])
                save.modify_basic_data(food=food)
                print(f"Changed food to {food}")
                modified = True
            elif cmd[0] == "save":
                print("Changes saved")
                modified = False
            else:
                print("Unknown command")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    if modified:
        confirm = input("Save changes? (y/n): ")
        if confirm.lower() == 'y':
            print("Changes saved")
    
    save.close()


def cmd_cat(args):
    """Show detailed info for a specific cat."""
    save = SaveFile(args.sav_path)
    
    if args.cat_key not in save.cats:
        print(f"Error: Cat {args.cat_key} not found")
        save.close()
        return
    
    cat = save.cats[args.cat_key]
    
    print("=" * 70)
    print(f"[CAT {cat.key}]")
    print(f"  Name:     {cat.name or '(Unnamed)'}")
    print(f"  ID64:     {cat.id64}")
    print(f"  Class:    {cat.cat_class}")
    print(f"  Level:    {cat.level}")
    print(f"  Sex:      {cat.sex}")
    print(f"  Age:      {cat.age} days (born day {cat.birth_day})")
    print(f"  Room:     {cat.room}")
    print(f"  Status:   {'Retired' if cat.retired else 'Active'}{' | Dead' if cat.dead else ''}{' | Donated' if cat.donated else ''}")
    
    if cat.stats:
        print(f"\n  [STATS]")
        for s in cat.stats:
            print(f"    {s.name}: {s.value}")
    
    if cat.abilities:
        print(f"\n  [ABILITIES]")
        for a in cat.abilities:
            print(f"    {a.slot}: {a.name}")
    
    if cat.mutations:
        print(f"\n  [MUTATIONS]")
        for m in cat.mutations:
            part_name = MUTATION_SLOT_MAP.get(m.body_part, (f"T[{m.body_part}]", ""))[0]
            mut_name = get_mutation_name(m.mutation_id, MUTATION_SLOT_MAP.get(m.body_part, ("", ""))[1])
            print(f"    {part_name}: {mut_name} (ID: {m.mutation_id})")
    
    print("=" * 70)
    save.close()


def cmd_extract(args):
    """Extract cat binary data for analysis."""
    save = SaveFile(args.sav_path)
    
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    if args.cat_key:
        # Extract specific cat
        if args.cat_key not in save.cats:
            print(f"Error: Cat {args.cat_key} not found")
            save.close()
            return
        cats_to_extract = {args.cat_key: save.cats[args.cat_key]}
    else:
        # Extract all cats
        cats_to_extract = save.cats
    
    extracted = []
    for key, cat in cats_to_extract.items():
        bin_path = output_dir / f"cat_{key}.bin"
        with open(bin_path, 'wb') as f:
            f.write(cat.raw_data)
        extracted.append((key, len(cat.raw_data), bin_path))
        print(f"Extracted cat {key} ({len(cat.raw_data)} bytes) -> {bin_path}")
    
    print(f"\nTotal extracted: {len(extracted)} cats")
    save.close()


# ==================== Main Entry Point ====================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Mewgenics Save File Editor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s parse save.sav
  %(prog)s list save.sav --compact
  %(prog)s verify save.sav
  %(prog)s compare old.sav new.sav
  %(prog)s modify save.sav --cat 123 --age 50
  %(prog)s export save.sav --output data.json
  %(prog)s interactive save.sav
  %(prog)s cat save.sav --key 123
  %(prog)s extract save.sav --output ./cats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # parse command
    parse_parser = subparsers.add_parser("parse", help="Parse and display save info")
    parse_parser.add_argument("sav_path", help="Path to save file")
    parse_parser.set_defaults(func=cmd_parse)
    
    # list command
    list_parser = subparsers.add_parser("list", help="List all cats")
    list_parser.add_argument("sav_path", help="Path to save file")
    list_parser.add_argument("--compact", action="store_true", help="Compact output")
    list_parser.set_defaults(func=cmd_list)
    
    # verify command
    verify_parser = subparsers.add_parser("verify", help="Verify save integrity")
    verify_parser.add_argument("sav_path", help="Path to save file")
    verify_parser.set_defaults(func=cmd_verify)
    
    # compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two saves")
    compare_parser.add_argument("path1", help="First save file")
    compare_parser.add_argument("path2", help="Second save file")
    compare_parser.set_defaults(func=cmd_compare)
    
    # modify command
    modify_parser = subparsers.add_parser("modify", help="Modify save data")
    modify_parser.add_argument("sav_path", help="Path to save file")
    modify_parser.add_argument("--gold", type=int, help="Set gold amount")
    modify_parser.add_argument("--food", type=int, help="Set food amount")
    modify_parser.add_argument("--day", type=int, help="Set current day")
    modify_parser.add_argument("--percent", type=int, help="Set completion percent")
    modify_parser.add_argument("--cat", dest="cat_key", type=int, help="Cat key to modify")
    modify_parser.add_argument("--age", type=int, help="New age for cat")
    modify_parser.set_defaults(func=cmd_modify)
    
    # export command
    export_parser = subparsers.add_parser("export", help="Export to JSON")
    export_parser.add_argument("sav_path", help="Path to save file")
    export_parser.add_argument("-o", "--output", help="Output JSON file")
    export_parser.set_defaults(func=cmd_export)
    
    # interactive command
    interactive_parser = subparsers.add_parser("interactive", help="Interactive mode")
    interactive_parser.add_argument("sav_path", help="Path to save file")
    interactive_parser.set_defaults(func=cmd_interactive)
    
    # cat command
    cat_parser = subparsers.add_parser("cat", help="Show cat details")
    cat_parser.add_argument("sav_path", help="Path to save file")
    cat_parser.add_argument("-k", "--key", dest="cat_key", type=int, required=True, help="Cat key")
    cat_parser.set_defaults(func=cmd_cat)
    
    # extract command
    extract_parser = subparsers.add_parser("extract", help="Extract cat binary data")
    extract_parser.add_argument("sav_path", help="Path to save file")
    extract_parser.add_argument("-k", "--key", dest="cat_key", type=int, default=None, help="Specific cat key")
    extract_parser.add_argument("-o", "--output", default="extracted_cats", help="Output directory")
    extract_parser.set_defaults(func=cmd_extract)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        args.func(args)
    except FileNotFoundError as e:
        print(f"Error: Save file not found: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
