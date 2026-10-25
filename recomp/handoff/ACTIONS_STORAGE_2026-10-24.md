# Actions artifact storage cleanup (2026-10-24)

The user requested removal of unused Actions output after a limit notification.
The API inventory contained 224 artifacts using 4,458,445,626 bytes.

Removed 159 obsolete generated Windows binaries from before 2026-10-20:
143 M7 Discovery and 16 M6 Probe artifacts. The selection excluded every run or
artifact ID referenced in tracked documentation, tests, workflows and evidence;
each artifact name's latest build; and restore branches. Source snapshots,
validation reports, saves, current M8 development/player packages and other
artifact categories were retained. No workflow runs, branches or source were deleted.

The deletion API succeeded for all 159 IDs, reclaiming 3,946,430,584 bytes.
A fresh inventory independently confirmed 65 artifacts and 512,015,042 bytes
(488.30 MiB), all protected IDs retained and all selected IDs absent. In particular,
the pinned M8 Windows binary, baseline acceptance evidence and the later Windows
dancer evidence remain downloadable. The API inventory is the evidence here;
no assertion is made about when GitHub's separate billing meter refreshes.

The complete selection, preserved metadata, deleted IDs, timestamps and
post-deletion checks are recorded in
[evidence/2026-10-24/actions-storage-cleanup.json](evidence/2026-10-24/actions-storage-cleanup.json).
