#!/usr/bin/env python3
"""Build mutation JSON files from GameData GON and localized CSV files."""

from __future__ import annotations

import re
from pathlib import Path

from game_data_common import (
    COMBINED_CSV,
    GAME_DATA_DIR,
    LOCALES,
    PUBLIC_DIR,
    child_blocks,
    load_localized_csv,
    localized_text,
    quoted_value,
    top_level_blocks,
    write_json,
)


MUTATION_PARTS = (
    "body",
    "ears",
    "eyebrows",
    "eyes",
    "head",
    "legs",
    "mouth",
    "tail",
    "texture",
)

def parse_mutation_part(path: Path) -> tuple[str, dict[str, dict]]:
    top_blocks = top_level_blocks(path)
    if not top_blocks:
        raise ValueError(f"{path} has no mutation part block")

    part_name, part_body = top_blocks[0]
    entries = {}

    for mutation_id, body in child_blocks(part_body, r"-?\d+"):
        entries[mutation_id] = {
            "name": mutation_name_from_source(path, mutation_id),
            "_desc_key": quoted_value(body, "desc"),
        }

    return part_name, entries


def mutation_name_from_source(path: Path, mutation_id: str) -> str:
    pattern = re.compile(rf"^\s*{re.escape(mutation_id)}\s*\{{\s*//\s*(.+?)\s*$", re.MULTILINE)
    match = pattern.search(path.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else mutation_id


def build_base_mutations() -> dict[str, dict[str, dict]]:
    all_mutations = {}
    for part in MUTATION_PARTS:
        path = GAME_DATA_DIR / "mutation" / f"{part}.gon"
        if not path.exists():
            raise FileNotFoundError(path)
        parsed_part, entries = parse_mutation_part(path)
        all_mutations[parsed_part] = entries
    return all_mutations


def localized_mutations(
    locale: str,
    csv_data: dict[str, dict[str, str]] | None = None,
    base_mutations: dict[str, dict[str, dict]] | None = None,
) -> dict[str, dict[str, dict[str, str]]]:
    csv_data = csv_data or load_localized_csv(COMBINED_CSV)
    base_mutations = base_mutations or build_base_mutations()
    localized = {}

    for part, entries in base_mutations.items():
        localized[part] = {}
        for mutation_id, entry in entries.items():
            desc_key = entry.get("_desc_key")
            public_entry = {"name": entry["name"]}
            desc = localized_text(csv_data, locale, desc_key, "")
            if desc:
                public_entry["desc"] = desc
            localized[part][mutation_id] = public_entry

    return localized


def build() -> None:
    output_dir = PUBLIC_DIR / "mutations"
    csv_data = load_localized_csv(COMBINED_CSV)
    base_mutations = build_base_mutations()

    for locale in LOCALES:
        localized = localized_mutations(locale, csv_data, base_mutations)

        write_json(output_dir / locale / "all.json", localized)
        for part, entries in localized.items():
            write_json(output_dir / locale / f"{part}.json", {part: entries})

        if locale == "en":
            write_json(output_dir / "all.json", localized)

    total_entries = sum(len(entries) for entries in base_mutations.values())
    print(f"mutations: {len(base_mutations)} parts, {total_entries} entries, {len(LOCALES)} locales")


if __name__ == "__main__":
    build()
