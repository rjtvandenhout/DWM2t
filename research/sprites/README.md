# DWM2 Cobi's Journey — ROM Sprite Extraction

This pack was generated directly from the supplied **Dragon Warrior Monsters 2: Cobi's Journey (USA)** ROM.

The ROM itself is **not included**.

## Source verification

- Size: `4,194,304` bytes
- SHA-256: `8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`

All graphics in this pack are decoded from that ROM. No external sprite sheets were used as the source.

## What is included

### Battle monster sprites

`battle/individual/`
- `383` core-ID sprite PNGs.
- Fixed **48×48** transparent canvas.
- Original CGB palette from the ROM.
- Core IDs are preserved, including unused/internal/secret/duplicate slots.

`battle/individual_tight/`
- Same sprites cropped tightly to visible pixels.

`battle/battle_atlas_defined_clean.png`
- All `323` core records that the mechanics table marks as defined.
- 48×48 cells, 16 columns, transparent background.

`battle/battle_atlas_defined_labeled.png`
- Readable labeled version with core ID, ROM name and family.

`battle/battle_atlas_all_core_ids_*`
- All `383` sprite-table entries, including internal/unused duplicate IDs.

`battle/battle_atlas_unique_visuals_*`
- `326` unique rendered RGBA sprites after palette application.

`battle/families/`
- Separate clean and labeled atlas for Slime, Dragon, Beast, Bird, Plant, Bug, Demon, Zombie, Material, Water and the boss/unknown family.

### Overworld sprites

The overworld does **not** have one sprite definition for every monster species. It has a shared bank of entity sprite definitions used by the player, NPCs, story monsters, bosses and objects.

To avoid silently omitting any monster-like overworld graphic, this pack exports **all 98 overworld entity definitions**.

`overworld/all/sprite_XXX/`
- `tight/frame_N.png`: tightly cropped frame.
- `canvas_64x48/frame_N.png`: stable **64×48** canvas preserving the game's OAM origin.
- `strip.png`: all stored frames in original order.
- `four_direction_strip_generated.png`: for standard six-frame entities, adds a mirrored side pair so all four directions are available.

The standard six-frame order is:

1. down / front A
2. down / front B
3. side A
4. side B
5. up / back A
6. up / back B

The opposite horizontal direction is not stored separately by the game; it is produced by horizontal mirroring.

Frame-count distribution in this ROM:
- 95 definitions: 6 frames
- IDs 71 and 72: 3 large composite frames
- ID 84: 8 frames

`overworld/overworld_first_frame_atlas_clean.png`
- Fixed-grid clean preview of every overworld definition.

`overworld/overworld_first_frame_atlas_labeled.png`
- Labeled overview by overworld sprite ID.

`overworld/overworld_all_frames_labeled.png`
- Every stored frame for all 98 definitions.

## Exact ROM formats found

### Full battle monsters

- Far-pointer table: ROM `0x0E0001`
- One 3-byte far pointer per core ID: `pointer low, pointer high, ROM bank`
- Each block decompresses to `0x0240` bytes = 576 bytes
- 576 bytes = 36 Game Boy 2bpp tiles
- Tiles are arranged row-major in a 6×6 grid = **48×48 pixels**
- CGB palette table: ROM `0x09F328`
- 8 bytes / four BGR555 colors per core ID
- Color index 0 is exported as transparent

### Overworld entities

- Graphics pointer table: ROM `0x0103AC`
- IDs below `0x50` load graphics from ROM bank 125
- IDs `0x50+` load graphics from ROM bank 126
- Palette-map table: ROM `0x010A46`
- Palette data: ROM `0x1F8B15`
- OAM definition pointer table: ROM `0x1FC008`, bank 127
- OAM entries are `Y offset, X offset, tile offset, attributes`
- OAM frame data terminates with `Y = 0x80`
- Horizontal and vertical flip attribute bits are applied in the exported PNGs

### Graphics compression

Both sprite systems use the game's runtime decompressor at CPU address `0x0CF5`.

Compressed blocks contain:
- 2-byte little-endian decompressed length
- 1-byte marker value
- literal bytes and marker-triggered 12-bit backreferences

A standalone reproduction extractor is included in `tools/extract_sprites.py`.

## Metadata

`metadata/battle_sprites.csv`
- core ID and name
- defined/internal status
- family
- source ROM bank/pointer/offset
- compressed/decompressed sizes
- exact palette colors
- visible bounding box
- image hash and duplicate relationship
- output filenames

`metadata/overworld_sprites.csv`
- overworld sprite ID
- graphics bank/pointer/offset
- tile count
- palette
- OAM definition pointer
- frame count
- fixed-canvas anchor

`metadata/overworld_frames.csv`
- OAM pointer for every frame
- OAM object count
- relative bounding box
- tile usage
- exported file paths

`metadata/manifest.json`
- machine-readable version of the complete extraction metadata.

## Unity import recommendation

For pixel-perfect use:

- Texture Type: **Sprite (2D and UI)**
- Filter Mode: **Point**
- Compression: **None**
- Generate Mip Maps: **Off**
- Alpha Is Transparency: **On**

For the 64×48 overworld canvas, the game's logical origin/foot anchor is pixel `(32, 40)` measured from the top-left.

Equivalent Unity custom pivot:
- X = `0.5`
- Y = `0.166667`

The original overworld walking animation toggles its two stored walking frames every **8 Game Boy frames**.
At ~59.7275 Hz this is about **0.13394 seconds per walking frame**.

## Notes

- Names are the ROM's original English localization names.
- Several core IDs are unused, internal or special and may share graphics.
- `duplicate_of_core_id` in the metadata is based on the final rendered RGBA pixels, so palette variants remain distinct.
- The overworld IDs are deliberately kept numeric. A single ROM table does not provide a trustworthy one-to-one monster-name label for every overworld entity; inventing names would make the asset pack less reliable.
- Nothing in this archive modifies the original ROM.
