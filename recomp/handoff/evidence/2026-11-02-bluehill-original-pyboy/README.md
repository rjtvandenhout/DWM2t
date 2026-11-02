# BlueHill challenger: independent original-ROM comparison

On 2026-11-02 we compared an observed repeated-prize sequence in the native recompilation with the original Cobi cartridge code running in the independent [PyBoy 2.6.1](https://github.com/Baekalfen/PyBoy) Game Boy Color emulator. Both used copies of the same genuine pre-challenge Journal. This is an emulator comparison, not a recording from a physical cartridge.

The recompilation's [challenge](native-143.bmp), [victory/reward introduction](native-247.bmp), [first prize](native-249.bmp), [last prize](native-277.bmp), and [closed dialogue](native-281.bmp) were captured with the Windows x64 diagnostic EXE under Wine. After one battle, the player received meat items repeatedly until all 24 inventory slots were occupied.

The original ROM in PyBoy reached a BlueHill challenger in the same region with the same opening dialogue: [challenge](original-rom-015.png), [battle victory](original-rom-042.png), and [reward introduction](original-rom-044.png). The first observed prize was [BeefJerky](original-rom-046.png); [further button presses produced more prizes](original-rom-047.png). The observed inventory grew from 8 occupied slots at the challenge to [15 slots](original-rom-052.png), then [24 slots](original-rom-061.png). The dialogue then closed ([first](original-rom-062.png), [second](original-rom-063.png) capture). The original ROM therefore also shows the repeated-prize behavior; these observations do not establish a native-recompilation defect. The specific randomly chosen meat items differed between the two runs.

Both runs used only original player input. The PyBoy script read game memory to observe inventory and location, but never changed it, injected a state, edited a save, or used a cheat. The original ROM and Journal files remained byte-identical. PyBoy's built-in startup required one additional ordinary A press on the Continue card. The original recompilation's input was replayed through snapshot 135; the NPC moved differently after snapshot 127, so subsequent navigation used ordinary input to approach the challenger. The different navigation and RNG mean this is a behavioral comparison, not frame-identical replay or proof of every possible seed.

Inputs and identities:

- ROM: the repository-rebuilt 4,194,304-byte Cobi image, SHA-256 `8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`.
- Genuine input Journal: 32,768 bytes, SHA-256 `5afe17c1e9817cf9229af195690ba0834fccbe8155bf9992e6415f6a45d4ee00`; no Journal or ROM is committed here.
- Recompilation game source: `1351bcd058e491455a477045a2ff86bbc3bd7b1c`; Windows diagnostic SHA-256 `61a0e6d3ff84b5322b101247fc93ff6889f123a1bcd94df663135757fb3b9855`.
- Environment: Linux x86-64, Python 3.12.14, PyBoy 2.6.1, NumPy 2.5.4, PySDL2 0.9.17 and PySDL2-DLL 2.32.10. Packages were installed in an isolated scratch directory, not into the project or a system environment.
- Full completed native trace SHA-256 `28ad04d18daec846dd90fa9e07e3b21dc138634249be4af51f5eebdc7cfa0829`; [input prefix](prefix-p1.txt), [subsequent input](followup-p1.txt), [observation log](original-observations.jsonl), and [independent replay receipt](reproduction.json) are preserved here.

The entire PyBoy comparison was run a second time from the same original ROM and Journal. It again observed 8→24 occupied slots, and all nine selected original-ROM screenshot hashes matched the first PyBoy run. To reproduce when the genuine files are available, install PyBoy 2.6.1 into an isolated environment and run:

```sh
python reproduce.py --rom /path/to/cobi.gbc --save /path/to/genuine-prechallenge.sav --output /path/to/new-output
```

The script refuses mismatched inputs, uses a memory-only copy of the Journal, and does not write the original save. It checks the recorded inventory progression and all nine screenshot hashes.
