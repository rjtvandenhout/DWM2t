#!/usr/bin/env python3
import argparse, pathlib, re

DB_RE = re.compile(r"^\s*db\s+(.*)$", re.I)
HEX_RE = re.compile(r"\$([0-9A-Fa-f]{2})")

TARGETS = {
    2: [0x48C3, 0x4F4C],
}

def parse(path):
    out = bytearray()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = DB_RE.match(line)
        if m:
            out.extend(int(x, 16) for x in HEX_RE.findall(m.group(1)))
    return bytes(out)

def ctx(data, i, before=20, after=28):
    lo=max(0,i-before); hi=min(len(data),i+after)
    return " ".join(f"{b:02x}" for b in data[lo:hi])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--banks-dir", type=pathlib.Path, required=True)
    args=ap.parse_args()

    banks={}
    for path in sorted(args.banks_dir.glob("bank_*.asm")):
        bank=int(path.stem.split("_")[-1])
        banks[bank]=(path,parse(path))

    hits=0
    for target_bank, targets in TARGETS.items():
        for source_bank,(path,data) in banks.items():
            base=0 if source_bank==0 else 0x4000
            for i in range(len(data)-5):
                # Common DWM2 far call: LD HL,addr / LD B,bank / RST $10.
                if data[i]==0x21 and data[i+3]==0x06 and data[i+5]==0xD7:
                    addr=data[i+1] | (data[i+2]<<8)
                    bank=data[i+4]
                    if bank==target_bank and addr in targets:
                        hits+=1
                        print(
                            f"M7_BATTLE_GATE_FAR_CALL source_bank={source_bank} "
                            f"source_pc=0x{base+i:04x} target_bank={bank} "
                            f"target_pc=0x{addr:04x} context={ctx(data,i)} "
                            f"file={path.name}"
                        )

        # Same-bank direct CALL/JP references.
        path,data=banks[target_bank]
        base=0 if target_bank==0 else 0x4000
        for i in range(len(data)-2):
            if data[i] not in (0xCD,0xC3):
                continue
            addr=data[i+1] | (data[i+2]<<8)
            if addr not in targets:
                continue
            hits+=1
            kind="call" if data[i]==0xCD else "jump"
            print(
                f"M7_BATTLE_GATE_LOCAL_REF bank={target_bank} "
                f"source_pc=0x{base+i:04x} kind={kind} "
                f"target_pc=0x{addr:04x} context={ctx(data,i)} "
                f"file={path.name}"
            )

    print(f"M7_BATTLE_GATE_SCAN_COMPLETE hits={hits}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
