#!/usr/bin/env python3
"""Pure Python CLI for reading and editing Mewgenics save files."""

from __future__ import annotations

import argparse
from pathlib import Path

from .core import (
    apply_cat_update,
    apply_furniture_update,
    apply_item_update,
    export_json,
    parse_save,
)
from .scripts.rebuild import build_cli_game_data

DEFAULT_GAMEDATA_DIR = Path.cwd() / "gamedata"


def cmd_parse(args: argparse.Namespace) -> None:
    data = parse_save(Path(args.save))
    if args.json:
        print(export_json(data))
        return

    basic = data["basic"]
    print(f"cats: {data['total_cats']}")
    print(f"furniture: {data['total_furniture']}")
    print(
        "items: "
        f"storage={len(data['items']['storage'])} "
        f"trash={len(data['items']['trash'])} "
        f"backpack={len(data['items']['backpack'])}"
    )
    print(f"day: {basic['current_day']}")
    print(f"gold: {basic['house_gold']}")
    print(f"food: {basic['house_food']}")


def cmd_game_data_rebuild(args: argparse.Namespace) -> None:
    counts = build_cli_game_data(
        Path(args.output_dir),
        args.locale,
        Path(args.source_game_data_dir) if args.source_game_data_dir else None,
    )
    print(
        " ".join(
            f"{name}={count}"
            for name, count in sorted(counts.items())
        )
    )


def cmd_item_add(args: argparse.Namespace) -> None:
    added = [args.item_id] if args.item_id else []
    apply_item_update(
        Path(args.save),
        Path(args.output),
        group=args.group,
        added_item_ids=added,
        removed_instance_ids=args.remove_instance_id or [],
        gamedata_dir=Path(args.gamedata_dir) if args.gamedata_dir else None,
    )
    print(str(Path(args.output)))


def cmd_item_remove(args: argparse.Namespace) -> None:
    apply_item_update(
        Path(args.save),
        Path(args.output),
        group=args.group,
        added_item_ids=[],
        removed_instance_ids=args.instance_id,
        gamedata_dir=Path(args.gamedata_dir) if args.gamedata_dir else None,
    )
    print(str(Path(args.output)))


def cmd_furniture_add(args: argparse.Namespace) -> None:
    added = [
        {
            "key": args.key,
            "furniture_id": args.furniture_id,
            "x": args.x,
            "y": args.y,
            "room": args.room,
        }
    ]
    apply_furniture_update(
        Path(args.save),
        Path(args.output),
        added=added,
        removed_keys=args.remove_key or [],
        gamedata_dir=Path(args.gamedata_dir) if args.gamedata_dir else None,
    )
    print(str(Path(args.output)))


def cmd_furniture_remove(args: argparse.Namespace) -> None:
    apply_furniture_update(
        Path(args.save),
        Path(args.output),
        added=[],
        removed_keys=args.key,
        gamedata_dir=Path(args.gamedata_dir) if args.gamedata_dir else None,
    )
    print(str(Path(args.output)))


def cmd_cat_set(args: argparse.Namespace) -> None:
    apply_cat_update(
        Path(args.save),
        Path(args.output),
        cat_key=args.cat_key,
        level=args.level,
        stats=args.stat or [],
        mutations=args.mutation or [],
    )
    print(str(Path(args.output)))


def add_output_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", required=True, help="Output save path")


def add_gamedata_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--gamedata-dir",
        help="Path to generated JSON gamedata. Defaults to ./gamedata.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_parser = subparsers.add_parser("parse")
    parse_parser.add_argument("save")
    parse_parser.add_argument("--json", action="store_true")
    parse_parser.set_defaults(func=cmd_parse)

    game_data = subparsers.add_parser("game-data")
    game_data_sub = game_data.add_subparsers(dest="game_data_command", required=True)
    rebuild = game_data_sub.add_parser("rebuild")
    rebuild.add_argument("--output-dir", default=str(DEFAULT_GAMEDATA_DIR))
    rebuild.add_argument("--locale", default="en")
    rebuild.add_argument(
        "--source-game-data-dir",
        help="Optional path to extracted data folder when rebuilding JSON from GON/CSV.",
    )
    rebuild.set_defaults(func=cmd_game_data_rebuild)

    rebuild_short = subparsers.add_parser("rebuild")
    rebuild_short.add_argument("--output-dir", default=str(DEFAULT_GAMEDATA_DIR))
    rebuild_short.add_argument("--locale", default="en")
    rebuild_short.add_argument(
        "--source-game-data-dir",
        help="Optional path to extracted data folder when rebuilding JSON from GON/CSV.",
    )
    rebuild_short.set_defaults(func=cmd_game_data_rebuild)

    item = subparsers.add_parser("item")
    item_sub = item.add_subparsers(dest="item_command", required=True)
    item_add = item_sub.add_parser("add")
    item_add.add_argument("save")
    item_add.add_argument("--item-id", required=True)
    item_add.add_argument("--group", default="storage", choices=("storage", "trash", "backpack"))
    item_add.add_argument("--remove-instance-id", action="append", type=int)
    add_gamedata_arg(item_add)
    add_output_arg(item_add)
    item_add.set_defaults(func=cmd_item_add)

    item_remove = item_sub.add_parser("remove")
    item_remove.add_argument("save")
    item_remove.add_argument("--instance-id", action="append", type=int, required=True)
    item_remove.add_argument("--group", default="storage", choices=("storage", "trash", "backpack"))
    add_gamedata_arg(item_remove)
    add_output_arg(item_remove)
    item_remove.set_defaults(func=cmd_item_remove)

    furniture = subparsers.add_parser("furniture")
    furniture_sub = furniture.add_subparsers(dest="furniture_command", required=True)
    furniture_add = furniture_sub.add_parser("add")
    furniture_add.add_argument("save")
    furniture_add.add_argument("--key", type=int, required=True)
    furniture_add.add_argument("--furniture-id", required=True)
    furniture_add.add_argument("--x", type=int, default=256)
    furniture_add.add_argument("--y", type=int, default=256)
    furniture_add.add_argument("--room")
    furniture_add.add_argument("--remove-key", action="append", type=int)
    add_gamedata_arg(furniture_add)
    add_output_arg(furniture_add)
    furniture_add.set_defaults(func=cmd_furniture_add)

    furniture_remove = furniture_sub.add_parser("remove")
    furniture_remove.add_argument("save")
    furniture_remove.add_argument("--key", action="append", type=int, required=True)
    add_gamedata_arg(furniture_remove)
    add_output_arg(furniture_remove)
    furniture_remove.set_defaults(func=cmd_furniture_remove)

    cat = subparsers.add_parser("cat")
    cat_sub = cat.add_subparsers(dest="cat_command", required=True)
    cat_set = cat_sub.add_parser("set")
    cat_set.add_argument("save")
    cat_set.add_argument("--cat-key", type=int, required=True)
    cat_set.add_argument("--level", type=int)
    cat_set.add_argument("--stat", action="append")
    cat_set.add_argument("--mutation", action="append")
    add_output_arg(cat_set)
    cat_set.set_defaults(func=cmd_cat_set)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
