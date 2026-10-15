# Sprite formats

## Battle monster sprites

- Far-pointer table: file offset `0x10EAA`.
- One 3-byte `(pointer low, pointer high, bank)` entry per core-monster slot.
- Compressed data expands through the game's common decompressor.
- A battle sprite expands to `0x0100` bytes before tile/layout processing.

## Overworld sprites

- Far-pointer table: file offset `0xE0001`.
- One 3-byte far pointer per overworld sprite definition.
- Each extracted definition expands to `0x0240` bytes (576 bytes, 36 Game Boy 2bpp tiles).
- Runtime frame/OAM layout has been reconstructed.

## Timing

The game is VBlank driven at approximately `59.7275 Hz`. Normal overworld walking alternates the two walking frames every 8 VBlanks, or about `0.13394 s` per displayed walking frame. The slower state uses 32 VBlanks per sprite state, about `0.53577 s`.
