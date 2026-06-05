#!/usr/bin/env python3
"""Build CLI game-data JSON from docs/GameData sources."""

from __future__ import annotations

from pathlib import Path

import build_abilities_json
import build_furniture_json
import build_items_json
import build_mutations_json
import game_data_common
from game_data_common import load_localized_csv, localized_text, write_json


def configure_game_data_dir(game_data_dir: Path | None) -> None:
    if game_data_dir is None:
        return

    game_data_common.set_game_data_dir(game_data_dir)
    for module in (
        build_abilities_json,
        build_furniture_json,
        build_items_json,
        build_mutations_json,
    ):
        module.GAME_DATA_DIR = game_data_common.GAME_DATA_DIR
        module.COMBINED_CSV = game_data_common.COMBINED_CSV
    build_items_json.ITEMS_DIR = game_data_common.GAME_DATA_DIR / "items"


def build_abilities(locale: str = "en") -> dict[str, list[dict[str, str]]]:
    csv_data = load_localized_csv(game_data_common.COMBINED_CSV)
    output: dict[str, list[dict[str, str]]] = {}

    for gon_path in sorted((build_abilities_json.GAME_DATA_DIR / "abilities").glob("*.gon")):
        abilities = build_abilities_json.parse_active_gon(gon_path)
        key = build_abilities_json.active_output_name(gon_path).removesuffix(".json")
        output[key] = [
            {
                "key": str(ability["key"]),
                "name": localized_text(csv_data, locale, ability["name_key"], str(ability["key"])),
                "desc": localized_text(csv_data, locale, ability["desc_key"], ""),
            }
            for ability in abilities
        ]

    disorders = build_abilities_json.parse_passive_gon(
        build_abilities_json.GAME_DATA_DIR / "passives" / "disorders.gon"
    )
    output["disorder"] = [
        {
            "key": str(disorder["key"]),
            "name": localized_text(csv_data, locale, disorder["name_key"], str(disorder["key"])),
            "desc": localized_text(csv_data, locale, disorder["desc_key"], ""),
        }
        for disorder in disorders
    ]

    for gon_path in sorted((build_abilities_json.GAME_DATA_DIR / "passives").glob("*_passives.gon")):
        passives = build_abilities_json.parse_passive_gon(gon_path)
        key = f"{gon_path.stem.removesuffix('_passives')}_passive"
        output[key] = [
            {
                "key": str(passive["key"]),
                "name": localized_text(csv_data, locale, passive["name_key"], str(passive["key"])),
                "desc": localized_text(csv_data, locale, passive["desc_key"], ""),
            }
            for passive in passives
        ]

    return output


def build_cli_game_data(
    output_dir: Path,
    locale: str = "en",
    game_data_dir: Path | None = None,
) -> dict[str, int]:
    configure_game_data_dir(game_data_dir)
    csv_data = load_localized_csv(game_data_common.COMBINED_CSV)
    items = build_items_json.localized_items(locale, csv_data, build_items_json.parse_items())
    furniture = {}
    for furniture_id, entry in build_furniture_json.parse_furniture_gon(
        build_furniture_json.GAME_DATA_DIR / "furniture_effects.gon"
    ).items():
        localized = dict(entry)
        name_key = build_furniture_json.text_key(entry, "name", furniture_id)
        desc_key = build_furniture_json.text_key(entry, "desc", furniture_id)
        localized["name"] = localized_text(csv_data, locale, name_key, furniture_id)
        localized["desc"] = localized_text(csv_data, locale, desc_key, "")
        furniture[furniture_id] = localized

    mutations = build_mutations_json.localized_mutations(
        locale, csv_data, build_mutations_json.build_base_mutations()
    )
    abilities = build_abilities(locale)

    write_json(output_dir / "items" / "items.json", items)
    write_json(output_dir / "furniture" / "furniture.json", furniture)
    write_json(output_dir / "mutations" / "all.json", mutations)
    for part, entries in mutations.items():
        write_json(output_dir / "mutations" / f"{part}.json", {part: entries})
    for name, payload in abilities.items():
        write_json(output_dir / "abilities" / f"{name}.json", payload)

    return {
        "abilities": len(abilities),
        "furniture": len(furniture),
        "items": len(items),
        "mutations": len(mutations),
    }


if __name__ == "__main__":
    build_cli_game_data(Path("data/game"))
