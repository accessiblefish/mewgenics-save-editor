#!/usr/bin/env python3
"""Build furniture JSON files from GameData GON and localized CSV files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..gamedata import (
    COMBINED_CSV,
    GAME_DATA_DIR,
    LOCALES,
    PUBLIC_DIR,
    load_localized_csv,
    localized_text,
    top_level_blocks,
    write_json,
)


RESERVED_KEYS = {
    "name",
    "desc",
    "set",
    "special",
    "can_be_rare",
    "removed",
}


def parse_scalar_lines(body: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or "{" in line or "}" in line or "[" in line or "]" in line:
            continue

        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s+(.+?)\s*$", line)
        if not match:
            continue

        key, raw_value = match.groups()
        if raw_value.lower() == "true":
            values[key] = True
        elif raw_value.lower() == "false":
            values[key] = False
        elif re.fullmatch(r"-?\d+", raw_value):
            values[key] = int(raw_value)
        else:
            values[key] = raw_value.strip('"')

    return values


def parse_furniture_gon(path: Path) -> dict[str, dict[str, Any]]:
    furniture = {}
    for furniture_id, body in top_level_blocks(path):
        scalars = parse_scalar_lines(body)
        entry: dict[str, Any] = {"id": furniture_id}
        effects = {}

        for key, value in scalars.items():
            if key in RESERVED_KEYS:
                entry[key] = value
            elif isinstance(value, int):
                effects[key] = value
            else:
                entry[key] = value

        if effects:
            entry["effects"] = effects

        furniture[furniture_id] = entry

    return furniture


def text_key(entry: dict[str, Any], field: str, furniture_id: str) -> str:
    value = entry.get(field)
    if isinstance(value, str) and value.startswith("FURNITURE_"):
        return value

    key_id = str(value or furniture_id).upper()
    if field == "name":
        return f"FURNITURE_NAME_{key_id}"
    return f"FURNITURE_DESC_{key_id}"


def build() -> None:
    output_dir = PUBLIC_DIR / "furniture"
    csv_data = load_localized_csv(COMBINED_CSV)
    base_furniture = parse_furniture_gon(GAME_DATA_DIR / "furniture_effects.gon")

    for locale in LOCALES:
        localized = {}
        for furniture_id, base_entry in base_furniture.items():
            entry = dict(base_entry)
            name = localized_text(csv_data, locale, text_key(base_entry, "name", furniture_id), "")
            desc = localized_text(csv_data, locale, text_key(base_entry, "desc", furniture_id), "")

            if name:
                entry["name"] = name
            if desc:
                entry["desc"] = desc
            else:
                entry["desc"] = ""

            localized[furniture_id] = entry

        write_json(output_dir / locale / "furniture.json", localized)
        if locale == "en":
            write_json(output_dir / "furniture.json", localized)

    print(f"furniture: {len(base_furniture)} items, {len(LOCALES)} locales")


if __name__ == "__main__":
    build()
