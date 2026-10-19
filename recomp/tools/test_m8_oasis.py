"""Revalidate original Oasis/Asiya Journal routes; not final M8 acceptance."""
import argparse
from pathlib import Path
import subprocess
import tempfile

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--route", type=Path, required=True)
    parser.add_argument("--inn-route", type=Path, required=True)
    parser.add_argument("--checkpoint-route", type=Path, action="append", default=[])
    parser.add_argument("--feeding-route", type=Path)
    parser.add_argument("--audio-route", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.feeding_route and len(args.checkpoint_route) < 5:
        parser.error("feeding side branch requires the five original story checkpoints")
    if args.audio_route and len(args.checkpoint_route) < 8:
        parser.error("audio side branch requires the post-Oasis home checkpoint")
    args.output.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="oasis-", dir=args.output.resolve()))
    result = subprocess.run([str(args.exe.resolve()), "--m8-oasis-test",
                             str(args.seed.resolve()), str(args.route.resolve()), str(output)])
    print(f"M8_OASIS_EVIDENCE {output}", flush=True)
    if result.returncode == 0:
        result = subprocess.run([str(args.exe.resolve()), "--m8-inn-test",
                                 str(output / "oasis_original_journal.sav"),
                                 str(args.inn_route.resolve()), str(output / "inn")])
    seed = output / "inn" / "inn_original_journal.sav"
    for index, route in enumerate(args.checkpoint_route, start=1):
        if result.returncode != 0:
            break
        checkpoint = output / f"story-{index:02}"
        result = subprocess.run([str(args.exe.resolve()), "--m8-checkpoint-test",
                                 str(seed), str(route.resolve()), str(checkpoint)])
        seed = checkpoint / "checkpoint.sav"
        if result.returncode == 0 and index == 5 and args.feeding_route:
            # Side branch from the original thieves-report Journal: do not
            # replace the main story seed with the food-test detour's save.
            result = subprocess.run([str(args.exe.resolve()), "--m8-checkpoint-test",
                                     str(seed), str(args.feeding_route.resolve()),
                                     str(output / "enemy-feeding")])
            if result.returncode == 0:
                print("M8_ENEMY_FEEDING_BRANCH_PASS original_item_consumption_and_bonus", flush=True)
        if result.returncode == 0 and index == 8 and args.audio_route:
            result = subprocess.run([str(args.exe.resolve()), "--m8-audio-output-test",
                                     str(seed), str(args.audio_route.resolve()),
                                     str(output / "hub-audio")])
    return result.returncode

if __name__ == "__main__":
    raise SystemExit(main())
