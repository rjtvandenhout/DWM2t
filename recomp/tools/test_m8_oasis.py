"""Revalidate the original early-Oasis checkpoint; not final M8 acceptance."""
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="oasis-", dir=args.output.resolve()))
    result = subprocess.run([str(args.exe.resolve()), "--m8-oasis-test",
                             str(args.seed.resolve()), str(args.route.resolve()), str(output)])
    print(f"M8_OASIS_EVIDENCE {output}", flush=True)
    if result.returncode == 0:
        result = subprocess.run([str(args.exe.resolve()), "--m8-inn-test",
                                 str(output / "oasis_original_journal.sav"),
                                 str(args.inn_route.resolve()), str(output / "inn")])
    return result.returncode

if __name__ == "__main__":
    raise SystemExit(main())
