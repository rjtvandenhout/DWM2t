#!/usr/bin/env python3
"""Extract original Magic Key thresholds and exact selector bins; no game or saves."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import tempfile

ROM_SHA = '8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e'
ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

def original_name(banks: list[bytes], kind: str, index: int) -> dict:
    # Original formatter 0:$248F/$2498 uses prefix+1 and suffix+17,
    # then0:$24A2 indexes bank9:$4078 and copies through the F0 byte.
    table_index=index+(1 if kind=='prefix' else 17)
    pointer_offset=0x78+2*table_index
    address=int.from_bytes(banks[9][pointer_offset:pointer_offset+2],'little')
    start=address-0x4000
    end=banks[9].index(0xf0,start)
    raw=banks[9][start:end+1]
    if len(raw)>7 or any(value>=len(ALPHABET) for value in raw[:-1]):
        raise ValueError('Original Magic Key name alphabet or terminator differs')
    return {'name':''.join(ALPHABET[value] for value in raw[:-1]),
            'pointer_cpu_address':f'9:${pointer_offset+0x4000:04X}',
            'string_cpu_address':f'9:${address:04X}','raw_including_f0':raw.hex(' ')}

def read_bank(path: Path) -> bytes:
    out=bytearray()
    for line in path.read_text(encoding='utf-8').splitlines():
        match=re.match(r'^\s*db\s+(.*)$',line,re.I)
        if match:
            out.extend(int(x,16) for x in re.findall(r'\$([0-9a-fA-F]{2})(?![0-9a-fA-F])',match.group(1).split(';',1)[0]))
    if len(out)!=16384:
        raise ValueError('Source bank must be exactly16384 bytes: '+str(path))
    return bytes(out)

def select(row: list[int], roll: int, skip_zero: bool) -> int:
    if not 0<=roll<100:
        raise ValueError('Original accepted roll is0..99')
    for index,threshold in enumerate(row):
        if (not skip_zero or threshold!=0) and threshold>=roll:
            return index
    raise ValueError('No original threshold accepts the roll')

def existing(path: Path, id_field: str) -> tuple[dict[int,str],list[dict[str,str]]]:
    rows=list(csv.DictReader(path.open(encoding='utf-8-sig',newline='')))
    names={int(r[id_field]):r.get(id_field.replace('_id','_name'),'') for r in rows if r.get(id_field.replace('_id','_name'), '')}
    return names,rows

def extract(repo: Path, output: Path) -> dict:
    banks=[read_bank(repo/'src/banks'/f'bank_{i:03}.asm') for i in range(256)]
    digest=hashlib.sha256(b''.join(banks)).hexdigest()
    if digest!=ROM_SHA:
        raise ValueError('Original ROM identity differs')
    b=banks[96]
    if (b[0x2942:0x294b]!=bytes.fromhex('0e 3c cd 82 16 11 09 6a 19') or
            b[0x2924:0x2929]!=bytes.fromhex('cb 37 21 69 69') or
            b[0x295c:0x2969]!=bytes.fromhex('cd f3 09 fa 04 cd e6 7f fe 64 30 f4 c9') or
            b[0x2934:0x293b]!=bytes.fromhex('2a b7 28 03 b9 30 03') or
            b[0x2951:0x2958]!=bytes.fromhex('2a b9 30 03 04 18 f9')):
        raise ValueError('Original table-stride/selector code differs')
    if (b[0xcC1+56*4:0xcC1+56*4+5]!=bytes.fromhex('06 00 21 63 cd') or
            b[0x2a09+10*60:0x2a09+10*60+5]!=bytes.fromhex('3e 02 ea 00 41') or
            banks[0][0x248f:0x2495]!=bytes.fromhex('2a 3c e5 cd a2 24') or
            banks[0][0x2497:0x249d]!=bytes.fromhex('7e c6 11 cd a2 24')):
        raise ValueError('Original table boundary or name formatter differs')
    if output.exists():
        raise ValueError('Output must be a new directory; nothing is overwritten')
    result={'schema':1,'scope':'Static original-source threshold extraction; no game execution, state edits or save generation',
            'rom_sha256':digest,'bank':96,'accepted_rolls':[0,99],
            'comparison':'first nonzero threshold>=roll for prefix; first threshold>=roll for suffix',
            'boundary_semantics':{'prefix_zero':'skip; not a terminator',
                'suffix_zero':'ordinary threshold; not a terminator; actual first threshold in every row is positive',
                'threshold100':'inclusive comparison, but accepted random rolls stop at99',
                'suffix_padding':'four zero bytes after56 logical IDs; never selected by actual rows',
                'suffix_table_end':'next routine96:$6C61; no extra level band or suffix names'},
            'probability_limit':'roll_counts count the100 accepted roll values; they are not an exhaustive distribution over correlated PRNG seed states',
            'tables':{},'terrain':{},'existing_csv_comparison':{}}
    csv_outputs={}
    for kind,offset,stride,logical in [('prefix',0x2969,16,16),('suffix',0x2a09,60,56)]:
        names,old=existing(repo/'research/full_rom_read'/f'magic_key_{kind}_thresholds.csv',kind+'_id')
        decoded_names={index:original_name(banks,kind,index) for index in range(logical)}
        if any(names[index]!=decoded_names[index]['name'] for index in names):
            raise ValueError('Existing nonblank name label differs from original ROM')
        rows=[];exports=[];mismatches=[]
        for band in range(10):
            raw=list(b[offset+band*stride:offset+(band+1)*stride])
            if len(raw)!=stride or raw[logical:]!=[0]*(stride-logical):
                raise ValueError('Original padding differs')
            nonzero=[n for n in raw if n]
            if nonzero!=sorted(nonzero) or nonzero[-1]!=100:
                raise ValueError('Nonzero original thresholds must end at100')
            outcomes=[select(raw,r,kind=='prefix') for r in range(100)]
            if any(i>=logical for i in outcomes):
                raise ValueError('A padding entry is unexpectedly selected')
            counts=[outcomes.count(i) for i in range(stride)]
            if sum(counts)!=100:
                raise ValueError('Selector coverage must contain exactly100 roll values')
            rows.append({'band':band,'level_min':band*10,'level_max':band*10+9,
                         'cpu_address':f'96:${offset+0x4000+band*stride:04X}',
                         'raw_thresholds':raw,'roll_counts':counts,'selected_ids_by_roll_0_to_99':outcomes})
            previous=0
            for index in range(logical):
                threshold=raw[index]
                exports.append({'level_div10_index':band,kind+'_id':index,
                    kind+'_name':decoded_names[index]['name'],
                    'threshold':threshold,
                    'threshold_delta_from_previous':threshold-previous if threshold else 0,
                    'accepted_roll_count':counts[index],
                    'minimum_winning_roll':min((r for r,i in enumerate(outcomes) if i==index),default=''),
                    'maximum_winning_roll':max((r for r,i in enumerate(outcomes) if i==index),default='')})
                if threshold:
                    previous=threshold
        for oldrow in old:
            band,index=int(oldrow['level_div10_index']),int(oldrow[kind+'_id'])
            actual=rows[band]['raw_thresholds'][index]
            if int(oldrow['threshold'])!=actual:
                mismatches.append({'band':band,'id':index,'existing':int(oldrow['threshold']),'original':actual})
        result['tables'][kind]={'offset':hex(96*0x4000+offset),'cpu_address':f'96:${offset+0x4000:04X}',
            'bands':10,'row_stride_bytes':stride,'logical_ids':logical,'padding_bytes_per_row':stride-logical,
            'sha256':hashlib.sha256(b[offset:offset+10*stride]).hexdigest(),'rows':rows,
            'names_original_rom':decoded_names,
            'names_from_existing_csv_unverified':names}
        result['existing_csv_comparison'][kind]={'rows_checked':len(old),'threshold_mismatches':len(mismatches),
            'mismatches':mismatches,'existing_delta_column_is_not_exact_roll_count':True}
        csv_outputs[kind]=exports
    terrain=[]
    for suffix in range(56):
        raw=list(b[0x0cc1+suffix*4:0x0cc5+suffix*4])
        if any(x>10 for x in raw) or not any(raw):raise ValueError('Original terrain selectors differ')
        terrain.append({'suffix_id':suffix,'raw_choices':raw,'class_ids':sorted(set(x-1 for x in raw if x)),
                        'zero_means_retry':True})
    result['terrain']={'cpu_address':'96:$4CC1','row_stride_bytes':4,'suffix_rows':56,'class_ids':list(range(10)),
        'selector':'RNG low2bits selects one of4 cells; retry zero, subtract1 for class',
        'rows':terrain}
    output.mkdir(parents=True)
    for kind,rows in csv_outputs.items():
        with (output/f'magic_key_{kind}_thresholds.csv').open('x',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    with (output/'magic-key-tables.json').open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    choice=parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--output',type=Path,help='New directory for extracted tables and source evidence')
    choice.add_argument('--check',action='store_true',help='Check the committed CSVs against the original ROM')
    args=parser.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory(prefix='dwm2t-magic-keys-') as temporary:
            destination=Path(temporary)/'tables'
            report=extract(args.repo,destination)
            for kind in ('prefix','suffix'):
                filename=f'magic_key_{kind}_thresholds.csv'
                expected=destination/filename
                actual=args.repo/'research/full_rom_read'/filename
                if expected.read_bytes()!=actual.read_bytes():
                    raise SystemExit(f'Original Magic Key table differs: {actual}')
    else:
        report=extract(args.repo,args.output)
    print(json.dumps({'status':'extracted_static_only','rom_sha256':report['rom_sha256'],
        'output':str(args.output) if args.output else None,'check_passed':bool(args.check),
        'prefix_threshold_mismatches':report['existing_csv_comparison']['prefix']['threshold_mismatches'],
        'suffix_threshold_mismatches':report['existing_csv_comparison']['suffix']['threshold_mismatches'],
        'suffix_stride':60,'suffix_logical_ids':56,'roll_cases_checked':2000},indent=2))
