"""Core operations for the pure Python Mewgenics save CLI."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from . import parser as save_parser


REPO_ROOT = Path(__file__).resolve().parents[1]
GAMEDATA_DIR = REPO_ROOT / "gamedata"


def resolve_gamedata_dir(gamedata_dir: Path | None = None) -> Path:
    if gamedata_dir is not None:
        return gamedata_dir

    cwd_gamedata = Path.cwd() / "gamedata"
    if (cwd_gamedata / "items" / "items.json").exists():
        return cwd_gamedata
    return GAMEDATA_DIR


def read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def parse_save(path: Path) -> dict[str, Any]:
    return save_parser.parse_save_file(path.read_bytes())


def write_modified_save(
    source_path: Path,
    output_path: Path,
    *,
    basic_changes: dict[str, Any] | None = None,
    cat_changes: dict[int, dict[str, Any]] | None = None,
    furniture_changes: dict[str, Any] | None = None,
    item_changes: dict[str, Any] | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_parser.modify_save_file(
        source_path.read_bytes(),
        basic_changes or {},
        cat_changes or {},
        furniture_changes or {"added": [], "removed": []},
        item_changes or {},
        str(output_path),
    )


def _copy_if_same_output(source_path: Path, output_path: Path) -> Path:
    if source_path.resolve() == output_path.resolve():
        temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
        shutil.copyfile(source_path, temp_path)
        return temp_path
    return source_path


def load_item_ids(gamedata_dir: Path | None = None) -> set[str]:
    items = read_json(resolve_gamedata_dir(gamedata_dir) / "items" / "items.json")
    if not isinstance(items, dict):
        raise ValueError("gamedata/items/items.json must be a JSON object")
    return set(items)


def load_furniture_ids(gamedata_dir: Path | None = None) -> set[str]:
    furniture = read_json(resolve_gamedata_dir(gamedata_dir) / "furniture" / "furniture.json")
    if not isinstance(furniture, dict):
        raise ValueError("gamedata/furniture/furniture.json must be a JSON object")
    return set(furniture)


def apply_item_update(
    source_path: Path,
    output_path: Path,
    *,
    group: str,
    added_item_ids: list[str],
    removed_instance_ids: list[int],
    gamedata_dir: Path | None = None,
) -> None:
    item_ids = load_item_ids(gamedata_dir)
    unknown = [item_id for item_id in added_item_ids if item_id not in item_ids]
    if unknown:
        raise ValueError(f"unknown item id: {', '.join(unknown)}")

    source_for_edit = _copy_if_same_output(source_path, output_path)
    changes = {
        group: {
            "added": [{"item_id": item_id} for item_id in added_item_ids],
            "removed": removed_instance_ids,
        }
    }
    write_modified_save(source_for_edit, output_path, item_changes=changes)
    if source_for_edit != source_path:
        source_for_edit.unlink(missing_ok=True)


def apply_furniture_update(
    source_path: Path,
    output_path: Path,
    *,
    added: list[dict[str, Any]],
    removed_keys: list[int],
    gamedata_dir: Path | None = None,
) -> None:
    furniture_ids = load_furniture_ids(gamedata_dir)
    unknown = [str(item["furniture_id"]) for item in added if item["furniture_id"] not in furniture_ids]
    if unknown:
        raise ValueError(f"unknown furniture id: {', '.join(unknown)}")

    source_for_edit = _copy_if_same_output(source_path, output_path)
    write_modified_save(
        source_for_edit,
        output_path,
        furniture_changes={"added": added, "removed": removed_keys},
    )
    if source_for_edit != source_path:
        source_for_edit.unlink(missing_ok=True)


def parse_assignment(raw: str) -> tuple[str, int]:
    if "=" not in raw:
        raise ValueError(f"expected NAME=VALUE: {raw}")
    name, value = raw.split("=", 1)
    name = name.strip()
    if not name:
        raise ValueError(f"empty assignment name: {raw}")
    return name, int(value)


def apply_cat_update(
    source_path: Path,
    output_path: Path,
    *,
    cat_key: int,
    level: int | None = None,
    stats: list[str] | None = None,
    mutations: list[str] | None = None,
) -> None:
    parsed = parse_save(source_path)
    cat = next((item for item in parsed["cats"] if item["key"] == cat_key), None)
    if cat is None:
        raise ValueError(f"missing cat key: {cat_key}")

    changes: dict[str, Any] = {
        "_name_end": cat["_name_end"],
        "_level_offset": cat["_level_offset"],
        "_birth_day_offset": cat["_birth_day_offset"],
        "_stats_offset": cat["_stats_offset"],
        "_birth_day": cat["_birth_day"],
        "_current_day": parsed["basic"]["current_day"],
    }
    if level is not None:
        changes["level"] = level

    if stats:
        updated_stats = dict(cat["stats"])
        for raw in stats:
            name, value = parse_assignment(raw)
            normalized = name.upper()
            if normalized not in updated_stats:
                raise ValueError(f"unknown stat: {name}")
            updated_stats[normalized] = value
        changes["stats"] = updated_stats

    if mutations:
        updated_mutations = dict(cat["mutations"])
        for raw in mutations:
            name, value = parse_assignment(raw)
            updated_mutations[name] = value
        changes["mutations"] = updated_mutations

    source_for_edit = _copy_if_same_output(source_path, output_path)
    write_modified_save(source_for_edit, output_path, cat_changes={cat_key: changes})
    if source_for_edit != source_path:
        source_for_edit.unlink(missing_ok=True)


def export_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
