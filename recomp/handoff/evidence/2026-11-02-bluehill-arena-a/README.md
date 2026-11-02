# BlueHill funding and A Class attempts

On 2 November 2026 the original game was driven with controller inputs in the full-ROM R4 diagnostic under Wine. The diagnostic executable SHA-256 was `61a0e6d3ff84b5322b101247fc93ff6889f123a1bcd94df663135757fb3b9855` and the game source was `1351bcd058e491455a477045a2ff86bbc3bd7b1c`. The independent input was the original BlueHill Journal SHA-256 `91d52195a0a82e69bf5991c7e519aed888da4f50b7286ddb6f60b691ba6fc606`, containing the strong Garon/Slash/Derzo party and 106G. This Journal belongs to the 386G recipient of the original key trade, not to the earlier B-champion donor. Its Arena status was checked separately. Original controller input and read-only observations were used; no game memory, RNG, money, item or save bytes were injected. Squiz was not used or bred.

## PltnmCape and funding

The player traversed the original BlueHill type-4 dungeon and reached its third level. Its original chest awarded [PltnmCape](cape-obtained.bmp). PLAN > Journal displayed [“Your progress has been recorded”](cape-journal-confirmed.bmp); the exact 32-KiB resulting SRAM was preserved separately as a Journal, SHA-256 `af6e22a5004a0ce919f1dd4c6f64611e89a342bb9cac355f38c1d4aa6fa2d139`. A [fresh diagnostic Continue](cape-fresh-continue.bmp) restored that location, the original party and PltnmCape; its entire 32-KiB SRAM was byte-for-byte identical.

The player returned through the original key shrine and GreatLog Key, then sold the actual cape through the original Main Street merchant. The original [3750G offer](cape-sale-offer.bmp) was accepted, raising the wallet from 106G to [3856G](cape-sale-3856g.bmp). An original Journal after the sale was SHA-256 `522b1a6094e59f7043746a27e8d8bb0303a987aad8b28a52bb083b1433ef0ac9`; its diagnostic fresh Continue retained all 32768 bytes exactly.

## B victory on this save, then A attempts

With 3856G, choosing A first yielded [“You can't try that Class yet”](a-class-locked-before-b.bmp). The same party then paid 500G and completed all three original B Class fights on this separate save. The original receptionist [confirmed the victory](b-victory-confirmed.bmp) and [awarded a Magic Key](b-key-received.bmp). The subsequent original Journal with 3356G, SHA-256 `d0ef51a3221b3e9cf3b45f1a841a3d550eab4cb964ec77813ab65bfeec945e08`, passed the [fresh-runtime Continue comparison](b-continue-evidence.txt) and its complete 32-KiB SRAM was byte-identical. Each later A attempt started from an independent copy of that genuine pre-A Journal.

The original receptionist accepted the [1000G A Class entry](a-entry-3356g.bmp). The following were separate original-input attempts from the pre-A Journal; none of these five attempts won the A championship:

1. The first attempt to select individual skills encountered the tournament's four tactic choices instead. The automation consequently selected No Skil/Defense combinations and [lost in the first fight](a-first-defeat.bmp).
2. Garon and Derzo were set to Mixed, Slash to Charge. This also [lost in the first fight](a-mixed-defeat.bmp).
3. All three were set to Charge. The game [confirmed victory in fight one](a-round1-win.bmp), but the [second fight started at 13/79/172 HP](a-round2-start-hp.bmp) for Garon/Slash/Derzo. Switching to Mixed/Charge/Mixed led to [defeat in fight two](a-round2-defeat.bmp).
4. The same original-input Charge route was replayed from the genuine pre-A Journal. At the last fight-one menu, with 13/79/172 HP and one remaining opponent, Mixed/Defense/Mixed left [Garon knocked out](a-late-heal-intervention.bmp) before a recovery; this exploratory branch was stopped at the next original menu, without claiming a tournament result.
5. A second original-input replay intervened one turn earlier at 44/114/207 HP with two opponents remaining. Mixed/Defense/Mixed caused Garon to use MouthShut, not HealAll, and the [party's HP fell](a-earlier-heal-intervention.bmp); a subsequent Defense turn did not recover the party. After further original tactic inputs Derzo won fight one alone, and the party [lost fight two](a-earlier-intervention-defeat.bmp).

The original game does not allow items in these Arena battles, as independently observed in the [B attempt](../2026-11-02-arena-b/README.md).

## A Class victory on a later original-input attempt

A further independent attempt used the same genuine pre-A Journal. At the first original battle menu, the player chose **Defense for Garon and Charge for Slash and Derzo**. The game confirmed [victory in battle one](a-defense-round1-win.bmp). Battle two began at 58/112/147 HP; during that battle the game explicitly displayed [“Garon cast HealAll”](a-defense-healall.bmp), and confirmed [victory in battle two](a-defense-round2-win.bmp). The [third battle began](a-defense-round3-hp.bmp) at 166/181/207 HP. The same original tactics then won the third battle; the game announced [the A Class champion](a-champion-title.bmp) as [Master CobiA and powerful friends](a-champion-name.bmp). This is an observation of HealAll in this particular battle, not proof the AI always chooses it.

The original receptionist [awarded a Magic Key](a-magic-key-received.bmp). The player made a separate original 32-KiB Journal with 2356G, SHA-256 `5afe17c1e9817cf9229af195690ba0834fccbe8155bf9992e6415f6a45d4ee00`; [fresh Continue](a-champion-fresh-continue.bmp) produced byte-identical SRAM and the [diagnostic field comparison](a-champion-continue-evidence.txt) reported zero mismatches. The new unappraised key is index 9, record `fe 04 33 1b`, seed bytes `33 dc` (0xDC33). The protected Squiz was not used or bred.

The original S Class menu listed [5000G](s-entry-2356g.bmp) and, when confirmed with the actual 2356G, responded [“Not enough gold for that Class”](s-insufficient-gold.bmp). No S battle or result is claimed.

## Reproduction material

- [Original controller and observation trace: cape, sale, B, first A attempt](cape-b-a-original-trace.txt); [session commands](cape-b-a-input-commands.txt).
- Independent original traces: [Mixed/Charge](a-mixed-original-trace.txt), [Charge](a-charge-original-trace.txt), [late recovery intervention](a-late-heal-original-trace.txt), and [earlier recovery intervention](a-earlier-heal-original-trace.txt). These branches replay original inputs from the authentic pre-A Journal; observational RAM was not used as a save seed. The cape Journal above is a copy of cartridge SRAM immediately after the original save confirmation.
- The successful A attempt has its own [original-input trace](a-champion-original-trace.txt) (SHA-256 `ddb2876ba7c2c24e8e351c2bab90011c2df722a2f5e443eb53fcb3e265d55723`) and [session commands](a-champion-input-commands.txt).
- [SHA-256 manifest](sha256sums.txt) covers the unmodified screenshots and retained traces. Actual Journals, RAM snapshots and executables remain in scratch and are not included in this directory.
