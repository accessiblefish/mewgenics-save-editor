#!/usr/bin/env python3
"""Build CLI game-data JSON from docs/GameData sources."""

from __future__ import annotations

from pathlib import Path

from .. import gamedata as game_data_common
from ..gamedata import load_localized_csv, localized_text, write_json
from . import abilities as abilities_builder
from . import furniture as furniture_builder
from . import items as items_builder
from . import mutations as mutations_builder


def configure_game_data_dir(game_data_dir: Path | None) -> None:
    if game_data_dir is None:
        return

    game_data_common.set_game_data_dir(game_data_dir)
    for module in (
        abilities_builder,
        furniture_builder,
        items_builder,
        mutations_builder,
    ):
        module.GAME_DATA_DIR = game_data_common.GAME_DATA_DIR
        module.COMBINED_CSV = game_data_common.COMBINED_CSV
    items_builder.ITEMS_DIR = game_data_common.GAME_DATA_DIR / "items"


def _build_abilities(locale: str = "en") -> dict[str, list[dict[str, str]]]:
    csv_data = load_localized_csv(game_data_common.COMBINED_CSV)
    output: dict[str, list[dict[str, str]]] = {}

    for gon_path in sorted((abilities_builder.GAME_DATA_DIR / "abilities").glob("*.gon")):
        abilities = abilities_builder.parse_active_gon(gon_path)
        key = abilities_builder.active_output_name(gon_path).removesuffix(".json")
        output[key] = [
            {
                "key": str(ability["key"]),
                "name": localized_text(csv_data, locale, ability["name_key"], str(ability["key"])),
                "desc": localized_text(csv_data, locale, ability["desc_key"], ""),
            }
            for ability in abilities
        ]

    disorders = abilities_builder.parse_passive_gon(
        abilities_builder.GAME_DATA_DIR / "passives" / "disorders.gon"
    )
    output["disorder"] = [
        {
            "key": str(disorder["key"]),
            "name": localized_text(csv_data, locale, disorder["name_key"], str(disorder["key"])),
            "desc": localized_text(csv_data, locale, disorder["desc_key"], ""),
        }
        for disorder in disorders
    ]

    for gon_path in sorted((abilities_builder.GAME_DATA_DIR / "passives").glob("*_passives.gon")):
        passives = abilities_builder.parse_passive_gon(gon_path)
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
    items = items_builder.localized_items(locale, csv_data, items_builder.parse_items())
    furniture = {}
    for furniture_id, entry in furniture_builder.parse_furniture_gon(
        furniture_builder.GAME_DATA_DIR / "furniture_effects.gon"
    ).items():
        localized = dict(entry)
        name_key = furniture_builder.text_key(entry, "name", furniture_id)
        desc_key = furniture_builder.text_key(entry, "desc", furniture_id)
        localized["name"] = localized_text(csv_data, locale, name_key, furniture_id)
        localized["desc"] = localized_text(csv_data, locale, desc_key, "")
        furniture[furniture_id] = localized

    mutations = mutations_builder.localized_mutations(
        locale, csv_data, mutations_builder.build_base_mutations()
    )
    abilities = _build_abilities(locale)

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
