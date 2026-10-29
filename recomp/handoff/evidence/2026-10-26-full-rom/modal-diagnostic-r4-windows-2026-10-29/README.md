# Native Windows rejection-dialog diagnostic

Original validation [run 40806942912](https://github.com/rjtvandenhout/DWM2t/actions/runs/40806942912) and its retry stopped at the two-window gate because its same-save rejection process did not exit. The player's captured stderr identified the expected refusal: `Local link requires two different save files`.

The separately dispatched native Windows [diagnostic run 40817904586](https://github.com/rjtvandenhout/DWM2t/actions/runs/40817904586) exercised the exact original R4 player (game source `1351bcd058e491455a477045a2ff86bbc3bd7b1c`, EXE SHA-256 `63bf283dfeb7543c82d2787221788ab71e8651130b0a829b8987b368864a6f95`). It used separate copies of the genuine ending Journal, SHA-256 `0649c4ef78867d2e55f352ddb0fea811fea6e3cf7407f8451220cc2bf01df95d`. The diagnostic tooling commit was `170dec30424e4acc4c5339f479198f886f4318d6`, not the game source commit.

In the `button_click` case, the owned, visible and enabled `#32770` dialog was on the Default desktop, but `GetDlgItem(dialog, 1)` returned null throughout the 30-second observation. No click was delivered; the diagnostic terminated that rejected process at timeout. In the separate `dialog_close` case, posting `WM_CLOSE` to the same kind of owned `DWM2t player` modal led to exit code 1 and the expected stderr refusal. Both seed copies remained unchanged, and neither case created a game window. This established a test automation control-layout assumption; it did not by itself certify the full player.

- [Unmodified diagnostic report](modal-diagnostic.json), SHA-256 `22c6bdaffbee2a843c4b8db503528fef5e6912ff0808ad4d7e84bf4f459dd745`.
- [Exact diagnostic helper](diagnose_player_modal.py), SHA-256 `ffa75e4719fe40fc4a2915f265cc583c26a757ca5e8d651ecd5e9b4e170acf60`; it imported its Windows helpers from tooling commit `170dec3`.
- [Original GitHub artifact metadata](artifact-metadata.json). Artifact ID `12873720167`, ZIP SHA-256 `281386eb54e4af7802703d422bee13091d736cf2aef39103e43774650dc1b76a`.

No Journal files or executable are included in this evidence folder.
