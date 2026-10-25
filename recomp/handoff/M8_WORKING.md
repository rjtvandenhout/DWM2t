# M8 working record (not an acceptance/completion record)

Current continuation (2026-10-23): the user requested M7 review and M8 work
for the whole game. The historical stop/continue choice below is answered.
The continuing report with original screenshots is
`M8_PROGRESS_2026-10-25.md` (continuing `M8_PROGRESS_2026-10-24.md`). HoodSquid and the mermaid-palace route have now been
reached; the user also requested breeding while reserving Squiz for the story.
See `M8_DANCER_2026-10-23.md` and `M8_PREPARATION_2026-10-24.md` for the
replayed farm, recovery, trading and trained-party Journals. Remaining worlds
and ending still need validation. Actions storage cleanup is recorded in
`ACTIONS_STORAGE_2026-10-24.md`.

Approved scope: finish the original game through ending/credits, retain every
M1-M7 regression, verify later original Saves and fresh Continue, and package
the final native Windows release. Only repository/original game output may
inform implementation. No fabricated game state or runtime interpreter.

## Baseline

- Branch: `work/recomp-m8`, starting at clean M7 `bc79ec91342031451103145e4fd830d9b7fe00dd`.
- Immutable M7 restore stays at `3bb1e18170fc928f372f9cc72cc433d85c0666ca`.
- M7 was revalidated immediately before M8: all twelve tests passed in 139.29 s.
- Accepted input/save fixtures and all exact M7 constants remain unchanged.
- No `restore/recomp-m8`, `M8_RESULT.md`, or final-release claim until full acceptance.

Latest complete Windows prefix: twenty story checkpoints through Sea World,
post-story Squiz/Phes breeding, C Class, IceKey, Norden restoration, Westania's
performance, YunaSoul/Puppetor/Yuna restoration and SleepHerb/GoatHorn/Helen
restoration. Run 40136433795 passed at
`0e39a6fe49e37261d33d3a44b488ff66defa8930`. All twenty archived Journals were
independently downloaded and exactly match Wine, including the 64-byte quest
comparison after fresh Continue. Later original breeding/training continues.

Subsequent Ice exploration ended in an original defeat and Warubou recovery.
Further original battles trained Slash to level 16, Totum and Liset to level
17; Liset learned HealAll and TwinHits. A WingSlime joined the farm. The finite
fourteenth route retains the exploration, defeat, recovery and training and
passes independent Wine replay to exact Journal SHA256
`d8e8e6992d67bf03df63edd302b36d02778084b680bdb7ad9831b60fae97bbd1`.
All thirteen owned creatures and their inherited data persist through fresh
Continue. A fifteenth route earns the spirit's Crest and rests at Norden's
inn; its exact Journal also independently replays under Wine.

The sixteenth route wins the original 650 HP BombCrag battle, follows the
gold-dust aftermath, is imprisoned by Norden's impostor, meets the real king
and Kameha, opens the hollow jail wall and escapes. Its original town Journal
independently replays under Wine to SHA256
`494ed3a48672d938c986a8ce96fc21c5e3359e6387f75195087190592bc7ee48`.
Party order Totum/Liset/Slash is retained at levels 18/18/16, HP 63/70/0 and
status 0/0/0x80; all thirteen monsters, skills, inherited data, keys and quest
bytes persist. The original B-button jump is required in the central mine
shaft. The seventeenth route revives Slash through the original priest for
85G, rests, exposes and defeats the 550 HP AgDevil with all three monsters
alive, restores the real king, opens the border (flag 0x94), rests again and
saves in Norden. Its exact Journal independently replays under Wine to SHA256
`16a86744a4e6416083a49b371d5b9071faae0036318306ac6364f2b79938cdd0`.
Party Totum/Liset/Slash is level 19/18/16, full HP 118/76/138 and status 0/0/0,
with all thirteen owned monsters and 355G. Both boss routes retain read-only
combat-mode/full-HP witnesses without changing any controller input or Save
hash. Native Windows acceptance of stages fourteen through seventeen passed.

An eighteenth route reads Westania's palace notice, follows Kameha's arrival,
gains admission and plays the original performance before the king and Lady
Yuna. Yuna remains unresponsive. Its original town Journal independently
replays under Wine to SHA256
`7324097161189f30ada19a2577750b36b98bafe14a7e67bebf5d87566bff0f8c`;
all thirteen monsters persist, with Totum/Liset/Slash level 19/19/17, HP
86/58/109, status 0/0/0 and 945G. The action point for the notice is original
world 90, region 1,0, position 96,96, facing Up. Bank 135's original field
event tables describe non-NPC interactions and map-entry scenes; read-only
inspection is useful alongside the NPC and map guides.

Seventeen-stage Windows run 40130993635 at
`f37cbcc4992605a747977376975dec499135ce98` passed. A temporary HTTP 401 blocked
evidence retrieval, but GitHub access recovered. Artifact 12575663721
(1,128,844 bytes; ZIP SHA256
`b4bdc27b86f81a046eb9e4fc1a3056492980c5f448aabd7ba7be4e087e9199ef`)
was downloaded and all seventeen Journals matched the exact manifest hashes.
The Python validator now additionally compares 64 quest bytes after fresh
Continue: later Ice court scripts use flags 0x1E1 through 0x1F1 beyond the
native 56-byte core witness. This stronger read-only check also passes against
all seventeen archived Windows captures and the five latest Wine captures.
The native executable and all M1–M7 checks remain unchanged.
The nineteenth original route obtains YunaSoul, defeats 400 HP Puppetor,
restores Yuna and saves in Westania. Independent Wine replay and fresh Continue
pass to exact Journal SHA256
`c186ec00dc3cb19e00fa7cc5951e3d3ba8baeb0447b3f5843d6cc4f24fcbee1a`.
All thirteen owned monsters persist; Totum/Liset/Slash are level 20/19/17,
HP 74/64/140, status 0/0/0, with 935G and flags 0x97–0x9D. Stages eighteen
through twenty passed Windows run 40136433795. The twentieth route obtains SleepHerb,
defeats 850 HP GoatHorn with all three alive, restores Helen and rests. Its
original Journal and fresh Continue independently replay under Wine to SHA256
`bc02bc19997678687215aafcc50bd7761f61533e95b48897da939123f4c924d7`.
The party is level 21/20/18, full HP 119/79/143, with thirteen owned monsters,
905G and late flags 0x1E1/0x1E2/0x1F1. The finite route includes the original
unsuccessful save attempt during movement and later successful settled save;
no runtime/game-state workaround was used. The live continuation fought the spring's ArcDemon/GoatHorn group twice and
was defeated through original combat. Warubou recovery retained quest progress.
The twenty-first route retains both defeats and then breeds Totum (male
RayGigas, level 21) with farm Merman Nyar (female, level 14). The original
20G hatch produces Derzo, a male RayGigas +1. Independent Wine replay and
fresh Continue pass to exact Journal SHA256
`8bdc0713a519207c2e4536b2748c5c5fe803df331a6b85a596c33ff7a69aa70c`.
All eleven other monsters are retained after original compaction; the active
party is Liset/Slash/Derzo (records 7/0/11), levels 21/18/1, HP 79/143/46,
with twelve owned monsters and 206G. Derzo then reaches level 10 through
original training, HP 118, ATK 114 and DEF 104; former Totum at level 21 had
HP 119, ATK 115 and DEF 78. The twenty-second original Journal now reaches
Liset/Slash/Derzo levels 23/20/20, full HP 84/146/167, with twelve owned monsters
and 206G. Derzo's Info shows ATK 186, DEF 153 and the learned Firebane, Defense,
Vivify and SleepAir. Its exact Journal SHA256 is
`62d2f2a5b77748dd0d79d29e4814cd3600e2c60993d66f67306bf16ae49eed24`;
independent replay of the 658,627-frame route passed. The twenty-third route
then defeats the spring group with all three alive, returns the Crest through
its original Use action, earns Sky Shield, returns to Warubou and unlocks cloud
flight (new flags 0x1E/0x23/0x1E4/0x1E5; IceKey entry 0x44). Independent Wine
replay and fresh Continue pass to exact Journal SHA256
`8297929d8dc38948f3cfec4bf1e94865220215aa10d2913fcf46d7ce2f6364f3`.
The party is level 24/21/21, full HP 87/146/167, with twelve owned monsters
and 206G. The subsequent live royal audience about Kameha's disappearance has
added the original SkyKey entry 0x05. Native Windows acceptance after stage 20
passed in run 40142961686: twenty archived checkpoints audited and four later
routes replayed, with exact Journal hashes and current persistence checks.
The separate production GUI has loaded Yuna's later Journal, completed original
Journal Save and reloaded it in a fresh process under Wine/Xvfb. This does not
replace final Windows/full-game release acceptance; its exact report and
screenshots are linked in the progress report.

Ice World's main story and Sky Key now pass independent Wine replay. The
24th original Journal SHA256 is
`48f169d790414fea04e028a437dfaec06567c7558f55cdcc6e2163d72be6bb4f`.
All twelve monsters, full party HP 87/146/167, 206G and six keys persist after
fresh Continue. Windows run 40142961686 has independently passed the four
later routes after auditing all twenty archived prefix checkpoints. Artifact
12579134999 is 269,528 bytes, ZIP SHA256
`27aaf91b98cca87b5d5c29e6cfbdec56b00eb5236f789032daa5e41fb952c1c9`;
all four downloaded Journals exactly match Wine and pass current checks.
Production GUI Windows run 40144322233 passed: two normal shutdowns, later
Journal Save and fresh-process reload with all twelve monsters and 64 quest
bytes retained. Its downloaded Save independently passes the current checks. The live party has
visited Fhunt tower, seen the MadCondor take the LightOrb and obtained
ChangeStaff from behind Ugor’s grave. The 25th finite route independently
passes under Wine to original Journal SHA256
`dd9b5864e04c93be97c1b6513718dab84e734b8ef0012625b14110683ae74626`.
The party is level 25/22/22, HP 87/121/169, status 0/0/0, with twelve owned
monsters, 196G and ChangeStaff. Every persistent-data check passes. Its live
continuation has used ChangeStaff and passed the guarded bridge normally. Later worlds,
ending/credits and final release acceptance remain outstanding. Screenshots and exact provenance are in
`M8_PROGRESS_2026-10-24.md`.

## Current Sky continuation (2026-10-25)

Checkpoint 26, Pei inn, passes independent Wine replay to Journal SHA256
`fc4be98a84c03cd273c4ab422f9d85af911b9d828afe07e8c6f77e469fd9e736`.
All thirteen owned monsters persist; party Slash/Derzo/Liset is level 23/24/26,
full HP 151/175/90, with 186G. Gigantes joined the farm normally. Derzo's
inherited Vivify revived Liset after a travel knockout. Current validators
compare the full original 107-byte saved quest block CBD7:CC42 (bank 2:$7636
and $76AC, length 0x6B; original SRAM 3DA0:3E0B), including Sky flag 0x209.
All 24 Windows and two later Wine captures pass that stronger read-only check.

The live continuation defeated the 600-HP MadCondor with all three alive after
Derzo revived Slash. MadCondor joined the farm. WorldDew was collected but the
LightOrb chest is empty. The original game refused Journal Save at the nest.
The exact original P1 prefix, including that refusal, replayed from the
original Pei Journal. The party returned to Pei's traveler inn, rested and
made its 27th Journal. Its 136,123-frame Wine replay and fresh Continue pass
to SHA256 `2655aa444fb56f2312e36b48ec446d0e085024ff3e11001fcc282fd3e6814788`,
including all 107 quest bytes and fourteen owned monsters. The party is
Derzo/Liset/Slash, level 25/27/24, full HP 176/90/154, with 166G. The live
continuation has read the royal notice at world 124: Heaven Sword, Armor and
Helmet are requested for LightOrb. Native Windows run 40148369185 passed all
seven routes after the audited twenty-checkpoint prefix; all downloaded
Journals match Wine and independently pass the full 107-byte checks.

The 28th route retains a subsequent travel defeat and Warubou recovery, then
breeds Liset (base, Octokid +1 female level 27) with Varli (MadCondor male
level 30). Original 40G hatching produces male Garon, RayGigas +3, WLD0,
HP59 MP74 ATK65 DEF70 AGI85 INT131 at level 1. The complete 85,603-frame
Wine replay passes to original Journal SHA256
`111a2214b78f69882ce8e0a0ddfe9d4391f2fb42511ec03b39b9686e7d3cd720`.
Party Derzo/Garon/Slash is level 26/1/25, full HP 178/59/155, with thirteen
owned monsters and 43G. Liset and Varli are consumed through original
breeding; twelve other identities persist through compaction. Scratch
`sky-quest-45` starts only from that genuine Journal and is training Garon.
No observational dump is used as a seed.

Production Windows run 40148371157 also passes the current direct 107-byte
quest comparison, all twelve original birth-21 monsters, later Journal Save,
two normal shutdowns and fresh-process Continue on the pinned production EXE.

The 29th original Journal trains Garon to level 17, HP174, with HealAll,
Increase and TwinHits; its 86,481-frame independent Wine replay passes.
The 30th route passes the smaller-disguise hole, explores the Sword dungeon,
retains original skill-forgetting choices, defeats Metabble (20 HP/999 DEF)
with all three alive and obtains Heaven Sword. It returns to the settlement
inn, rests for 10G and saves at world125 r0,0 x48,32 Down. Independent Wine
replay of 131,651 frames passes to original Journal SHA256
`94d024c3d3aa146f246136b0c7107d69b4a05bf67f784aaafbbe68344bccd06d`.
All sixteen monsters, quest107, inherited data, skills, keys, wallet33G and
inventory persist. Party Derzo/Garon/Slash is level29/24/27, fullHP184/188/157.
Scratch `sky-quest-47` starts only from that authentic Sword Journal and is
exploring Heaven Armor's platform maze. Original unlocked flight crosses the
black gaps; ordinary walking and B jumping did not. Only P1 changes game state.

Journal safety: verify that the original Plan menu actually offers Journal
before invoking the native Journal helper. Dungeons can offer Info instead
and refuse Save. Use a clear, stationary town tile facing an empty tile.
Keep original dialogue/recruitment visible; repeated identical dialogue can
need another A, and battle completion can lead into original naming.

ChangeStaff copies current-room NPCs. Pei region 1,0 includes Swordgon (43),
a shiny disguise. Cloud flight (unlocked flag 0x1E) uses A facing suitable
shore terrain, crosses gaps automatically, and lands on walkable ground;
its flight script pauses the disguise countdown. It does not use the boat's
persistent FF8C bit 3. The observed cloud route successfully reached the nest
with 53 disguise steps remaining. Scratch helpers issue only finite original
P1 commands; all game/runtime state remains original.

## Work sequence

Current authorization: continue through the whole original game and finish M8.
The user's later whole-game and "continue and finish" instructions supersede
the historical per-world stopping choices retained in the chronological record.
Keep progress reports and important screenshots current. The user also requested
breeding stronger monsters while reserving Squiz until his story role is complete.
Keep all further project-authored text in English.

1. Extend finite P1-only route support for complete battles and later Continue
   without assuming the introductory quest flags are still unchanged.
2. Extend original play through Oasis and subsequent worlds/systems, retaining
   checkpoints created by original Journal Save and replayable P1 transcripts.
3. Add only reached or directly required native banks/fragments; verify every
   runtime fix against retained exact regressions.
   An optional all-bank AOT build is now being tested to avoid repeated local
   compile interruptions during later-game discovery. Its complete static
   coverage does not replace original gameplay acceptance.
4. Prove the original ending/credits and late-game fresh Continue. Run all
   retained and new gates together; package and create final restore only then.

## Chronological discovery record

### English-language prerequisite (2026-10-18)

Project-authored Dutch text in the active M7 PowerShell validator and the
packaging launcher was translated. Validator changes are string-only and
PowerShell parsing passes. English README/report translations were added to
the previous output packages; original reports/logs remain historical evidence.
The separate `outputs/M7-English` package contains the accepted byte-identical
M7 game/save and a rebuilt English launcher. No original game text was changed.

### P1-only M8 tooling

`--m8-probe <save|-> <output>` starts a new runtime and original Continue.
It accepts appended commands from `<output>/commands.txt`. `--m8-resume
<save|-> <trace> <output>` reconstructs a session by replaying its recorded
controller inputs from a new runtime, not by loading CPU/WRAM savestates.
`--m8-replay <save|-> <trace> <output>` is the finite verification path.
New output directories are required to avoid overwriting traces/evidence.

Commands: button/hold/release, `walk DIRECTION frames [release]`, `battle`,
`flee` (still experimental), `talk [budget] [period]`, `journal UNIQUE_NAME`,
`snapshot`, `quit`. Only P1 changes game state; snapshots/assertions are read-only.
Journal requires original save acceptance, nonzero SRAM changes, field return,
then a fresh-runtime Continue comparison before reporting a checkpoint pass.
Movement stops when the original field leaves idle mode. Recruitment naming
requires explicit input rather than unlimited default confirmations.

`inspect_map.py` reads/decompresses the original map tables at bank-0
$19B7/$0CF5 and bank-17 $44B8. The observed Oasis region 1,0 graphics matched
all 360 runtime tile bytes exactly. This is read-only data inspection, not a
runtime CPU interpreter. No external game information was used.

`recomp/build/m8_oasis01` resumes original M7 Save through Continue. Its P1
transcript reaches Oasis and completes a real CactiBall encounter, returning
to world 0x20, region 1,0, position 0x10,0x50 at frame 10352. Subsequent travel
has reached region 0,1, position 0x50,0x40. This is route discovery, not M8
acceptance. Diagnostic mark/back are not valid acceptance fixtures.

Full M8 original-game playthrough and ending/credits remain unproven.

Subsequent pure-P1 discovery in `m8_oasis02` through `m8_oasis05` completed
another battle, recruited an original monster through the naming/Yes menus,
and reached the town at world 33, region 0,0, position 80,128, party size 2.
The full controller-only trace replayed from the original M7 SRAM with state
assertions. Outdoor Journal correctly says "You can't save here" and was
rejected. Town Journal changed 174 SRAM bytes, but the first helper attempt
ended in field-menu mode 1:2, not idle 1:0, and was therefore NOT accepted.
Menu-close retry support is being validated; no later-save pass is claimed yet.

### Verified first later checkpoint

The retry in `recomp/build/m8_oasis06` succeeded through original Journal,
then a new Runtime loaded only the resulting 32768-byte file. All 304 party/
inventory bytes and ten quest/location fields matched (zero mismatches).
Party size 2 is part of that 304-byte comparison. Final source frame 29449,
world 33, region 0,0, position 80,128. SRAM FNV `0x79f780ede66cc6d1`;
save SHA256 `BCD5CD10221F95A1C032579B1B315F9F60A084D4137AF8D38DF3DB899C32AB0F`.
This early-Oasis save is genuine later progress, not late-game/ending proof.

The pure controller/assertion transcript is pinned as
`tests/m8_oasis_town_p1.txt`. The new `M8_oasis_checkpoint` test regenerates
that progress from the accepted M7 Journal save, checks the exact checkpoint,
then verifies fresh Continue. CTest sets up that seed through the unchanged
M7 save/Continue test. `M8_trace_contract` checks twelve fail-closed/protection
cases; all twelve tool-contract cases passed independently.

The M1-M7 suite passed again in 131.07 seconds with the M8 driver compiled.
Both existing acceptance save hashes were preserved. A subsequent expanded
14-check run is in progress. The `check-m7` target continues to select exactly
the retained twelve tests; `check-m8-development` includes partial M8 checks
and does not certify full M8 completion.

### Inn code expansion

Original P1 conversation with the world-34 innkeeper reached missing native
41:$4001 (`m8_oasis06`, frame 29954, selector 0A), then 151:$4026 through
41:$4008 (`m8_inn01`, frame 2900 after fresh Continue). Both banks were added
to AOT because of those concrete failures, not guessed game coverage. Bank 41
compiled/linked; bank 151 is being compiled. No runtime fallback was added.
The failure traces contain an explicit non-replayable failure marker rather
than silently pretending the partial failed frame completed successfully.

Bank 151 compiled/linked and the inn welcome dialogue now executes. Continuing
that original dialogue reached 28:$4075 at frame 2993 (`m8_inn02`); this exact
native bank is being added next. Healing has not yet been proven.

The first expanded run passed every retained M1-M7 test and M8 tool contracts,
but failed the new Oasis test because the initial fixture capture itself had
been truncated. The fixture was regenerated with every one of the 29,449 P1
frames retained and redundant read-only assertions omitted. The corrected
finite native `--m8-oasis-test` then passed, reproducing exact original Journal
SRAM and fresh Continue. A combined all-green run is still required after the
new inn banks are linked. This failed run is not described as all-green.

### Inn proof and combined regression

Further P1 inn execution reached 240:$4001 at frame 2999 (`m8_inn03`).
Banks 28 and 240 were compiled and linked alongside 41 and 151. The inn then
completed in `m8_inn04`, frame 3580: original SRAM monster-record HP changed
18->25 (maximum 25), while the recruited monster stayed 16/16. No host writes
were used for healing. A subsequent original Journal inside the inn changed
38 SRAM bytes, produced an exact 32768-byte file, and passed a new-runtime
Continue comparison (304 party/inventory bytes, ten quest/location fields).

Inn checkpoint: frame 4924; world 34, region 0,0, position 80,80; party size 2.
SRAM FNV `0x520c04981e15a459`; save SHA256
`C42458D17E1B0EE448F771A44874DA0A906910DECA336DF0483D7786B0505697`.
Its full 4924-frame P1 trace is pinned as `tests/m8_inn_heal_p1.txt`. The new
`--m8-inn-test` requires the exact original town checkpoint, verifies healing,
replays the original Journal, and verifies fresh Continue. The Oasis CTest
driver now chains this inn proof after regenerating the town checkpoint.

Before adding this final inn-test chain, all 14 combined development checks
passed in 202.18 seconds (`m8-development-14-checks-03.log`). The updated chain
is being revalidated; that earlier green run is not passed off as a test of
unbuilt changes. The retained M7 acceptance saves still have their original
SHA256 values. There are now 49 registered native ROMX banks.

Original village dialogue identifies world 33 as Kalka. Observed NPC dialogue
mentions a thieving band and says it knows nothing about a navel plug. These
are original on-screen observations only; no external game guide was used.
The idle exploration session was cleanly quit. Resume actual progress from
`recomp/build/m8_inn04/oasis_after_inn.sav` using a NEW output directory:

```powershell
recomp/build/DWM2tRecomp.exe --m8-probe recomp/build/m8_inn04/oasis_after_inn.sav recomp/build/m8_next01
```

That is an original Save/fresh Continue, not a diagnostic savestate. Remaining
work still includes further Oasis progression, all later worlds/systems,
ending/credits, later-game saves, full acceptance and final release/restore.

## Current verified development checkpoint (2026-10-18)

All 14 combined tests, INCLUDING the final inn-healing/second-Journal/fresh-
Continue chain, passed in 260.97 seconds. Evidence:
`recomp/build/m8-development-14-checks-04.log` and
`recomp/build/Testing/Temporary/LastTest.log`. The regenerated inn save is
byte-identical to the observed original checkpoint (SHA256 C42458D1...05697).
Both existing M6/M7 acceptance saves retained their original hashes.

The packaged development EXE is Windows x64 (PE machine 8664), 233263104 bytes,
SHA256 `EDC52071A4A229AEB1E853594F7B374DFE1A5A9182204BE347C13BBB7DF56774`.
`outputs/M8-development` contains that exact binary, a separate original inn
test save, English instructions, and the local test report/evidence. The
package EXE additionally passed M3/M4 self-tests. It is NOT the final release.
The M7 English validator cleanup is commit `890f5f1`; M7 restore remains
`3bb1e18170fc928f372f9cc72cc433d85c0666ca`, also checked remotely.

Full M8 is still incomplete. No ending/credits proof, `M8_RESULT.md`, or
`restore/recomp-m8` exists. Do not describe these 14 partial development tests
as final M8 acceptance or as a successful hosted GitHub Actions run.

### Asiya/canal development evidence (ongoing)

The original king's request, the town well complaint (selector 0F), the report
to the king, the canal-manager scene in world 42 and walking into the canal
(world 43) all executed. New original Journal checkpoints passed fresh
Continue for 304 party bytes, 56 quest-flag bytes and five location fields:

- `m8_asiya05/asiya_king_request.sav`: FNV `3b7c45f1713eb77e`,
  SHA256 `2CA33149B19F9CF0B2CAFD8A139B7A1B75CFFCC33C63C5F6E0663F0B6A76224A`.
- `m8_asiya06/asiya_water_reported.sav`: FNV `e5873b72c24a1e6a`,
  SHA256 `C6FAE888C6100528C5408C67B259E28F2F1B550BF3FA66F227D07631748270EB`.
- `m8_asiya06/kalka_canal_preparation.sav`: FNV `3de20fbe8f08b6c3`,
  SHA256 `BFD205B39C77C7B21BDDD0DB310ED6BF36F8969D833E7514A17FF736A80F6E5F`.
  Original inn healing restored all three monsters to 33/33, 21/21, 17/17.

The dam creature is at world 43, region 1,2, position 48,96 (selector 37).
Original confrontation produces a real mode-4 battle with enemy HP 98.
Its Fight command reached 226:$5426, which directly calls 5:$772B; both
native banks were added. `m8_dam01` replayed all 28,353 entry-route frames
and proved enemy HP 98->85->76->68->56->52 and party damage. The underprepared
party lost and the original defeat return executed. This is NOT a passing
boss milestone. Subsequent retry/flee experiments do not claim victory.

All 14 combined local development tests passed in 188.21 seconds after banks
5/137/149/226 and the 56-byte quest check (`m8-development-dam-14-checks-01.log`).
Existing M6/M7 acceptance saves retained their exact hashes. This result
predates bank 30 and the later checkpoint/creature-stat test extensions.

`m8_training01` earns normal battle experience near the Kalka canal entrance,
returns to the inn before the weakest member dies, and uses original Journal
after each cycle. Three separate 32768-byte saves and fresh Continue passed:
`training_cycle_01.sav`, `_02.sav`, `_03.sav` (last FNV `e3ed777cd9f7c95d`).
Further combat raised Slash and the second monster to level 3 and produced
another original recruitment offer. The original send-to-farm > Info menu
reached 30:$7163 at frame 39569. Bank 30 was added; `m8_training02` replays
the complete 39,568-frame prefix before trying Info again. No farm exchange
has yet been confirmed. No world or important boss has passed yet, so the
user's milestone pause has not been triggered.

Three finite P1 fixtures now pin inn->Asiya, recruitment/castle/king Journal,
and water-report/canal-preparation Journal (7194/26188/15883 frames). The M8
CTest driver chains these after its retained Oasis and inn proofs using
`--m8-checkpoint-test`. Fresh Continue additionally checks each active
monster's persistent status/level/experience/HP/MP/stats (22 bytes per member).
The expanded 14-check run is in progress in
`m8-development-asiya-chain-14-checks-02.log`; do not claim it passed yet.

## Continuation from tested 0e2b236

The executable and original inn save hashes matched the tested baseline before
new work. `m8_next01` follows original village dialogue south through Oasis to
Asiya (world 36) and its inn (world 35). The original Journal there produced
32768 bytes; fresh Continue matched the checked party/quest/location fields.
Save: `recomp/build/m8_next01/asiya_arrival.sav`, SHA256
`E1366BBCCBB10F563B5F1E5779905A37D689B04605B7395257775742BB5903D1`.
This is another early-game checkpoint, not world completion.

Original NPC dispatch 4:$63ED requires three healthy party monsters before
the circus route can progress; the current party contains two. Original text
and map/NPC tables are being used to find that route, not an external guide.
An actual information-menu execution reached 149:$4650 (`m8_next01`, frame
8780), so that native bank is being added. No missing-bank failure is counted
as a pass, and no host-written party/quest state is used to bypass the gate.

### Three-monster party and castle entry

Bank 149 compiled and linked. From the Asiya Journal seed, `m8_asiya03`
records two real field encounters. The second produced an original recruitment
offer; A/name, Start/END, A and Yes completed it. Party count changed 2->3 at
frame 9672, without host-written party state. The returning party's original
Journal changed 127 SRAM bytes and produced `m8_asiya03/asiya_party_three.sav`
(32768 bytes, FNV `2b63a58fb2c71006`, SHA256
`A9B92496C5C73F94566FADA517BF89EF42DD002C3CAB523BA762DB4C49818A8E`).
Fresh Continue passed; a read-only comparison also found no differences in
the full 56-byte quest-flag block. M8 Continue verification now explicitly
checks those 56 bytes plus five location fields and 304 party bytes. M7's
acceptance implementation and fixtures are unchanged.

The original circus gate accepted the living three-monster party, transferred
it into castle world 37, and original walking reached the throne room (38).
Talking to the king reached missing native bank 137:$4001 at frame 22821.
That bank was compiled and linked. This is not boss/world completion.
The first replay-extraction attempt accidentally omitted B holds and correctly
failed its screen assertion. The corrected prefix retains all P1 buttons,
ends at frame 22621 before the failed story command, and is being replayed in
`m8_asiya05`. No failed trace is presented as a passing result.

## Latest stopping point: dam-boss victory (milestone decision required)

This section supersedes the earlier ongoing-work notes above. The king's
canal/dam creature has now been defeated through original P1 gameplay.
Training and the original recruitment/farm exchange produced a stronger
party. The existing level-6 CactiBall was sent to the original farm, not
deleted; the new recruit joined the active party. Bank 30's Info path passed.
`m8_training02` reconstructs all earlier training by P1 replay from the
preserved canal-preparation Journal save, not from CPU/WRAM snapshots.

Scripted battle: frame 52036, world 43, region 1,2, position 32,96,
selector 37, mode 4, party HP 30/24/24, boss HP 98. Normal Fight turns
reduced boss HP 98->78->50->33->13->0 by frame 55037. All three members
survived (9/16/24 HP). Original rewards/level-ups and post-fight dialogue
completed; CBE1 changed 00->18 (quest flags 0x53 and 0x54). No subsequent story
objective was started. Returning to Kalka included one normal field battle,
original inn healing and PLAN > Journal.

Victory save: `recomp/build/m8_training02/dam_boss_victory.sav`, exactly
32768 bytes, original Journal changed 52 bytes, FNV `51c23bf4c4399ebc`, SHA256
`400DF427C538F0776C1F9066813EC90005E20D78EB8FF2C11AACBC13D3DA29CE`.
Original route ends at frame 66305, Kalka inn (world 34, region 0,0, 80,80).
Fresh Runtime Continue passed with zero mismatches in 304 party bytes,
56 quest-flag bytes, five location fields and 66 persistent creature bytes.
The active party is healed; all older saves remain separate.

`tests/m8_dam_boss_victory_p1.txt` retains all 66,305 controller frames and
asserts battle-entry HP 98, boss HP zero with every member alive, and the
final flags/Journal/screen hashes. Independent `--m8-checkpoint-test` replay
passed in `recomp/build/m8_boss_regression01`, reproducing the byte-identical
victory save and another fresh Continue. This route is now chained after
the three Asiya/canal fixtures in the development CTest driver.

All 14 development gates including the three Asiya/canal fixtures and the
66-byte creature comparison passed in 279.90 seconds before adding the final
boss fixture (`m8-development-asiya-chain-14-checks-02.log`). The final retained
suite rerun passed all 14 checks in 292.99 seconds
(`m8-development-dam-victory-14-checks-03.log`). This run used the earlier
three-story-route test list: the initial terminal reconfiguration lacked the
Visual Studio environment, was corrected, and the independent new boss gate
passed. The final registered four-story-route M8 CTest chain passed separately:
both M8 tests passed in 287.94 seconds (`m8-complete-dam-chain-checks-04.log`).
It regenerates every seed from the accepted M7 Journal and retains 149,943
recorded P1 frames across all six M8 routes, plus separate fresh Continue
verification. The final victory save is byte-identical to discovery and
the independent boss replay. Do not describe
the 292.99-second run as already including the newly registered boss route.
No result here is a hosted GitHub Actions pass or full M8 acceptance.

A separate Windows-x64 development package is in
`outputs/M8-dam-boss-checkpoint`, with an independent M8-test.sav, untouched
evidence/original-journal.sav, English launcher/instructions and evidence.
EXE SHA256 `4AEBA6723D4C4D47D7AD4135C2B3CB5D7AAE54C1E62FB31A8D47529660CC172B`;
255736832 bytes; PE machine 8664. The packaged binary passed M3/M4 self-tests.
Do not replace the user's earlier output packages or saves.

STOP gameplay at this fully working important boss milestone and ask whether
to continue immediately or stop for now. Wait for the user's explicit answer.
Remaining scope: the rest of Oasis, later worlds, ending/credits, later saves,
all regressions/final release. Do not create restore/recomp-m8 or M8_RESULT.md
or describe M8 as complete. M7 restore stays 3bb1e18170fc928f372f9cc72cc433d85c0666ca.

## Approved continuation after the dam milestone (2026-10-19)

The user explicitly chose "Continue immediately" in the milestone dialog.
The pause above is therefore satisfied. Continue from commit `9a3e86a` and
the original dam-victory Journal, preserving both and all earlier saves.
Pause again at the next completed world or fully working important boss.
First follow the king's original invitation; no later story outcome is
claimed until its gameplay and original Save/fresh Continue are verified.

### Asiya thieves report and original WaterCall exchange (2026-10-19)

From the dam-victory Journal, original travel, king dialogue and Journal
produce `m8_after_dam01/asiya_thieves_report.sav` (32768 bytes, FNV
`25b3f7391031727c`, SHA256
`BEA17C3F71AC891AC8F07B9067D942C69885CD72D1765A6A502B5BBDB259320E`).
The king's expedition changes CBE1 from 18 to 78. The pinned 12,869-frame
fixture `m8_asiya_thieves_report_p1.txt` independently reproduces that save
and fresh Continue with zero mismatches.

The prison stairs work through original movement. No-food dialogue correctly
refuses the exchange. The Asiya item shop (selector 12, town region 0,1,
128,32) sells BeefJerky for 10 gold; the purchase reduces 30 gold to 20.
The church is selector 17, NOT the item shop: use actual game screens to
resolve service identity rather than assumptions from adjacent text IDs.
The original church menu reached 36:$60DB; bank 36 is statically compiled.

Giving the purchased food to the starving prisoner grants WaterCall and
sets quest flag 57 (CBE1 78->F8). Original town Journal produces
`m8_mirage02/watercall_original.sav`, exactly 32768 bytes, FNV
`5fe465082e40e700`, SHA256
`E66FB1B2FBE7FAA5E68922CEBDE80A02284770BE2C455D353E67821A531EAE5E`.
Its 20,511-frame fixture `m8_watercall_exchange_p1.txt` independently
replays from the thieves-report save and passes fresh Continue, checking
304 party bytes, 56 quest bytes, 5 location fields and 66 creature bytes.

M8 snapshots now retain cumulative original APU sample count, nonzero count,
peak and PCM FNV. `expect_audio` validates exact replay without changing
cartridge state or the existing sample drain point. All 17 trace contracts
pass; the WaterCall fixture includes its final audio hash.

All 14 local CTest gates, including all unchanged M1-M7 checks and the complete
eight-route M8 checkpoint chain, pass in 448.12 seconds
(`recomp/build/m8-watercall-all-14-checks-01.log`). This is local evidence,
not hosted CI. The M6/M7 original saves were copied to the unique directory
`recomp/build/preserved-before-watercall-validation-01` before that run.

Ongoing `m8_lake01`: follow the original mountain pass to the east/south of
Oasis, enter Mirage Lake (world 47). WaterCall Use at a wrong position
correctly says nothing happened. At world 47 region 0,1, 80,64 facing Up,
normal Use consumes WaterCall, sets quest flag 58, and reveals the hideout.
Do not confuse the lake water with an entrance: the hideout is northeast,
world 47 region 1,0, 64,48. Normal movement reaches world 40 region 0,1.
The hideout conversation (selector 3C) enters a real battle and reaches
missing native bank 59:$40CD at frame 15221. No victory is yet claimed.
Bank 59 is being compiled; replay only the safe P1 prefix ending at frame
14089 (`recomp/build/m8_lake_prefix14089.txt`) from the WaterCall Journal.
No CPU or WRAM state is restored. The next proven important fight still
requires the user's milestone pause before further story progression.

## Latest milestone: Oasis completed; user decision required (2026-10-19)

This supersedes the earlier ongoing lake notes, not their historical evidence.
Banks 59 (battle path) and 39 (original recruitment naming) compile statically.
The original CurseLamp fight is proven in `m8_lake02`: frame 15491,
world 40 region 0,1 at 64,32, mode 4, enemy HP 220 and party HP 48/35/30.
Normal Fight turns reduce enemy HP 220->194->164->124->105->75->30->0.
At frame 19818 every ally survives with HP 3/35/7.

The original APU emits 4,747,802 sample values between the pinned entry and
zero-HP checkpoints, of which 4,632,796 are nonzero. Both exact cumulative
audio hashes are asserted. This proves deterministic original digital audio
activity, not a subjective listening assessment. The M7 audio gate remains
unchanged.

Original naming supplies the automatic nickname Phes for the recruited
CurseLamp; original No/Send to Farm preserves the three active monsters and
stores the recruit at record 4. Existing farm creatures are not deleted.
The original defeat dialogue and quest aftermath complete automatically,
set CBE2 to 07 (flags 58/59/5A), and return the party to the Navel chamber
(world 5 region 1,0 at 80,48). The original scene heals HP to 60/40/32.
No next world or later boss has been started.

The first attempted Journal was incorrectly facing Warubou. It stopped
safely at newly reached bank 42:$4001, before any save was claimed. Bank 42
is now compiled. The successful route replays only the safe P1 prefix before
that interaction and faces an empty tile instead; it does not continue
Warubou's next objective or load any CPU/WRAM state.

The successful original Journal is
`recomp/build/m8_lake04/oasis_curselamp_victory.sav`: 32768 bytes,
201 changed bytes, FNV `dd87953eae7f0643`, SHA256
`BD09E51673BE26BD0B21BE7AC78FFD86F621F6D4D8361CD3A60D8F17832DFBB9`.
Fresh Continue passes 304 party bytes, 56 quest bytes, 5 location fields and
66 active-creature bytes. An additional read-only comparison verifies all
110 persistent bytes (55..6A) across all five occupied creature records,
including the two farm creatures. Continue changes four original name-cache
padding bytes in record 4 (15..18), not those persistent creature fields.

`tests/m8_oasis_curselamp_victory_p1.txt` retains 30,639 P1 frames and the
actual battle-entry/zero-HP/audio assertions, final quest/location/Journal
hashes and final PCM hash. The independent checkpoint replay passes and
reproduces the byte-identical original Journal, plus another fresh Continue
(`recomp/build/m8-oasis-victory-independent-01.log`). The final full CTest
run passes all 14 checks in 507.86 seconds, including the complete nine-route
chain in 390.34 seconds (`recomp/build/m8-oasis-complete-all-14-checks-02.log`).
Its final Journal is byte-identical to discovery and independent replay.
The chain retains 213,962 recorded controller frames from the accepted M7
Journal. No external game information or fabricated game state was used.

A separate package is in `outputs/M8-Oasis-complete-checkpoint`: copied
Windows-x64 EXE, untouched evidence save and separate M8-test.sav, English
launcher/instructions/test report. The copied EXE passes M3/M4 self-tests
and independently replays the full boss route plus fresh Continue, again
reproducing the byte-identical save. EXE SHA256
`06E47C07A43D3C01FF1429A7299868BACDC9F4E0D058DD0BDA75A589C67EDE04`,
274321408 bytes, PE machine 8664. No hosted CI pass is claimed.

STOP at this fully working major boss and completed world. Finish only
milestone verification, packaging and evidence/commit work, then ask whether
to continue immediately or stop for now. Wait for the user's explicit answer.
M8 remains incomplete: later worlds and ending/credits still require proof.
Do not create restore/recomp-m8 or M8_RESULT.md. The immutable M7 restore
remains `3bb1e18170fc928f372f9cc72cc433d85c0666ca`.

## Approved resume: reported audio and enemy-feeding failures (2026-10-19)

After first stopping at Oasis, the user explicitly approved resuming M8,
fixing the playback warning, missing bank 61 and enemy meat feeding, retaining
all regressions, and providing a revised test build before later-world work.
The earlier stop is lifted. The next completed world/important boss still
requires an explicit continue/stop decision. Keep everything new in English.

The user's modified testing SRAM is preserved separately at
`work/M8-user-save-preserved-20261019-01/user-current-test.sav` (workspace-relative,
outside this repository), SHA256
`2255D149CD66E597EBDCDC79BF063B551D05ACD9FE47F1EFBEFF6F22FE3993A2`.
The original accepted Oasis Journal remains byte-identical. A fresh Continue
of the user's file succeeds at the same home checkpoint. Do not overwrite
the user's current testing copy or the earlier output packages.

### Reproduced host-audio cause and correction

Local Windows reports 11 WinMM playback devices and running audio services.
WAVE_MAPPER fails with MMSYSERR_BADDEVICEID (2), even at 32768, 44100 and
48000 Hz. All eleven explicitly enumerated devices open successfully at
the original APU rate, 32768 Hz. Therefore "no playback device" was an
incorrect diagnosis: the default mapper fails, not the actual outputs.
No Windows system audio settings have been changed.

The production WaveOut sink now tries explicit devices after a failed
default mapper, logs the actual error/device, and supports an explicit
`--play [save] --audio-device N` override. `--audio-devices` lists outputs.
Six pure host-selection contracts cover mapper success, fallback to first
or second available device, no devices, all-open failure and explicit-device
failure without silently switching to a different output.

`--audio-playback-test` generates PCM from original cartridge execution,
submits nonzero samples through the production sink, and checks the Windows
playback position. Automatic fallback to device 0 (Sonar Gaming) and explicit
device 9 (Arctis Nova 7 headphones) both pass: 16458 nonzero sample values
submitted, 8229 stereo frames played. This is real output-device/queue
evidence, NOT a subjective hearing claim. Logs:
`recomp/build/m8-audio-fallback-playback-01.log` and
`recomp/build/m8-audio-headphones-playback-01.log`.
No APU generation/timing or M7 audio acceptance constants were changed.

### Reproduced enemy feeding and native bank fix

The preserved pre-fix EXE `recomp/build/DWM2tRecomp-2c37720-diagnostic.exe`
replays an original purchase of BeefJerky from the thieves-report Journal.
Actual battle ITEM > BeefJerky > Enemy reproduces exactly the user's failure:
`m8_meat01`, frame 17008, missing bank 61:$4001, original action D801=2C.
Bank 61 is now statically compiled; no runtime interpreter is introduced.

`m8_meat02` replays only the safe P1 prefix to frame 16886, executes the
original throw animation, consumes item 19 and increases the original
feeding/recruitment value D89F:D8A0 from 10 to 20. Original bank 59:$4934
looks up item 19's +10 value at $4949 and adds it at $4953. This is not a
guaranteed-recruitment modification. The original battle then finishes.
Returning to Asiya and using original Journal produces
`recomp/build/m8_meat02/enemy_meat_verified.sav` (32768 bytes, 90 changed,
FNV `eea0f1d399fac8f8`), with passing fresh Continue.

`tests/m8_enemy_meat_p1.txt` retains 19508 controller frames, before/after
inventory and feeding-value assertions, exact original audio hashes, and
the final Journal. The development driver now runs this as an isolated side
branch after the thieves-report checkpoint (story-05), leaving the main
Oasis completion chain unchanged. Independent replay and the new 16-check
full suite are being verified; do not claim those results prematurely.

Ongoing later-world discovery uses a separate diagnostic copy of the EXE
and accepted Oasis Journal, not the user's testing save. In world 5 the
actual exit corridor is east: region 2,0 at 80,0, not the chest/rock graphics
in the western chamber. `m8_home_next02` records all discovery P1 input.

### Audio/meat correction fully validated and separately packaged

Commit `65c7d7f23948ecd23778981ad4cb5e7b45545fa5` is pushed. Its unchanged
59-bank EXE passes all 16 local checks (no skips) in 669.19 seconds.
The complete original M8 chain including the feeding side branch passes in
523.10 seconds. Log: `recomp/build/m8-audio-meat-all-16-checks-01.log`.
The regenerated feeding Journal is byte-identical to discovery and the
independent/packaged replay (SHA256
`7828354F1A28E017B62959DEF2C5DB3144B93D71F3D1E4EE7C351C7961B153CB`).
M6/M7 validation-save hashes and the M7 restore are unchanged.

The separate `outputs/M8-audio-meat-fix` package and
`outputs/DWM2t-M8-audio-meat-fix-65c7d7f.zip` contain the validated EXE,
a copy of the user's current save, normal and direct-Arctis launchers,
English report/source record and local evidence. EXE is 279242240 bytes,
SHA256 `48892CA617819F61080F830127E909524D9A8C2C9C6A3BEFE68993AEB3850B99`.
The copied EXE independently passes original meat use/Journal/fresh Continue
and real headset output. No subjective hearing or hosted CI pass is claimed.

Later M8 work is separate from that frozen 59-bank executable. The home-hub
event reached bank 152:$404B, which is now statically compiled in the
development EXE `recomp/build/DWM2tRecompNext.exe`. CMake supports optional
`DWM2T_OUTPUT_NAME` (default DWM2tRecomp) to avoid replacing an EXE while a
long regression run still uses it; the local cache currently selects
DWM2tRecompNext. The original DWM2tRecomp.exe and packaged fix remain frozen.

Original post-Oasis hub event completed and sets CC07 bit 7. The game's
dialogue announces a royal tournament for child monster masters and invites
the farmer's child; its prize is being read in a separate P1 dialogue replay.
`m8_home_next03/post_oasis_home_event.sav` is a successful original Journal,
32768 bytes, FNV `d5374bb11f3cdd70`, SHA256
`4058A37DC9FBED49C07717AF8C465C4E3FD1FE64898588A59D562E3577087713`.
The 9251-frame `tests/m8_post_oasis_home_p1.txt` independently replays and
passes fresh Continue (`m8_home_regression01`). This route is appended to the
working CMake chain but was NOT part of the frozen 65c7d7f 16-check run.
It is a smaller technical checkpoint, not a completed later world/boss.
Continue toward the tournament; do not pause merely because the fixes pass.

### User listening feedback and unclipped, quieter host playback

The user confirms that the normal 65c7d7f launcher is audible, but reports
excessive volume and a "crispy" sound. No system settings were changed.
Investigation of an original P1 key-shop visit finds actual legacy mixer
saturation, not just device selection: premix peak 35328, 1768 sample values
outside signed 16-bit range. Do not claim this explains every possible
headset/driver artifact or establishes hardware-perfect sound.

APU sample timing and channel state remain unchanged. Its existing private
sample vector now retains the exact small integer mix before the old x96
conversion; no class layout is changed. `take_samples()` performs the same
legacy scale/clamp and retains the exact M7 and M8 capture hashes.
`take_playback_samples()` exposes the unclipped x96 mix to host presentation.
Live output applies adjustable gain before 16-bit conversion, default 25%,
and a mild one-pole smoothing filter; `--audio-raw` disables smoothing.
`--audio-volume 0..100` adjusts only this game's playback. At excessive user
gain the final converter still saturates safely; default gain has headroom
for the full possible original mix. No synthetic sound replaces game audio.

`tests/m8_hub_audio_p1.txt` retains the original key-shop input and exact
legacy audio hash `865ab37c80553b36`. `m8_hub_audio_range01` passes original
P1/memory/screen/PCM assertions with output peak 8831 and zero output clipping.
The new host contracts cover exact raw conversion, gain/mute, independent
stereo history, filter decay, pre-conversion headroom and bounded saturation.
The complete checkpoint driver now tests this as another isolated side branch
from story-08 (the post-Oasis home Journal). Its finite timeout is 900 seconds
to accommodate the longer chain; per-frame/P1 runtime guards are unchanged.

The preliminary 17-check comfort build passes all checks, no skips, in
604.60 seconds (chain 472.47 seconds). This is NOT the final pre-conversion
build: `DWM2tRecompDev2.exe` is now undergoing the expanded 17-check suite
including the real loud-music side branch. Log names end in `checks-01.log`
for preliminary and `checks-02.log` for final; do not confuse these results.
The original frozen 65c7d7f package and all saves remain untouched.

Original hub discovery confirms the tournament prize is PirateKey. The key
shop (world 9) and bank (world 8) have been visited through ordinary P1 input;
neither is a completed world or major boss. Discovery probes are not acceptance
evidence for winning the tournament. Continue from the saved home event.

Final clipping-corrected 60-bank EXE from commit `4a91cfb` passes all 17 local
checks with zero skips in 751.16 seconds; M8 chain is 591.21 seconds. Evidence:
`recomp/build/m8-audio-comfort-all-17-checks-02.log` and CTest LastTest.log.
Full driver output `local-validation/m8_oasis/oasis-aq06bhf2` retains byte-identical
home Journal SHA256 `4058A37D...577087713` and feeding Journal `7828354F...961B153CB`.
M6/M7 validation-save hashes and M7 restore remain unchanged. This is local
evidence, not hosted CI or final M8 acceptance. Updated separate package:
`outputs/M8-quieter-audio-test`, EXE SHA256
`D6F7610C8EC341242C0DCF285F1E35F5E670A9AFE461411730FF60EDE939EA5B`.
Normal 25%, quieter 15% and raw-comparison launchers share only their own
copy of the user's original testing save. Packaged direct-headset output passes.

Hub navigation discovery `m8_tournament04` proves the southern forest path
from world 1 region 0,2 at 64,128 exits into harbor world 2. Crossing its
boardwalk east reaches the original farm district world 0. Taking the north
forest exit returns to world 1 region 3,2 at 64,128. No story victory is claimed.
The original castle-road NPC (selector 20 at world1/region1,1/80,32) currently
blocks the single terrain connection to the upper hub. Its observed dialogue
is "This leads to GreatLog Castle!". Investigate original movement/interaction
instead of bypassing the NPC or fabricating access. No current save is lost.

### Further listening feedback, streaming diagnosis and reference-only tooling

The user reports that even 15% remains loud and distortion is only slightly
reduced. Subjective audio quality is NOT resolved. Existing 4a91cfb package
now has additional 5% and 1% amplitude launchers, with its EXE/save untouched.
The next development build defaults to 5% and prebuffers 1638 stereo frames
(about 50 ms) through WinMM Pause/Restart. It refills after a drained queue
without stalling or altering the emulated CPU/APU clock.

`m8-buffered-audio-stream-01.log` isolates the actual Windows stream using
180 captured frames of original cartridge music. With injected 20 ms host
jitter, the old immediate-start stream has two queue-empty events. Buffered
playback has zero; all 98753 stereo frames are submitted and played in both.
This diagnoses host-queue robustness, not subjective fidelity or physical
speaker output. New `M8_audio_stream` is serial, has a 60-second limit and
joins the expanded 18-check suite, currently running on DWM2tRecompDev3.exe.

A separate PyBoy 2.8.1 diagnostic install exists only in task work/
`m8-reference-tools`, not the repo, EXE, packaging or native runtime. The exact
owned ROM was reconstructed by the repo's rebuild.py and matches SHA256
`8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e`.
Reference runs load only a copy of the original Journal through BytesIO,
use controller buttons, record observations and stop without saving. No
CPU/memory writes, save states or interpreter fallback are used in the game.
Reference-gate01 is invalid (title mode was observed before intro completion).
Reference-gate02/03 correctly restore the field and reproduce the same guard
block with cardinal, Up+B and diagonal input. No native gate fix is justified.

Warubou's original post-Oasis conversation says to find the next key first,
in GreatLog. `m8_tournament06` uses the original lower-town shrine entrance
to world 12, then its altar-side passage into world 4 region 2,0. Continue
reading original hall dialogue rather than assuming the blocked castle road
is the only route. These are technical/navigation checks, not major milestones.

### Buffered audio accepted; hall discovery and complete static build

The user tested the buffered `1f6a45a` package and confirms: "Better with both.
The normal version is fine." Keep the normal 5% playback default, unclipped
pre-conversion gain and 50 ms WinMM prebuffer. This is subjective comfort
confirmation for the user's PC, not hardware-perfect sound certification.
Its exact 60-bank EXE passes all 18 local checks, no skips, in 697.23 seconds;
the original M8 checkpoint chain is 557.75 seconds. Evidence:
`m8-buffered-audio-all-18-checks-01.log` and the preserved
`m8-buffered-audio-60banks-LastTest-01.log` under `recomp/build/`.

Original hall NPC selector 66 reaches 44:$4001, now statically compiled in
`DWM2tRecompDev4.exe` (61 banks). All 18 local checks pass, no skips, in
1115.52 seconds while another compilation runs; chain 574.28 seconds.
EXE SHA256 `4ED5FD0BFBECFBA68E9BE0D7571AE2E1ABD772C9D07CAF8D77238A6D0C4E3891`.
Logs: `m8-bank44-all-18-checks-01.log` and
`m8-bank44-61banks-LastTest-01.log`. These are local results, not hosted CI.

`m8_tournament07` reconstructs the post-Oasis home Journal by original P1
replay. The southern room in world 12 enters world 4's right-hand hall. Its
side exit reaches the ground floor of world 24; its central exit reaches a
railed viewing platform instead. Ordinary NPC dialogue describes arena
entry fees/classes, Magic Key prizes and appraisal. No tournament win or
new major-boss/world milestone has been proven. Do not bypass castle-road
NPCs or infer a native bug from a blocked route.

`DWM2T_ALL_ROMX=ON` in a separate ignored `recomp/build-all` tree compiles
all original ROMX banks 1..255 plus fixed bank 0. The current local Ninja
build uses four jobs because of limited free RAM. This changes static code
coverage only, not game rules, acceptance or runtime architecture. Build,
link and regression results remain pending; do not claim complete coverage
or publish its EXE until verified. Full M8 remains incomplete.

### Complete AOT build and verified Kids Class milestone (2026-10-19)

The complete static build has linked successfully: 255 ROMX banks plus fixed
bank 0, no runtime instruction interpreter. `recomp/build-all/DWM2tRecompFull.exe`
is 725316608 bytes, Windows x64; SHA256
`907AE15F735C2F8FAE4A6156C5E145E840BB34EE4F3CD2B58119C4A018627066`.
Use this build tree for subsequent M8 discovery rather than the frozen older
61-bank development EXE. The initial all-bank run passes all 18 tests, no
skips, in 636.41 seconds (M8 chain 493.93 seconds). Evidence:
`recomp/build/m8-complete-aot-all-18-checks-01.log` and
`recomp/build/m8-complete-aot-255banks-LastTest-01.log`.
Regenerated home/feeding saves and retained M6/M7 save hashes are unchanged.

The actual Arena enrollment counter is world 4 region 1,0, player 64,48
facing north. NPC selector 65 welcomes the player and accepts Kids Class;
the nearby ground-floor selector 61 gives class/opponent advice only.
The earlier castle-road block was not bypassed and no game rule was patched.

`m8_tournament10` starts from the exact post-Oasis home Journal and records
three original mode-4 rounds in world 11. All three enemy HP values reach zero
in each round. Final-round party HP is 25/4/0: CactiBall legitimately faints;
the original Arena aftermath restores all three to 60/40/32. Do not describe
the final battle as an all-members-survived win. Separate P1 reconstruction
`m8_tournament11` records the original victory pages: "The winners are Master
CobiA and the fun friends!" and "You've won the Kids' Class!". Arena class
C82C changes 0->1. PLAN > Keys shows Pirate, described as the key to Sea World;
the original rules explicitly name PirateKey as the prize. No Pirate-world
entry, later tournament or subsequent story objective has been started.

Original GreatLog Journal: `m8_tournament10/kids_class_victory.sav`, exactly
32768 bytes, 25 changed, FNV `c13e0658b2e3cb22`, SHA256
`A48FB7B52D6B5063F03725D205F96964174B44AFBB3600782892BA44CAEAA91A`.
Final source frame 27075, world 1 region 2,2 at 64,80. Fresh Continue matches
304 party/inventory bytes (including key state), 56 quest-flag bytes, five
location fields and 66 persistent creature bytes, zero mismatches.

`tests/m8_kids_class_victory_p1.txt` retains every one of the 27075 P1 frames,
selected original battle HP/quest/screen/audio assertions, class/prize state,
and the original Journal. Independent `--m8-checkpoint-test` passes in
`m8_kids_regression01`, reproducing the byte-identical save and fresh Continue.
Log: `recomp/build/m8-kids-independent-replay-01.log`.
The route is appended as story-09 to the complete M8 CTest chain. The final
combined 18-check run including it PASSES, zero skips, in 610.50 seconds;
the extended M8 chain passes in 479.62 seconds. Evidence:
`m8-complete-aot-kids-all-18-checks-02.log` and
`m8-complete-aot-kids-255banks-LastTest-02.log` under `recomp/build/`.
The regenerated story-09 Journal is byte-identical to the original victory
save and independent replay. This chain contains eleven main Journal routes
and the retained feeding/audio side branches. Do not confuse it with the
earlier all-bank 18-check run that predates the new tournament route.

The copied package EXE independently passes M3/M4 self-tests and fresh
Continue from both the user's test-save copy and the tournament save. Its
original PLAN > Keys menu also shows Pirate after the fresh boot. Earlier
saves/packages and the M7 restore remain unchanged. A diagnostic replay on
the older 61-bank EXE fails closed at 242:$6692; an experimental 62-bank
diagnostic then reaches missing 12:$659F. These are NOT passing builds.
The tested 255-bank EXE contains both and is the package/primary M8 build.
The smaller default set remains at its proven 61-bank scope, with the earlier
Oasis/home chain. The extended Kids Class route requires DWM2T_ALL_ROMX=ON;
CMake explicitly prints which coverage is selected. This does not change
the all-bank command/route list that passed the final 18-check run. Do not
use the limited development EXEs for later-world manual testing.

Final configuration audit compares the complete AOT checkpoint command's
ordered arguments to the recorded passing LastTest command: identical. The
limited configuration excludes the new route explicitly. A final Ninja build
reports no work, and the full EXE retains SHA256 907AE15F...8627066. The local
limited cache selects `DWM2tRecompLimited.exe`, a byte-identical copy of the
previously validated 61-bank Dev4 EXE; all older named EXEs remain preserved.

This is the next important tournament/boss checkpoint. Story progression is
stopped here pending the user's explicit continue/stop decision. Remaining
work is technical validation/packaging of this checkpoint only. M8 remains
incomplete; later worlds and ending/credits are unproven. Keep the M7 restore
immutable and do not create an M8 result or restore branch yet.
