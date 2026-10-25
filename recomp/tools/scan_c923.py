#!/usr/bin/env python3
import argparse, pathlib, re
DB_RE = re.compile(r"^\s*db\s+(.*)$", re.I)
HEX_RE = re.compile(r"\$([0-9A-Fa-f]{2})")
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
    high_writes=[]
    for path in sorted(args.banks_dir.glob("bank_*.asm")):
        bank=int(path.stem.split("_")[-1])
        data=parse(path)
        base=0 if bank==0 else 0x4000
        for i in range(len(data)-2):
            if data[i] not in (0xEA,0xFA):
                continue
            if data[i+1]!=0x23 or data[i+2]!=0xC9:
                continue
            refs+=1
            kind="write" if data[i]==0xEA else "read"
            immediate=None
            if i>=2 and data[i-2]==0x3E:
                immediate=data[i-1]
            ctx=data[max(0,i-16):min(len(data),i+24)]
            extra=f" immA=0x{immediate:02x}" if immediate is not None else ""
            print(
                f"M7_C923_REF kind={kind} bank={bank} pc=0x{base+i:04x}{extra} "
                + "context=" + " ".join(f"{b:02x}" for b in ctx)
                + f" file={path.name}"
            )
            if kind=="write" and immediate is not None and immediate>=0x80:
                high_writes.append((bank,base+i,immediate))
    for bank,pc,value in high_writes:
        print(f"M7_C923_HIGH_WRITE bank={bank} pc=0x{pc:04x} value=0x{value:02x}")
    print(f"M7_C923_SCAN_COMPLETE refs={refs} high_writes={len(high_writes)}")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
