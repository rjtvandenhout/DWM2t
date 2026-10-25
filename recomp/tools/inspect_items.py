#!/usr/bin/env python3
"""Export exact original item records/names and independently proven shop resale lookups.
No game launches or state writes. Unknown record bytes retain neutral names.
"""
import argparse,csv,hashlib,io,json,re,tempfile
from pathlib import Path
ROM_SHA='8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e'
ALPHABET='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
PUNCT={0x3e:"'s",0x3f:"'m",0x40:"'r",0x41:"'t",0x42:"'v",0x43:"'l",0x44:"'d",0x90:' ',0x98:'?',0x99:'!',0x9c:'-',0xa3:':',0xab:',',0xb5:'.',0xf1:' / '}
def extract(repo,output):
 if not __debug__:raise ValueError('Run without Python optimization; source assertions are required')
 output.mkdir(parents=True,exist_ok=False)
 banks=[]
 for n in range(256):
  path=repo/'src/banks'/f'bank_{n:03}.asm';raw=bytes(int(x,16) for line in path.read_text().splitlines() if re.match(r'\s*db\s',line) for x in re.findall(r'\$([0-9a-fA-F]{2})\b',line));assert len(raw)==16384;banks.append(raw)
 assert hashlib.sha256(b''.join(banks)).hexdigest()==ROM_SHA
 def data(n,pc,size):return banks[n][pc-(16384 if n else 0):pc-(16384 if n else 0)+size]
 def byte(n,pc):return data(n,pc,1)[0]
 def word(n,pc):return int.from_bytes(data(n,pc,2),'little')
 def source(n,pc):return {'bank':n,'cpu':f'0x{pc:04X}','rom_offset':f'0x{n*16384+pc-(16384 if n else 0):06X}','file':f'src/banks/bank_{n:03}.asm','line':3+(pc-(16384 if n else 0))//16}
 def name(i):
  ptr=word(8,0x4716+2*i);end=banks[8].index(0xf0,ptr-0x4000);raw=data(8,ptr,end-(ptr-0x4000)+1);tokens=[ALPHABET[v] if v<len(ALPHABET) else PUNCT.get(v,f'<{v:02X}>') for v in raw[:-1]];return ptr,raw,''.join(tokens)
 # Exact loader, name-indexing and subsequent independent table boundary.
 assert data(22,0x400b,19)==bytes.fromhex('fa 81 d0 0e 0d cd 82 16 7d c6 c2 6f 7c ce 4c 67 d1 06 0d')
 assert data(0,0x2431,13)==bytes.fromhex('cb 27 6f 26 00 7d c6 16 6f 7c ce 47 67')
 assert data(22,0x44bf,3)==bytes.fromhex('21 c9 51')
 assert data(28,0x5f3e,32)==bytes.fromhex('c5 21 20 63 fa fb d7 85 6f 30 01 24 7e f5 21 38 63 19 4e 23 46 f1 cd aa 16 3e 64 cd e2 16 c1 c9')
 start,end,stride=0x4cc2,0x51c9,13;assert (end-start)%stride==0;count=(end-start)//stride;assert count==99
 factors=list(data(28,0x6320,24));assert factors[0]==75
 legacy_path=repo/'research/full_rom_read/items_data.csv';legacy=list(csv.DictReader(legacy_path.open(encoding='utf-8-sig')));is_legacy=bool(legacy and 'item_id' in legacy[0])
 rows=[];changes=[]
 for i in range(count):
  pc=start+i*stride;raw=data(22,pc,stride);np,nraw,text=name(i);sv=word(28,0x6338+2*i);value=int.from_bytes(raw[1:3],'little')
  row={'runtime_item_id':i,'legacy_name_index':i-1 if i else None,'record_cpu':f'0x{pc:04X}','record_rom_offset':f'0x{22*16384+pc-16384:06X}','raw_13_hex':raw.hex(' '),**{f'byte_{j:02X}':v for j,v in enumerate(raw)},'raw_u16_le_01_02':value,'name_pointer_cpu':f'0x{np:04X}','name_raw_hex':nraw.hex(' '),'name_original_glyphs':text,'shop_resale_base_gold':sv,'main_merchant_percent':factors[0],'main_merchant_unit_sale_gold':sv*factors[0]//100,'placeholder_name':not text or text=='None'}
  rows.append(row)
  if i and is_legacy:
   old=legacy[i-1];changes.append({'runtime_item_id':i,'name':text,'legacy_item_id':int(old['item_id']),'legacy_name':old['name'],'legacy_record_rom_offset':old['rom_offset'],'correct_record_rom_offset':row['record_rom_offset'],'legacy_purchase_price':int(old['purchase_price']),'correct_raw_u16_le_01_02':value,'actual_main_merchant_sale_gold':row['main_merchant_unit_sale_gold']})
 fields=list(rows[0]);buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(rows);(output/'items_data.csv').write_text(buf.getvalue(),newline='')
 mismatch=[r['runtime_item_id'] for r in rows if r['raw_u16_le_01_02']!=r['shop_resale_base_gold']]
 assert mismatch==[84,85,86,87,88,89,98] # Explicit unused/anonymous metadata placeholders retain raw13-word, not an invented sell price.
 metadata={'schema':'original-item-records-corrected-v1','rom_sha256':ROM_SHA,'storage':{'bank':22,'start_cpu':'0x4CC2','end_exclusive_cpu':'0x51C9','stride':stride,'records':count,'runtime_ids':[0,98],'bytes':count*stride,'sha256':hashlib.sha256(data(22,start,count*stride)).hexdigest(),'boundary_evidence':'Independent response matrix at51C9 referenced by22:44BF/44E8/4657; do not parse it as further item records.'},'names':{'bank':8,'pointer_table_cpu':'0x4716','next_table_cpu':'0x47F6','pointer_slots':112,'runtime_indexing':'Original0:2431 doubles runtimeID directly; slot0 empty. Legacy CSV nameindex is runtimeID-1. Only record IDs0..98 exported; unused remaining name slots are not metadata rows.','glyph_policy':'Original raw bytes retained losslessly; unknown icon glyphs stay<XX>, no outside name substitutions.'},'resale':{'routine':source(28,0x5f3e),'base_word_table':source(28,0x6338),'merchant_percent_table':source(28,0x6320),'merchant_percent_values':factors,'formula':'floor(base_word[runtime_id] * percent[merchant_D7FB] /100), per unit;28:5BE6 multiplies by original quantity.','purchase_price_caveat':'The13-byte row word01..02 agrees with independently used resale base for all ordinary named IDs. Seven unused/anonymous placeholders contain13 while resale base is0. The raw field stays neutral; buying stock/prices may vary by shop and are not inferred from oldCSV.','raw_word_different_from_resale_ids':mismatch},'original_citations':[source(22,0x400b),source(0,0x2431),source(22,0x44bf),source(28,0x5f3e),source(28,0x5be6)],'legacy_comparison':{'path':str(legacy_path),'sha256':hashlib.sha256(legacy_path.read_bytes()).hexdigest(),'legacy_rows':len(legacy),'legacy_format_detected':is_legacy,'defects':(['15-byte stride instead of original13','Names omit empty runtime0, so CSVitem_id is nameindex rather than runtimeID','Parsing111wide rows overruns the99record metadata table into unrelated tables/code'] if is_legacy else []),'same_name_different_rom_offset':sum(x['legacy_record_rom_offset'].lower()!=x['correct_record_rom_offset'].lower() for x in changes),'different_value_word':sum(x['legacy_purchase_price']!=x['correct_raw_u16_le_01_02'] for x in changes)},'records':rows}
 (output/'item-records-corrected.json').write_text(json.dumps(metadata,indent=2)+'\n');(output/'legacy-item-comparison.json').write_text(json.dumps(changes,indent=2)+'\n')
 # Source-observed mainmerchant transaction independently crosschecks the percentage and runtimeID mapping.
 steel=rows[69];assert steel['name_original_glyphs']=='SteelFang' and steel['shop_resale_base_gold']==500 and steel['main_merchant_unit_sale_gold']==375
 assert rows[10]['name_original_glyphs']=='SkyBell' and rows[10]['main_merchant_unit_sale_gold']==15
 print(json.dumps({'records':count,'table_bytes':count*stride,'SteelFang':{k:steel[k] for k in ('runtime_item_id','name_original_glyphs','record_cpu','raw_13_hex','shop_resale_base_gold','main_merchant_unit_sale_gold')},'legacy_comparison':metadata['legacy_comparison']}))
 return metadata

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
 group=ap.add_mutually_exclusive_group(required=True)
 group.add_argument('--output',type=Path,help='New directory for original item records and source evidence')
 group.add_argument('--check',action='store_true',help='Compare committed items_data.csv with the original ROM')
 a=ap.parse_args()
 if a.check:
  with tempfile.TemporaryDirectory(prefix='dwm2t-items-')as temporary:
   destination=Path(temporary)/'items';extract(a.repo,destination)
   if (destination/'items_data.csv').read_bytes()!=(a.repo/'research/full_rom_read/items_data.csv').read_bytes():
    raise SystemExit('Committed original item data differs')
  print('ORIGINAL_ITEM_RECORDS_CHECK_PASS')
 else:extract(a.repo,a.output)

if __name__=='__main__':main()
