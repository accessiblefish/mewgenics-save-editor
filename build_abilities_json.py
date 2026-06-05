#!/usr/bin/env python3
"""Build ability JSON files from GameData GON and localized CSV files."""

from __future__ import annotations

import re
from pathlib import Path

from game_data_common import (
    COMBINED_CSV,
    GAME_DATA_DIR,
    LOCALES,
    PUBLIC_DIR,
    bare_value,
    child_blocks,
    load_localized_csv,
    localized_text,
    quoted_value,
    top_level_blocks,
    write_json,
)


ABILITY_OUTPUTS = {
    "basic_attacks": "basic_attack.json",
    "basic_movement": "basic_move.json",
}


def meta_body(block_body: str) -> str:
    blocks = child_blocks(block_body, "meta")
    return blocks[0][1] if blocks else ""


def parse_active_gon(path: Path) -> list[dict[str, str | None]]:
    abilities = []
    for block_name, body in top_level_blocks(path):
        meta = meta_body(body)
        name_key = quoted_value(meta, "name")
        desc_key = quoted_value(meta, "desc")
        if name_key or desc_key:
            abilities.append(
                {
                    "key": block_name,
                    "name_key": name_key,
                    "desc_key": desc_key,
                }
            )
    return abilities


def parse_passive_gon(path: Path) -> list[dict[str, str | None]]:
    passives = []
    for block_name, body in top_level_blocks(path):
        name_key = quoted_value(body, "name")
        desc_key = quoted_value(body, "desc")
        level2_desc_key = None

        for level_name, level_body in child_blocks(body, r"\d+"):
            if level_name == "2":
                level2_desc_key = quoted_value(level_body, "desc")
                break

        if name_key or desc_key:
            passives.append(
                {
                    "key": block_name,
                    "name_key": name_key,
                    "desc_key": desc_key,
                    "level2_desc_key": level2_desc_key,
                }
            )
    return passives


def clean_level2_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", name) + "2"


def active_output_name(path: Path) -> str:
    stem = path.stem
    if stem in ABILITY_OUTPUTS:
        return ABILITY_OUTPUTS[stem]
    return f"{stem.removesuffix('_abilities')}_active.json"


def build_active_files(csv_data: dict[str, dict[str, str]], output_dir: Path) -> int:
    count = 0
    for gon_path in sorted((GAME_DATA_DIR / "abilities").glob("*.gon")):
        if gon_path.name.startswith("."):
            continue

        abilities = parse_active_gon(gon_path)
        output_name = active_output_name(gon_path)

        for locale in LOCALES:
            output = []
            for ability in abilities:
                key = str(ability["key"])
                name = localized_text(csv_data, locale, ability["name_key"], key)
                desc = localized_text(csv_data, locale, ability["desc_key"], "")
                output.append({"name": name, "desc": desc, "key": key})

            write_json(output_dir / locale / output_name, output)
        count += 1
    return count


def build_disorders(csv_data: dict[str, dict[str, str]], output_dir: Path) -> int:
    disorders = parse_passive_gon(GAME_DATA_DIR / "passives" / "disorders.gon")
    for locale in LOCALES:
        output = []
        for disorder in disorders:
            key = str(disorder["key"])
            name = localized_text(csv_data, locale, disorder["name_key"], key)
            desc = localized_text(csv_data, locale, disorder["desc_key"], "")
            output.append({"name": name, "desc": desc, "key": key})

        write_json(output_dir / locale / "disorder.json", output)
    return len(disorders)


def build_passive_files(csv_data: dict[str, dict[str, str]], output_dir: Path) -> int:
    count = 0
    for gon_path in sorted((GAME_DATA_DIR / "passives").glob("*_passives.gon")):
        passives = parse_passive_gon(gon_path)
        output_name = f"{gon_path.stem.removesuffix('_passives')}_passive.json"

        for locale in LOCALES:
            output = []
            for passive in passives:
                key = str(passive["key"])
                name = localized_text(csv_data, locale, passive["name_key"], key)
                desc = localized_text(csv_data, locale, passive["desc_key"], "")
                output.append({"name": name, "desc": desc, "key": key})

                level2_desc_key = passive["level2_desc_key"]
                if level2_desc_key:
                    output.append(
                        {
                            "name": clean_level2_name(name),
                            "desc": localized_text(csv_data, locale, level2_desc_key, ""),
                            "key": f"{key}2",
                        }
                    )

            write_json(output_dir / locale / output_name, output)
        count += 1
    return count


def build() -> None:
    output_dir = PUBLIC_DIR / "abilities"
    csv_data = load_localized_csv(COMBINED_CSV)

    active_files = build_active_files(csv_data, output_dir)
    disorder_count = build_disorders(csv_data, output_dir)
    passive_files = build_passive_files(csv_data, output_dir)

    print(
        f"abilities: {active_files} active files, {passive_files} passive files, "
        f"{disorder_count} disorders, {len(LOCALES)} locales"
    )


if __name__ == "__main__":
    build()
