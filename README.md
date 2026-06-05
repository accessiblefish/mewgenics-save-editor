# Mewgenics Save Editor

Pure Python CLI for reading and editing Mewgenics save files.

## Quick Start

```bash
cd mewgenics-save-editor
python3 main.py parse /path/to/steamcampaign01.sav
```

Or install globally:

```bash
python3 -m pip install .
mewgenics-save parse /path/to/steamcampaign01.sav
```

Example output:

```
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

Never overwrite your original save until the modified save works in game.

## Export Save JSON

```bash
python3 main.py parse /path/to/steamcampaign01.sav --json > save.json
```

Search in `save.json`:

- `"key"` — cats and furniture
- `"instance_id"` — items
- `"item_id"` — item names
- `"mutations"` — cat mutation fields

## Add an Item

```bash
python3 main.py item add /path/to/steamcampaign01.sav \
  --item-id Clover \
  --output /path/to/modified.sav
```

Change inventory group:

```bash
--group backpack   # default: storage
```

## Remove an Item

Find `instance_id` in `save.json`, then:

```bash
python3 main.py item remove /path/to/steamcampaign01.sav \
  --instance-id 1041 \
  --output /path/to/modified.sav
```

## Add Furniture

```bash
python3 main.py furniture add /path/to/steamcampaign01.sav \
  --key 900001 \
  --furniture-id set_wooden_lamp \
  --output /path/to/modified.sav
```

Optional position:

```bash
--x 256 --y 256
```

## Remove Furniture

Find `key` in `save.json`, then:

```bash
python3 main.py furniture remove /path/to/steamcampaign01.sav \
  --key -11 \
  --output /path/to/modified.sav
```

## Edit Cat Data

Find `key` in `save.json`, then:

```bash
python3 main.py cat set /path/to/steamcampaign01.sav \
  --cat-key 619 \
  --level 7 \
  --stat STR=6 \
  --mutation body=300 \
  --output /path/to/modified.sav
```

Multiple stats:

```bash
--stat STR=7 --stat DEX=7 --stat CON=7
```

## Custom Game Data

Default data folder:

```
mewgenics-save-editor/gamedata
```

Custom:

```bash
--gamedata-dir /path/to/gamedata
```

## Troubleshooting

### `unknown item id`

Check spelling/capitalization against `gamedata/items/items.json`.

### `unknown furniture id`

Check `gamedata/furniture/furniture.json`.

### Missing `gamedata/items/items.json`

Put JSON files in `./gamedata` or pass `--gamedata-dir`.

### Modified save does not work in game

Make one small change at a time and test:

```bash
cp steamcampaign01.sav test.sav
python3 main.py item add test.sav --item-id Clover --output test-modified.sav
```

## Technical Reference

See [TECHNICAL.md](TECHNICAL.md) for save file format details.
