# Original key-trade refusal and cancellation — 2026-11-02

On Wine, the exact verified production executable (source `1351bcd058e491455a477045a2ff86bbc3bd7b1c`, SHA-256 `63bf283dfeb7543c82d2787221788ab71e8651130b0a829b8987b368864a6f95`) ran with independent copies of the genuine QuietSea-clear Journal (`91b3690b8e7acee6a55118152497f0d57245236bce7c62d1b537ec0486180054`). Only original P1 keyboard inputs were used; no game-memory or original-save changes were made.

Player 1 proposed QuietSea. Player 2 separately selected and confirmed Pirate, Oasis, and GreatLog; the original game displayed “That key cannot be traded” each time. After player 2 cancelled, both players saw the original [refusal](cancel-player1.bmp) / [cancellation](cancel-player2.bmp) messages and returned to their title menus. The linked process exited 0.

Both actual resulting Journals were then independently reopened using original Continue in fresh processes; both reached the original QuietSea cave, exited 0, and returned byte-for-byte to the 32-KiB seed. [Player 1](fresh-player1.bmp) · [Player 2](fresh-player2.bmp).

Selected key confirmation and refusal: [Pirate](pirate-selection.bmp) / [refused](pirate-refused.bmp); [Oasis](oasis-selection.bmp) / [refused](oasis-refused.bmp); [GreatLog](greatlog-selection.bmp) / [refused](greatlog-refused.bmp). The [receipt](receipt.json), unmodified run reports and input event logs include SHA-256 values and exact observations. The scripts identify the scratch paths used; no saves or executable are included.

This covers three fixed-key refusal paths and cancellation, not a completed trade between different random keys, a Tara counterpart or DreamEgg exchange.
