#!/usr/bin/env python3
"""Shared helpers for building CLI JSON from Mewgenics GameData sources."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parent


def default_game_data_dir() -> Path:
    candidates = (
        PROJECT_ROOT / "docs" / "GameData",
        PROJECT_ROOT.parent / "docs" / "GameData",
        Path.cwd() / "docs" / "GameData",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


GAME_DATA_DIR = default_game_data_dir()
CSV_DIR = GAME_DATA_DIR / "csv"
COMBINED_CSV = CSV_DIR / "combined.csv"
PUBLIC_DIR = PROJECT_ROOT / "data"


def set_game_data_dir(path: Path) -> None:
    global GAME_DATA_DIR, CSV_DIR, COMBINED_CSV
    GAME_DATA_DIR = path
    CSV_DIR = GAME_DATA_DIR / "csv"
    COMBINED_CSV = CSV_DIR / "combined.csv"

CSV_TO_LOCALE = {
    "en": "en",
    "sp": "es",
    "fr": "fr",
    "de": "de",
    "it": "it",
    "pt-br": "pt-br",
    "ru": "ru",
    "ko": "ko",
    "ja": "ja",
    "zh": "zh",
}

LOCALES = tuple(CSV_TO_LOCALE.values())


def load_localized_csv(path: Path) -> dict[str, dict[str, str]]:
    """Return locale -> key -> text using the CSV header names."""
    rows_by_locale = {locale: {} for locale in LOCALES}

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{path} has no CSV header")

        available_columns = {
            csv_column: locale
            for csv_column, locale in CSV_TO_LOCALE.items()
            if csv_column in reader.fieldnames
        }

        for row in reader:
            key = (row.get("KEY") or "").strip()
            if not key or key.startswith("//"):
                continue

            for csv_column, locale in available_columns.items():
                value = (row.get(csv_column) or "").strip()
                if value:
                    rows_by_locale[locale][key] = value

    return rows_by_locale


def localized_text(
    csv_data: dict[str, dict[str, str]],
    locale: str,
    key: str | None,
    fallback: str = "",
) -> str:
    if not key:
        return fallback
    return csv_data.get(locale, {}).get(key) or csv_data["en"].get(key) or fallback


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def strip_line_comment(line: str) -> str:
    in_quote = False
    escaped = False
    for index, char in enumerate(line):
        if char == "\\" and in_quote:
            escaped = not escaped
            continue
        if char == '"' and not escaped:
            in_quote = not in_quote
        if char == "/" and not in_quote and line[index : index + 2] == "//":
            return line[:index]
        escaped = False
    return line


def strip_block_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def cleaned_lines(path: Path) -> list[str]:
    content = strip_block_comments(path.read_text(encoding="utf-8"))
    return [strip_line_comment(line).rstrip() for line in content.splitlines()]


def find_matching_brace(text: str, open_index: int) -> int:
    depth = 0
    in_quote = False
    escaped = False

    for index in range(open_index, len(text)):
        char = text[index]
        if char == "\\" and in_quote:
            escaped = not escaped
            continue
        if char == '"' and not escaped:
            in_quote = not in_quote
        elif not in_quote:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return index
        escaped = False

    raise ValueError("unmatched brace in GON content")


def top_level_blocks(path: Path) -> list[tuple[str, str]]:
    """Return (block_name, body) for top-level GON blocks."""
    text = "\n".join(cleaned_lines(path))
    blocks: list[tuple[str, str]] = []
    index = 0

    while index < len(text):
        match = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\{", text[index:])
        if not match:
            break

        name = match.group(1)
        open_index = index + match.end() - 1
        close_index = find_matching_brace(text, open_index)
        body = text[open_index + 1 : close_index]
        blocks.append((name, body))
        index = close_index + 1

    return blocks


def child_blocks(body: str, name_pattern: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    index = 0
    pattern = re.compile(rf"(?m)(?<![A-Za-z0-9_])({name_pattern})\s*\{{")

    while index < len(body):
        match = pattern.search(body, index)
        if not match:
            break
        name = match.group(1)
        open_index = match.end() - 1
        close_index = find_matching_brace(body, open_index)
        blocks.append((name, body[open_index + 1 : close_index]))
        index = close_index + 1

    return blocks


def quoted_value(body: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s+\"([^\"]*)\"", body)
    return match.group(1) if match else None


def bare_value(body: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s+([^\s{{}}]+)\s*$", body)
    return match.group(1) if match else None
