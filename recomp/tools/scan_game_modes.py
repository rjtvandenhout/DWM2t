#!/usr/bin/env python3
import argparse, pathlib, re

DB_RE = re.compile(r"^\s*db\s+(.*)$", re.I)
HEX_RE = re.compile(r"\$([0-9A-Fa-f]{2})")
TARGETS = {(0xDB,0xC5): "C5DB", (0xDC,0xC5): "C5DC"}

def parse(path):
    out=bytearray()
    for line in path.read_text(encoding="utf-8").splitlines():
        m=DB_RE.match(line)
        if m:
            out.extend(int(x,16) for x in HEX_RE.findall(m.group(1)))
    return bytes(out)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--banks-dir", type=pathlib.Path, required=True)
    args=ap.parse_args()
    refs=0
    writes={}
    for path in sorted(args.banks_dir.glob("bank_*.asm")):
        bank=int(path.stem.split("_")[-1])
        data=parse(path)
        base=0 if bank==0 else 0x4000
        for i in range(len(data)-2):
            op=data[i]
            if op not in (0xEA,0xFA):
                continue
            key=(data[i+1],data[i+2])
            if key not in TARGETS:
                continue
            refs+=1
            target=TARGETS[key]
            kind="write" if op==0xEA else "read"
            immediate=None
            if i>=2 and data[i-2]==0x3E:
                immediate=data[i-1]
            if kind=="write" and immediate is not None:
                writes.setdefault((target, immediate), []).append((bank,base+i))
            lo=max(0,i-20); hi=min(len(data),i+24)
            ctx=" ".join(f"{b:02x}" for b in data[lo:hi])
            extra=f" immA=0x{immediate:02x}" if immediate is not None else ""
            print(f"M7_MODE_REF target={target} kind={kind} bank={bank} pc=0x{base+i:04x}{extra} context={ctx} file={path.name}")
    for (target,value), locs in sorted(writes.items()):
        positions=",".join(f"{b}:0x{pc:04x}" for b,pc in locs)
        print(f"M7_MODE_WRITE_SUMMARY target={target} value=0x{value:02x} count={len(locs)} positions={positions}")
    print(f"M7_MODE_SCAN_COMPLETE refs={refs}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
