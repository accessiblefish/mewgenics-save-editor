# Mewgenics Save Editor

Pure Python CLI for reading and editing Mewgenics save files.

## What You Need

You need two things:

1. This folder: [mewgenics-save-editor](https://github.com/accessiblefish/mewgenics-save-editor)
2. Your save file, for example `steamcampaign01.sav`

## Install

Open a terminal in this folder:

```bash
cd mewgenics-save-editor
python3 -m pip install .
```

After install, the command is:

```bash
mewgenics-save
```

No-install local command:

```bash
python3 mewgenics_cli.py
```

## First Test

Read your save:

```bash
mewgenics-save parse /path/to/steamcampaign01.sav
```

No-install version:

```bash
python3 mewgenics_cli.py parse /path/to/steamcampaign01.sav
```

Example output:

```text
cats: 42
furniture: 163
items: storage=108 trash=0 backpack=0
day: 273
gold: 741
food: 462
```

## Safety Rule

Always write to a new save file:

```bash
--output /path/to/modified.sav
```

Do not overwrite your original save until the modified save works in game.

## Export Save JSON

Use this when you need cat keys, item instance IDs, or furniture keys:

```bash
mewgenics-save parse /path/to/steamcampaign01.sav --json > save.json
```

Open `save.json` and search for:

- `"key"` for cats and furniture
- `"instance_id"` for items
- `"item_id"` for item names
- `"mutations"` for cat mutation fields

## Add an Item

Add `Clover` to storage:

```bash
mewgenics-save item add /path/to/steamcampaign01.sav \
  --item-id Clover \
  --output /path/to/modified.sav
```

Choose a different inventory group:

```bash
mewgenics-save item add /path/to/steamcampaign01.sav \
  --item-id Clover \
  --group backpack \
  --output /path/to/modified.sav
```

Valid groups:

```text
storage
trash
backpack
```

## Remove an Item

First export JSON:

```bash
mewgenics-save parse /path/to/steamcampaign01.sav --json > save.json
```

Find the item `instance_id`, then remove it:

```bash
mewgenics-save item remove /path/to/steamcampaign01.sav \
  --instance-id 1041 \
  --output /path/to/modified.sav
```

Remove from a different group:

```bash
mewgenics-save item remove /path/to/steamcampaign01.sav \
  --instance-id 1041 \
  --group backpack \
  --output /path/to/modified.sav
```

## Add and Remove an Item Together

```bash
mewgenics-save item add /path/to/steamcampaign01.sav \
  --item-id Clover \
  --remove-instance-id 1041 \
  --output /path/to/modified.sav
```

## Add Furniture

Add `set_wooden_lamp`:

```bash
mewgenics-save furniture add /path/to/steamcampaign01.sav \
  --key 900001 \
  --furniture-id set_wooden_lamp \
  --output /path/to/modified.sav
```

Use a key that does not already exist in the save.

Optional position:

```bash
mewgenics-save furniture add /path/to/steamcampaign01.sav \
  --key 900001 \
  --furniture-id set_wooden_lamp \
  --x 256 \
  --y 256 \
  --output /path/to/modified.sav
```

## Remove Furniture

First export JSON:

```bash
mewgenics-save parse /path/to/steamcampaign01.sav --json > save.json
```

Find the furniture `key`, then remove it:

```bash
mewgenics-save furniture remove /path/to/steamcampaign01.sav \
  --key -11 \
  --output /path/to/modified.sav
```

## Add and Remove Furniture Together

```bash
mewgenics-save furniture add /path/to/steamcampaign01.sav \
  --key 900001 \
  --furniture-id set_wooden_lamp \
  --remove-key -11 \
  --output /path/to/modified.sav
```

## Edit Cat Data

First export JSON:

```bash
mewgenics-save parse /path/to/steamcampaign01.sav --json > save.json
```

Find the cat `key`, then edit:

```bash
mewgenics-save cat set /path/to/steamcampaign01.sav \
  --cat-key 619 \
  --level 7 \
  --stat STR=6 \
  --mutation body=300 \
  --output /path/to/modified.sav
```

Multiple stats:

```bash
mewgenics-save cat set /path/to/steamcampaign01.sav \
  --cat-key 619 \
  --stat STR=7 \
  --stat DEX=7 \
  --stat CON=7 \
  --output /path/to/modified.sav
```

## Use a Different JSON Data Folder

Default:

```text
mewgenics-save-editor/gamedata
```

Custom:

```bash
mewgenics-save item add /path/to/steamcampaign01.sav \
  --item-id Clover \
  --gamedata-dir /path/to/gamedata \
  --output /path/to/modified.sav
```

The custom folder must contain:

```text
gamedata/
  items/items.json
  furniture/furniture.json
  mutations/all.json
  abilities/*.json
```

## Optional: Rebuild JSON From GON

Normal users can skip this.

Use this only if you have original GON/CSV files and want to regenerate `gamedata`.

Expected source folder:

```text
  csv/combined.csv
  items/*.gon
  abilities/*.gon
  passives/*.gon
  mutation/*.gon
  furniture_effects.gon
```

Rebuild:

```bash
mewgenics-save game-data rebuild \
  --source-game-data-dir /path/to/GameData
```

This writes JSON to:

```text
mewgenics-save-editor/gamedata
```

## Common Problems

### `unknown item id`

The item ID is not in:

```text
gamedata/items/items.json
```

Check spelling and capitalization.

### `unknown furniture id`

The furniture ID is not in:

```text
gamedata/furniture/furniture.json
```

Check spelling and capitalization.

### `No such file or directory: gamedata/items/items.json`

The JSON data folder is missing.

Put JSON files in:

```text
mewgenics-save-editor/gamedata
```

Or pass:

```bash
--gamedata-dir /path/to/gamedata
```

### Modified Save Does Not Work in Game

Make one small change at a time:

```bash
cp steamcampaign01.sav test.sav
mewgenics-save item add test.sav --item-id Clover --output test-modified.sav
```

Test `test-modified.sav` in game before making more edits.

## Quick Copy-Paste Workflow

```bash
cd mewgenics-save-editor
python3 -m pip install .
mewgenics-save parse /path/to/steamcampaign01.sav
mewgenics-save item add /path/to/steamcampaign01.sav --item-id Clover --output /path/to/modified.sav
```
