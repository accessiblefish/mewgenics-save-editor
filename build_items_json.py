#!/usr/bin/env python3
"""Build item JSON files from GameData item GON and localized CSV files."""

from __future__ import annotations

from game_data_common import (
    COMBINED_CSV,
    GAME_DATA_DIR,
    LOCALES,
    PUBLIC_DIR,
    bare_value,
    load_localized_csv,
    localized_text,
    quoted_value,
    top_level_blocks,
    write_json,
)

ITEMS_DIR = GAME_DATA_DIR / "items"
WEBSITE_ITEM_FIELDS = ("kind", "rarity")


def parse_items() -> dict[str, dict[str, str | None]]:
    items: dict[str, dict[str, str | None]] = {}
    for path in sorted(ITEMS_DIR.glob("*.gon")):
        for item_id, body in top_level_blocks(path):
            entry: dict[str, str | None] = {
                "id": item_id,
                "_name_key": quoted_value(body, "name"),
                "_desc_key": quoted_value(body, "desc"),
            }
            for key in WEBSITE_ITEM_FIELDS:
                value = bare_value(body, key)
                if value is not None:
                    entry[key] = value
            items[item_id] = entry
    return items


def localized_items(
    locale: str,
    csv_data: dict[str, dict[str, str]] | None = None,
    base_items: dict[str, dict[str, str | None]] | None = None,
) -> dict[str, dict[str, str]]:
    csv_data = csv_data or load_localized_csv(COMBINED_CSV)
    base_items = base_items or parse_items()
    localized = {}

    for item_id, base_entry in base_items.items():
        entry: dict[str, str] = {
            key: value for key, value in base_entry.items() if not key.startswith("_")
        }
        entry["name"] = localized_text(
            csv_data, locale, base_entry.get("_name_key"), item_id
        )
        desc = localized_text(csv_data, locale, base_entry.get("_desc_key"), "")
        if desc:
            entry["desc"] = desc
        localized[item_id] = entry

    return localized


def build() -> None:
    output_dir = PUBLIC_DIR / "items"
    csv_data = load_localized_csv(COMBINED_CSV)
    base_items = parse_items()

    for locale in LOCALES:
        localized = localized_items(locale, csv_data, base_items)
        write_json(output_dir / locale / "items.json", localized)
        if locale == "en":
            write_json(output_dir / "items.json", localized)

    print(f"items: {len(base_items)} entries, {len(LOCALES)} locales")


if __name__ == "__main__":
    build()
