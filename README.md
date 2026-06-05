# Mewgenics Save Editor

Pure Python CLI for reading and editing Mewgenics save files.

## Quick Start

```bash
cd mewgenics-save-editor
python3 main.py parse /path/to/steamcampaign01.sav
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

## Get Game Data

The editor ships with generated JSON in `gamedata/`. You only need this section when you want to refresh that JSON from a newer game build.

### Step 1: Find the `resources.gpak`

In Steam:

1. Right-click Mewgenics
2. Select `Manage`
3. Select `Browse local files`

This opens the game install folder. Find: `resources.gpak`.

### Step 2: Unpack the `resources.gpak`

1. Open [https://mewgpaks.netlify.app/](https://mewgpaks.netlify.app/)
2. Upload the `resources.gpak`
3. Wait for the website to extract the data
4. Save the extracted `data` folder into this project folder

### Step 3: Check the extracted `data` folder

The extracted folder should contain these files and folders:

```
data/
  text/
    combined.csv
  items/
    *.gon
  abilities/
    *.gon
  mutations/
    *.gon
  passives/
    *.gon
  furniture_effect.gon
```

Required files:

- `data/text/combined.csv`
- `data/items/*.gon`
- `data/abilities/*.gon`
- `data/mutations/*.gon`
- `data/passives/*.gon`
- `data/furniture_effect.gon`

Keep this folder structure exactly. Do not move all `.gon` files into one folder.

### Step 4: Rebuild `gamedata`

Run this from the project folder:

```bash
python3 main.py rebuild
```

This updates:

```
gamedata/items/items.json
gamedata/furniture/furniture.json
gamedata/mutations/all.json
gamedata/abilities/*.json
```

### Notes

The rebuild command also accepts older source names:

```
csv/combined.csv
mutation/*.gon
furniture_effects.gon
```

If your extracted `data` folder is somewhere else:

```bash
python3 main.py rebuild --source-game-data-dir /path/to/data
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
