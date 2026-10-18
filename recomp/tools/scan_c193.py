#!/usr/bin/env python3
import argparse, pathlib, re
DB_RE=re.compile(r"^\s*db\s+(.*)$",re.I)
HEX_RE=re.compile(r"\$([0-9A-Fa-f]{2})")
def parse(path):
    out=bytearray()
    for line in path.read_text(encoding="utf-8").splitlines():
        m=DB_RE.match(line)
        if m: out.extend(int(x,16) for x in HEX_RE.findall(m.group(1)))
    return bytes(out)
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--banks-dir",type=pathlib.Path,required=True)
    args=ap.parse_args()
    hits=0
    for path in sorted(args.banks_dir.glob("bank_*.asm")):
        bank=int(path.stem.split("_")[-1]); data=parse(path)
        base=0 if bank==0 else 0x4000
        for i in range(len(data)-2):
            op=data[i]
            if op not in (0xEA,0xFA): continue
            if data[i+1]!=0x93 or data[i+2]!=0xC1: continue
            hits+=1
            kind="write" if op==0xEA else "read"
            imm=None
            if i>=2 and data[i-2]==0x3E: imm=data[i-1]
            lo=max(0,i-24); hi=min(len(data),i+32)
            ctx=" ".join(f"{b:02x}" for b in data[lo:hi])
            extra=f" immA=0x{imm:02x}" if imm is not None else ""
            print(f"M7_C193_REF kind={kind} bank={bank} pc=0x{base+i:04x}{extra} context={ctx} file={path.name}")
    print(f"M7_C193_SCAN_COMPLETE hits={hits}")
if __name__=="__main__": main()
