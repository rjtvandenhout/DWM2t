#!/usr/bin/env python3
import argparse, pathlib, re

DB_RE=re.compile(r"^\s*db\s+(.*)$",re.I)
HEX_RE=re.compile(r"\$([0-9A-Fa-f]{2})")

# C5DB=2 writers discovered by scan_game_modes.py.
TARGETS={
    2:[0x4FD4,0x5060,0x63C8],
    15:[0x4158],
    133:[0x4732],
}

def parse(path):
    out=bytearray()
    for line in path.read_text(encoding="utf-8").splitlines():
        m=DB_RE.match(line)
        if m:
            out.extend(int(x,16) for x in HEX_RE.findall(m.group(1)))
    return bytes(out)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--banks-dir",type=pathlib.Path,required=True)
    args=ap.parse_args()
    banks={}
    for path in sorted(args.banks_dir.glob("bank_*.asm")):
        bank=int(path.stem.split("_")[-1])
        banks[bank]=(path,parse(path))

    # Search the common far-call encoding used throughout this ROM:
    #   21 lo hi 06 bank d7
    # Include a window around each mode writer because the writer often sits
    # inside a larger entry function whose first instruction is earlier.
    hits=0
    for target_bank,writers in TARGETS.items():
        lo_addr=min(writers)-0x100
        hi_addr=max(writers)+0x100
        for source_bank,(path,data) in banks.items():
            base=0 if source_bank==0 else 0x4000
            for i in range(len(data)-5):
                if data[i]!=0x21 or data[i+3]!=0x06 or data[i+5]!=0xD7:
                    continue
                addr=data[i+1] | (data[i+2]<<8)
                bank=data[i+4]
                if bank!=target_bank or not (lo_addr<=addr<=hi_addr):
                    continue
                hits+=1
                ctx=data[max(0,i-16):min(len(data),i+24)]
                print(
                    f"M7_BATTLE_CALLER source_bank={source_bank} "
                    f"source_pc=0x{base+i:04x} target_bank={target_bank} "
                    f"target_pc=0x{addr:04x} nearest_mode_writers="
                    + ",".join(f"0x{x:04x}" for x in writers)
                    + " context=" + " ".join(f"{b:02x}" for b in ctx)
                    + f" file={path.name}"
                )

    # Also print same-bank direct CALL/JUMP references into the same windows.
    for target_bank,writers in TARGETS.items():
        path,data=banks[target_bank]
        base=0x4000 if target_bank else 0
        lo_addr=min(writers)-0x100
        hi_addr=max(writers)+0x100
        for i in range(len(data)-2):
            if data[i] not in (0xCD,0xC3):
                continue
            addr=data[i+1] | (data[i+2]<<8)
            if not (lo_addr<=addr<=hi_addr):
                continue
            hits+=1
            kind="call" if data[i]==0xCD else "jump"
            ctx=data[max(0,i-16):min(len(data),i+24)]
            print(
                f"M7_BATTLE_LOCAL_REF bank={target_bank} source_pc=0x{base+i:04x} "
                f"kind={kind} target_pc=0x{addr:04x} context="
                + " ".join(f"{b:02x}" for b in ctx)
                + f" file={path.name}"
            )

    print(f"M7_BATTLE_CALLER_SCAN_COMPLETE hits={hits}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
