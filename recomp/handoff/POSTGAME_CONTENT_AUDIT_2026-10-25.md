# Original postgame content inventory

This inventory separates original source gates from witnessed gameplay. It uses
the matching Cobi ROM and genuine Journals, with no outside walkthrough. The
accepted ending has 22 acquired catalogue species; the separate gift branch
has 24. A refusal checks a gate and does not complete its reward path.

| Content | Original requirement | Coverage |
| --- | --- | --- |
| Newlywed egg | Ending flag `25`, shared claim `CD` clear, farm capacity | Original WhipBird egg received and saved/reloaded. |
| Evaluator introduction and certified egg | Ending; introduction `28`, claim `29`, farm capacity | Original Lionex egg received; both flags and all owned data checked. |
| Granddaughter duel | Ending; earlier SpotSlime request is bypassed in this branch | Original battle 21 reached; attempt lost. |
| Arena B/A/S | Sequential progress; fees 500/1000/5000G | Actual B refusal and fee display at 11G. No later-class win claimed. S unlocks repeatable stronger-master prizes. |
| FunkyBird NPC breeding | Ending, adult owned parent, first offer unclaimed | Separate original-P1 service check in progress. |
| Skeletor NPC breeding | Ending, adult owned parent, first offer unclaimed | Separate original-P1 service check in progress. |
| Copycat and StoneMan offers | 100 species plus previous offer progression | Source gates/spawn chains checked. |
| Andreal offer | 150 species plus previous offer progression | Source gate/spawn chain checked. |
| Kameha / ElfKey | 50 species; victory `39`, key claim `3A` | Actual collection gate inspected at 24 species; reward route source-audited. |
| Kameha / TravelerKey | 150 species, prior key claim; victory `3B`, claim `3C` | Source-audited. |
| Old man / BrawnKey | Living LordDraco, Genosidoh, AsuraZoma, PsychoPiz or Darck; claim `3D` | Original refusal witnessed with the current party. Local Cobi branch grants Brawn, not Baffle. |
| Old man / SoulKey | Prior progression and both world-test flags `206/207`; claim `C8` | Source-audited; counterpart-key exchange required. |
| Four King bounties | 100/120/140/160 species, sequential quest flags | Source gates/rewards checked; ordinary training dialogue witnessed below the gates. Rewards are 10000/20000/30000/40000G. |
| Terry duel / later breeding | 150 species and completed Reception offer progression | Source-audited; first attempt `37`, victory `38`. |
| Petibou / Warubou | 250–289 / 290 species, both gift flags clear, farm capacity | Source-audited alternative gift branches. Claiming either flag `2A/2B` prevents a later second gift from this service. |
| Medal Man | Real TinyMedal currency and capacity | Exact seven-prize service checked in source; actual minimum refusal at one banked medal. |
| DreamEgg | Actual DreamEgg state `CECE == 1` at farm interaction | Real trigger traced. Obtaining, feeding and hatching remain unverified. Ordinary farm egg gifts are separate. |
| Lamia / Dimensaur / Kagebou arrivals | Exact legitimate acquisition paths unresolved | Arrival strings alone establish neither solo nor link-only acquisition. No completion claim. |

NPC breeding requires a selected owned parent at level 10 or above. The original
service protects a sole active party member and assigns the NPC mate the opposite
gender; there is no fixed player-parent gender requirement in that chooser.
Normal breeding compatibility still applies. The initial offers are available
without reaching the later catalogue gates.

Tavern world 23, selector `F0` at 64,48, progresses through FunkyBird, Copycat
and Andreal. Reception world 4 region 2,0, selector `F1` at 80,32, progresses
through Skeletor and StoneMan, then Terry selector `F2` occupies that position.
The original re-entry flags are `C9/CA` and `CB/CC`; claim flags are `32..36`.

## Medal Man and prices

Medal Man spends currency repeatedly; this is not a cumulative one-time ladder.
The original options and costs are:

| Prize | TinyMedals |
| --- | ---: |
| MeteOrb | 3 |
| MadCat | 3 |
| HornBeet | 4 |
| SkyDragon | 4 |
| Octogon | 5 |
| Servant | 5 |
| Darck | 10 |

The ending already enables the Darck option through `C837`; currency is at
`C838:C839`. Original code checks capacity before subtracting the selected cost.
The separate QuietSea branch has one banked medal and one unsubmitted TinyMedal.
The gift/NPC branch starts with only the banked medal. These branches are not
merged or credited with each other's items.

Original merchant pricing independently confirms runtime item 69 is SteelFang,
with resale base 500G and the inspected merchant's 75% offer of 375G. All current
priced extras on the QuietSea branch total 423G including the initial wallet,
below B's 500G fee. Runtime item 44 is TinyMedal; 45 is GoldPass. The repaired
item export retains the actual ID mapping and raw record bytes.

## Fixed key-world source inventory

| Key / area | Original fixed map IDs |
| --- | --- |
| Elf / Elven | 164, 168–175: Elven, forest, Lookout, Summit, mountain and doors |
| Lonely counterpart | 176–182: Lonely, Kiral Lab, three basement floors and Barrel room |
| Traveler | 184–197: Traveler, Miagen, hut, forest, inn, summit, seven old-tower floors and door |
| Brawn / Power | 200–206: Power world and six tower floors |
| Baffle counterpart | 208–215: door, Baffle world and six tower floors |
| Soul | 217–223: door, Soul world and five tower floors |

Cobi's local Kameha grants Elf then Traveler. The old-man branch grants Brawn;
the alternate Baffle branch is not taken. Soul requires both genuine test flags.
Counterpart acquisition needs an original peer exchange, for which the present
native runtime has no transport. These map inventories do not claim played
completion of the worlds.

An unresolved Home world 6 second-room event copies canned catalogue bitsets.
It was never used and is excluded from earned catalogue/reward coverage.

Machine-readable original bank/address/line citations are retained in
[the source inventory](evidence/2026-10-25-postgame/postgame-content-audit.json),
[the source-gap addendum](evidence/2026-10-25-postgame/postgame-source-gap-addendum.json)
and [conditional NPC records](evidence/2026-10-25-postgame/npc-breeding-and-terry-conditional-records.json).
Actual saves, screenshots and native results are summarized in
[the progress report](POSTGAME_PROGRESS_2026-10-25.md).
