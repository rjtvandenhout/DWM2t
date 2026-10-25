#!/usr/bin/env python3
"""Finite ORIGINAL-source checks; never execute the game, load/edit saves or set RNG."""
from __future__ import annotations
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROM_SHA = '8e38a7420ef5239c7196aa4fd4b1499e65db2823e875bbf8241bb2199e766d4e'

def source(bank, address):
    base = 0x4000 if bank else 0
    return {'bank': bank, 'cpu_address': f'${address:04X}',
            'file': f'src/banks/bank_{bank:03}.asm', 'line': 3+(address-base)//16}

def read_bank(path):
    result = bytearray()
    for line in path.read_text().splitlines():
        if re.match(r'^\s*db\s+', line, re.I):
            result.extend(int(v, 16) for v in re.findall(r'\$([0-9a-fA-F]{2})(?![0-9a-fA-F])', line.split(';',1)[0]))
    if len(result) != 16384:
        raise ValueError(f'Not one exact original bank: {path}')
    return bytes(result)

def audit(repo, diagnostic):
    if not __debug__:
        raise ValueError('Run without Python optimization; source assertions are required')
    banks = [read_bank(repo/'src/banks'/f'bank_{n:03}.asm') for n in range(256)]
    assert hashlib.sha256(b''.join(banks)).hexdigest() == ROM_SHA
    def at(n,a,size=1):
        base = 0x4000 if n else 0
        if not base <= a < base+16384 or a+size > base+16384:
            raise ValueError(f'Pointer outside exact original bank {n}:${a:04X}+{size}')
        return banks[n][a-base:a-base+size]
    def rb(n,a): return at(n,a)[0]
    def rw(n,a): return int.from_bytes(at(n,a,2),'little')
    def triple(n,a): return rb(n,a+2),rw(n,a)
    def guard(n,a,hexbytes):
        expected=bytes.fromhex(hexbytes)
        assert at(n,a,len(expected)) == expected, (n,a)
    guard(0,0x09f3,'e5 c5 fa 03 cd 6f fa 04 cd 67 4d 44 cb 25 cb 14 cb 25 cb 14 09 3e 0b 85 ea 03 cd 7c ce 00 ea 04 cd c1 e1 c9')
    guard(96,0x4b5c,'78 87 21 58 4c')
    guard(96,0x4b6a,'cd f3 09 fa 04 cd a1 80 ea 0c cd')
    guard(96,0x51f9,'fa 0c cd cb 27 21 0d 6d')
    guard(132,0x4005,'fa 0c cd 87 21 cb 4c')
    guard(96,0x53c3,'fe 0b 30 04 3e 00 18 14 fe 50 38 04 3e 0f 18 0c d6 0a 6f 26 00 3e 05 cd d1 16 7d 3c e6 0f ea 0f cd c9')

    report={'schema':1,'status':'passed_static_checks',
        'scope':'Original-source finite-table/asset/predicate validation, not native gameplay or all-seed world generation',
        'rom_sha256':ROM_SHA,'game_executed':False,'save_loaded_or_written':False,
        'rng_state_written_to_game':False,'findings':[], 'limitations':[
            'No generated world, monster, key, flag, WRAM/SRAM or CPU state is injected or synthesized.',
            'LCG calculations below are host-side mathematical checks, not executions of the native runtime.',
            'Full generator topology, placement and event correctness for all seeds is not proven by valid source pointers.',
            'Individual simple rejection predicates are bounded; the outer variable-length generator restart is not proven to terminate for every seed.',
            'CGB attribute assets are decoded below, but rendered attributes/palettes and collision semantics need gameplay evidence.',
            'AOT completeness is entry-address coverage, not an assertion that every translated opcode/path has been dynamically tested.']}

    # Every accepted suffix route must have at least one legal terrain class.
    terrain=[]
    for suffix in range(56):
        raw=list(at(96,0x4cc1+4*suffix,4))
        assert any(raw) and all(0<=v<=10 for v in raw)
        terrain.append({'suffix_id':suffix,'choices':raw,
                        'classes':sorted({v-1 for v in raw if v})})
    assert sorted({c for row in terrain for c in row['classes']}) == list(range(10))
    report['terrain']={'source':source(96,0x4cc1),'rows':terrain,'all_classes':list(range(10)),
                       'zero_means_retry':True}

    # 48 count-prefixed recipes are shared by placement and population code.
    recipe_table=at(96,0x6d0d,96)
    assert recipe_table == at(132,0x4ccb,96)
    recipes=[];ends=[];types=set()
    for i in range(48):
        pointer=int.from_bytes(recipe_table[2*i:2*i+2],'little')
        count=rb(132,pointer)
        assert 3<=count<=8
        raw=at(132,pointer+1,16*count)
        records=[raw[16*j:16*j+16] for j in range(count)]
        assert all(1<=r[0]<=6 for r in records)
        assert rb(132,pointer+1+16*count) == 0xff
        types.update(r[0] for r in records)
        recipes.append({'index':i,'source':source(132,pointer),'structures':count,
                        'types':[r[0] for r in records],
                        'records_hex':[r.hex(' ') for r in records],
                        'sha256':hashlib.sha256(at(132,pointer,2+16*count)).hexdigest()})
        ends.append(pointer+2+16*count)
    for i in range(47):
        assert ends[i] == int.from_bytes(recipe_table[2*i+2:2*i+4],'little')
    assert types==set(range(1,7)) and ends[-1]==0x5e0b
    handlers=[rw(132,0x405f+2*i) for i in range(7)]
    assert handlers == [0x406d,0x4072,0x4091,0x40c2,0x40f3,0x4156,0x406e]
    report['recipes']={'pointer_sources':[source(96,0x6d0d),source(132,0x4ccb)],
        'count':48,'records':sum(r['structures'] for r in recipes),
        'count_distribution':dict(sorted(Counter(r['structures'] for r in recipes).items())),
        'types':sorted(types),'type_handlers':[{'type':i,'source':source(132,p)} for i,p in enumerate(handlers)],
        'entries':recipes}

    # All 100 legal key difficulty bytes, every low-nibble size draw and recipe-mask outcome.
    dimensions=at(96,0x4bf4,100)
    assert dimensions == bytes([0x44]*10+[0x88]*90)
    controls=[tuple(at(96,0x4c58+2*i,2)) for i in range(10)]
    assert controls == [(0,15),(8,15),(8,15)]+[(16,31)]*7
    populations=list(at(96,0x53b3,16))
    assert populations == [10]*8+[15]*4+[20]*4
    levels=[]
    for level in range(100):
        band=level//10;base,mask=controls[band]
        choices=sorted({base+(roll&mask) for roll in range(256)})
        assert all(0<=i<48 for i in choices)
        sizes={dimensions[band*10+digit] for digit in range(10)}
        assert len(sizes)==1
        size=sizes.pop();w,h=size>>4,size&15
        tier=0 if level<11 else 15 if level>=80 else (level-10)//5+1
        assert 0<=tier<16 and populations[tier] in (10,15,20)
        levels.append({'level':level,'band':band,'surface_screens':[w,h],
            'recipes':choices,'tier':tier,'population_target':populations[tier]})
    report['levels']={'dimension_source':source(96,0x4bf4),
        'recipe_control_source':source(96,0x4c58),'tier_source':source(96,0x53c3),
        'population_source':source(96,0x53b3),'all_100_levels_checked':True,
        'boundaries':[levels[i] for i in range(100) if i==0 or
            any(levels[i][k]!=levels[i-1][k] for k in ('surface_screens','recipes','tier','population_target'))],
        'all_levels':levels,
        'placement_capacity':{'maximum_structures':8,'structure_record_bytes':4,
            'structure_records_wram':['$CD88','$CDA7'],'terminator_for_eight_at':'$CDAB',
            'interior_descriptors_wram':['$CDAC','$CE2B'],'interior_descriptor_bytes':16,
            'maximum_population_target':20,'population_record_bytes':8,
            'population_buffer_wram':['$CC48','$CCE7']}}

    # Full-period LCG proof/check and exact bounds for single-draw rejection loops.
    cycle=[];state=0
    while not cycle or state:
        cycle.append(state);state=(5*state+11)&0xffff
        assert len(cycle)<=65536
    assert len(cycle)==65536 and len(set(cycle))==65536
    def predicate_stats(label,predicate):
        accepted=[i for i,state in enumerate(cycle) if predicate(state)]
        assert accepted
        gaps=[(accepted[(i+1)%len(accepted)]-index-1)%65536 for i,index in enumerate(accepted)]
        return {'predicate':label,'accepted_states_per_full_cycle':len(accepted),
                'max_rejected_draws_before_accept':max(gaps),
                'max_draws_until_accept':max(gaps)+1}
    predicates=[predicate_stats('(high_byte & 0x7f) < 100',lambda s:((s>>8)&127)<100),
        predicate_stats('(high_byte & 0x0f) < 10',lambda s:((s>>8)&15)<10)]
    for size in (4,8):
        predicates.append(predicate_stats(f'(high_byte & 0x0f) < {size}',lambda s,k=size:((s>>8)&15)<k))
    for count in range(1,9):
        predicates.append(predicate_stats(f'(high_byte & 7) < {count}',lambda s,k=count:((s>>8)&7)<k))
    terrain_bounds=[]
    for row in terrain:
        raw=row['choices']
        terrain_bounds.append({'suffix':row['suffix_id'],**predicate_stats('terrain[low_byte&3] != 0',lambda s,t=raw:t[s&3]!=0)})
    report['rng_math']={'source':source(0,0x09f3),'formula':'next = (5 * state + 11) mod 65536',
        'period_from_zero':65536,'all_65536_integer_states_seen_once':True,
        'mathematical_reason':'Increment11 is odd and multiplier5 is1 mod4 (full-period conditions for a power-of-two modulus)',
        'single_predicate_bounds':predicates,'all_56_terrain_rejection_bounds':terrain_bounds,
        'not_proven':'End-to-end generator termination/distribution over all seeds; variable call counts and layout rejection are not one fixed single-draw predicate.'}

    # Bounded decompressor mirrors the original map copy format and validates every pointer read.
    extended_counter_bytes=set()
    @lru_cache(None)
    def decompress(n,a):
        length=rw(n,a);marker=rb(n,a+2);pc=a+3;out=bytearray();unknown=[];wraps=0;zeros=0
        assert length==360,(n,a,length)
        while len(out)<length:
            value=rb(n,pc);pc+=1
            if value!=marker:
                out.append(value);unknown.append(False);continue
            low,high=rb(n,pc),rb(n,pc+1);pc+=2
            offset=low|(high>>4)<<8;count=(high&15)+4
            if count==19:
                extra=rb(n,pc);pc+=1;extended_counter_bytes.add(extra)
                count=(count+extra)&255
                if count==0:count=256
            for index in range(offset,offset+count):
                if len(out)==length:break
                # Original0:$0D50..8E normalizes DE for EACH byte. Outside
                # the complete destination interval it emits zero. A true
                # forward reference inside that interval reads prior RAM.
                actual=index&0xfff
                if index>=4096:wraps+=1
                if actual>=length:
                    out.append(0);unknown.append(False);zeros+=1
                elif actual<len(out):
                    out.append(out[actual]);unknown.append(unknown[actual])
                else:
                    out.append(0);unknown.append(True)
        return bytes(out),pc-a,tuple(i for i,value in enumerate(unknown) if value),wraps,zeros
    groups=[];visual_assets=set();attributes=set();template_screen_refs=0
    for name,address,variants in [('single',0x610d,1),('vertical_pair',0x616d,2),
                                  ('horizontal_pair',0x61e5,2),('four',0x6245,4)]:
        pointers=[triple(96,address+3*i) for i in range(32)]
        entries=[]
        for n,p in sorted(set(pointers)):
            variant_rows=[]
            for variant in range(variants):
                visual=[];cgb=[]
                for cell in range(16):
                    mn,ma=triple(n,p+variant*96+3*cell)
                    data,consumed,unknown,wraps,zeros=decompress(mn,ma+8)
                    visual_assets.add((mn,ma));visual.append({'bank':mn,'address':ma,'header':at(mn,ma,8).hex(' '),
                        'map_sha256':hashlib.sha256(data).hexdigest() if not unknown else None,'compressed_bytes':consumed,
                        'unknown_destination_offsets':list(unknown),'wrapped_copy_bytes':wraps,'original_zero_fill_bytes':zeros})
                    an,aa=triple(n,p+variant*96+48+3*cell)
                    adata,aconsumed,aunknown,awraps,azeros=decompress(an,aa)
                    attributes.add((an,aa));cgb.append({'bank':an,'address':aa,
                        'attribute_sha256':hashlib.sha256(adata).hexdigest() if not aunknown else None,'compressed_bytes':aconsumed,
                        'unknown_destination_offsets':list(aunknown),'wrapped_copy_bytes':awraps,'original_zero_fill_bytes':azeros})
                    template_screen_refs+=1
                variant_rows.append({'variant':variant,'visual':visual,'cgb_attributes':cgb})
            entries.append({'table_bank':n,'table_address':p,'variants':variant_rows})
        groups.append({'kind':name,'source':source(96,address),'rolls':32,
                       'distinct_template_pointers':len(entries),'variants_per_template':variants,'templates':entries})
    report['surface_assets']={'sources':[source(96,0x5ee1),source(97,0x5443)],
        'template_roll_rows_checked':128,'distinct_templates':sum(g['distinct_template_pointers'] for g in groups),
        'screen_visual_and_attribute_pairs_checked':template_screen_refs,
        'distinct_visual_headers':len(visual_assets),'distinct_attribute_maps':len(attributes),
        'every_decoded_layer_has_360_bytes':True,'no_out_of_bounds_rom_pointer':True,
        'dictionary_wrap_model':'Original per-byte4KB normalization; outside-destination bytes arezero; true forward references inside destination aremarked unknown.',
        'groups':groups}

    # Reserved zero headers are not map classes. Inspect only all populated original interior IDs.
    interiors=[];reserved=[]
    for mid in range(103):
        hd=rw(97,0x60d8+2*mid)
        if not hd:
            reserved.append(mid);continue
        w,h=rb(97,hd+6),rb(97,hd+7)
        assert 0<w<=16 and 0<h<=16
        n,p=triple(97,hd+20);screens=[]
        for i in range(w*h):
            mn,ma=triple(n,p+3*i);data,consumed,unknown,wraps,zeros=decompress(mn,ma)
            screens.append({'bank':mn,'address':ma,'sha256':hashlib.sha256(data).hexdigest() if not unknown else None,
                'unknown_destination_offsets':list(unknown),'wrapped_copy_bytes':wraps,'original_zero_fill_bytes':zeros})
        interiors.append({'map_id':mid,'header':source(97,hd),'screens':[w,h],
                          'collision_threshold':rb(97,hd+8),'visual_maps':screens})
    assert len(interiors)==37 and sum(w['screens'][0]*w['screens'][1] for w in interiors)==83
    class_castles=list(at(132,0x41ae,10));class_other=list(at(132,0x41b8,10))
    valid={row['map_id'] for row in interiors}
    assert all(mid in valid for mid in class_castles)
    assert all(0x20+mid in valid and 0x40+mid in valid for mid in class_other)
    assert all(mid in valid for mid in [0x54,0x61,0x62,0x66])
    report['interior_assets']={'header_table':source(97,0x60d8),'populated_ids':37,
        'reserved_zero_headers':reserved,'screens_checked':83,'entries':interiors,
        'terrain_class_castle_map_ids':class_castles,
        'terrain_class_other_map_offsets':class_other,
        'all_10_terrain_map_variants_reference_populated_headers':True,
        'caveat':'Mode4/5 multi-floor layouts are built from these assets; this validates assets, not every composite layout.'}

    # Mode4/5 builds a shared floor-pair array, using layout IDs in bank114.
    # Check every recipe capacity and every possible stair-compatible next layout.
    floor_counts=[]
    for recipe in recipes:
        floors=[]
        for recordhex in recipe['records_hex']:
            raw=bytes.fromhex(recordhex)
            if raw[0] in (4,5):
                assert 3<=raw[1]<=9
                floors.append(raw[1])
        floor_counts.append({'recipe':recipe['index'],'requested_floor_counts':floors,
                             'stored_floor_pairs':sum(value-1 for value in floors)})
    maximum_pairs=max(row['stored_floor_pairs'] for row in floor_counts)
    assert maximum_pairs==32 and 0xce2c+2*maximum_pairs<=0xce7c
    layout_headers={};null_layouts=[];layouts=[];layout_visual=set();layout_cgb=set()
    for mid in range(192):
        pointer=rw(114,0x4001+2*mid)
        if not pointer:
            null_layouts.append(mid);continue
        stairs=list(at(114,pointer,3))
        assert len(set(stairs))==3 and all(0<=value<6 for value in stairs)
        layout_headers[mid]=stairs;cells=[]
        for cell in range(16):
            vn,va=triple(114,pointer+3+3*cell)
            vdata,vlen,vunknown,vwrap,vzero=decompress(vn,va)
            an,aa=triple(114,pointer+3+48+3*cell)
            adata,alen,aunknown,awrap,azero=decompress(an,aa)
            layout_visual.add((vn,va));layout_cgb.add((an,aa))
            cells.append({'visual':[vn,va],'visual_sha256':hashlib.sha256(vdata).hexdigest() if not vunknown else None,
                'visual_unknown_destination_offsets':list(vunknown),'attributes':[an,aa],
                'attribute_sha256':hashlib.sha256(adata).hexdigest() if not aunknown else None,
                'attribute_unknown_destination_offsets':list(aunknown)})
        layouts.append({'layout_id':mid,'source':source(114,pointer),'stairs':stairs,'cells':cells})
    first_type4=set(range(72))
    first_type5={160+8*group+offset for group in range(4) for offset in range(5)}
    intermediate=[];intermediate_ids=set()
    for incoming in range(6):
        bases=list(at(132,0x42c7+16*incoming,10))
        choices=sorted({base+offset for base in bases for offset in range(8)})
        assert all(mid in layout_headers and incoming in layout_headers[mid] for mid in choices)
        intermediate_ids.update(choices)
        intermediate.append({'incoming_stair_id':incoming,'original_base_choices':bases,'possible_layout_ids':choices,
                             'each_layout_contains_incoming_and_two_distinct_exits':True})
    assert first_type4|first_type5|intermediate_ids == set(layout_headers)
    assert len(layout_headers)==180 and len(null_layouts)==12
    assert all(mid not in first_type4|first_type5|intermediate_ids for mid in null_layouts)
    style4=list(at(132,0x41ca,40));style5=list(at(132,0x41c2,8))
    assert all(0<=value<12 for value in style4+style5)
    report['dungeon_layouts']={'generation_source':source(132,0x41f2),'loader_source':source(97,0x4533),
        'layout_pointer_table':source(114,0x4001),'stair_transition_table':source(132,0x42c7),
        'floor_array_start':'$CE2C','next_reserved_field':'$CE7C','capacity_pairs':40,
        'maximum_pairs_across_all48_recipes':maximum_pairs,'maximum_pair_end_exclusive':'$CE6C',
        'recipe_pair_counts':floor_counts,'first_type4_ids':sorted(first_type4),'first_type5_ids':sorted(first_type5),
        'intermediate_transitions':intermediate,'populated_layouts':180,'unused_null_layout_ids':null_layouts,
        'all_selected_layouts_non_null':True,'every_layout_has_three_distinct_stair_ids_0_to_5':True,
        'all_six_incoming_stair_classes_have_compatible_next_layouts':True,
        'all_selected_and_intermediate_layouts_checked':True,'screen_layer_pairs_checked':180*16,
        'distinct_visual_maps':len(layout_visual),'distinct_attribute_maps':len(layout_cgb),
        'terrain_styles':{'source_type4':source(132,0x41ca),'type4_choices':style4,
            'source_type5':source(132,0x41c2),'type5_choices':style5,'original_style_table':source(97,0x42dd)},
        'entries':layouts,'caveat':'Stair-ID compatibility and source/map bounds are checked; no claim of complete collision reachability, overlays or dynamic boss execution for all generated floor sequences.'}

    decoded=[{'bank':n,'address':a,'unknown_bytes':len(result[2]),'wrapped_copy_bytes':result[3],
              'original_zero_fill_bytes':result[4]} for (n,a),result in
             sorted((key,decompress(*key)) for key in
                {(n,a+8) for n,a in visual_assets}|attributes|
                {(row['bank'],row['address']) for interior in interiors for row in interior['visual_maps']}|
                layout_visual|layout_cgb)]
    report['map_compression']={'source':[source(0,0x0d50),source(0,0x0d60),source(0,0x0d74),source(0,0x0d8e)],
        'distinct_compressed_assets_checked':len(decoded),
        'assets_with_unknown_prior_destination_reads':sum(bool(row['unknown_bytes']) for row in decoded),
        'assets_using_dictionary_wrap':sum(bool(row['wrapped_copy_bytes']) for row in decoded),
        'wrapped_copy_bytes':sum(row['wrapped_copy_bytes'] for row in decoded),
        'assets_with_original_zero_fills':sum(bool(row['original_zero_fill_bytes']) for row in decoded),
        'extended_length_source':source(0,0x0d39),'extended_length_byte_values':sorted(extended_counter_bytes),
        'extended_counter_semantics':'8bit ADD19; zero executes256 copies, values beyond255 wrap before the loop',
        'assets':decoded,
        'model':'For each copied byte normalize source index to12bits; sources outside the complete360-byte output window emit zero. Source indices within that window but ahead of emitted data are explicitly unknown, never invented as valid tiles.'}

    # Original cache arithmetic and inventory bounds, checked for every valid slot/index.
    cache=[]
    for i in range(20):
        start=0xa000+405*i;end=start+404
        assert 0xa000<=start<=end<0xc000
        if cache:assert start==cache[-1]['last_cpu_address']+1
        cache.append({'slot':i,'marker':0x50+i,'first_cpu_address':start,'last_cpu_address':end,
                      'absolute_sram_offset':0x4000+start-0xa000})
    inventory=[{'key':i,'record_first':0xc707+4*i,'record_last':0xc70a+4*i,
                'seed_first':0xc787+2*i,'seed_last':0xc788+2*i} for i in range(32)]
    assert inventory[-1]['record_last']==0xc786 and inventory[-1]['seed_last']==0xc7c6
    report['persistence_bounds']={'cache_allocator':source(96,0x6c61),'cache_save':source(96,0x6c96),
        'cache_load':source(96,0x6cd1),'inventory_allocator':source(18,0x691f),
        'inventory_delete':source(18,0x69b0),'cache_slots':20,'record_bytes':405,'descriptor_bytes':404,
        'sram_bank':2,'cache_end_offset_exclusive':0x4000+20*405,
        'sram_bank_capacity':8192,'bytes_remaining_in_bank':8192-20*405,
        'markers_checked':cache,'inventory':inventory,'random_key_limit':20,'total_key_limit':32,
        'cache_full_behavior':'Allocator returnsFFC6=FF; generation4001 returns before assigning/writing a new slot.',
        'reentry_behavior':'Existing marker50+slot is required; descriptor is loaded, not regenerated from the seed.',
        'delete_behavior':'Original18:$69B0 invalidates cached marker and compacts all remaining4-byte records and2-byte seeds; adjusts selected index when needed.',
        'native_dynamic_boundary_cases_still_needed':['20 generated worlds','32 total keys','full-cache refusal','delete first/middle/last','re-enter after save/reload']}

    # Generator source creates every ROMX entry; branch reachability is not the code-coverage policy.
    sys.path.insert(0,str(repo/'recomp/tools'))
    import recompile_romx_bank as aot
    from inspect_map import decompress as common_decompress
    for item in decoded:
        data,_,unknown,_,_=decompress(item['bank'],item['address'])
        assert not unknown
        assert data==common_decompress(item['bank'],item['address']),item
    report['map_compression']['all_833_assets_match_repaired_repository_decoder']=True
    cmake=(repo/'recomp/CMakeLists.txt').read_text()
    generator=(repo/'recomp/tools/recompile_romx_bank.py').read_text()
    assert 'foreach(BANK RANGE 1 255)' in cmake and 'for off in range(begin, end)' in generator
    emitted=[]
    for n in (96,97,98,99,103,105,106,107,108,132,133,135):
        for address in (0x4000,0x4001,0x4fff,0x5000,0x6fff,0x7000,0x7fff):
            code=aot.emit_case(banks[n],address-0x4000)
            assert f'case 0x{address:04X}u:' in code
        emitted.append(n)
    if diagnostic is None:
        report['aot']={
            'accepted_binary_manifest_checked':False,
            'source_policy':'Every ROMX entry address is emitted; no reachability filter.',
            'entry_addresses_per_romx_bank':16384,
            'finite_dynamic_entry_samples_emitted_banks':emitted,
            'limitation':'Provide --diagnostic to verify the actual complete-AOT build and source manifest.'}
        return report
    from m8_build_identity import load_identity
    identity_path=diagnostic/'build-identity.json'
    identity=load_identity(identity_path)
    if (identity.source!='3d573873ae8122cbb10fcd5d0f7ae7a33a7609ba' or
            identity.sha256!='f93b7f96212559f65f05e09f8443a224bbda7d124047047fbf53510e16ae0321'):
        raise ValueError('Expected exact accepted M8 diagnostic identity')
    identity.verify(diagnostic/'DWM2tRecompFull.exe')
    identity_data=json.loads(identity_path.read_text())
    manifest_path=diagnostic/'source-manifest.json'
    manifest_digest=hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if (manifest_digest!='462752ad7e2fa0e658486cc5524106bb1f121a353d279418dd5cfa75d230ba99' or
            manifest_digest!=identity_data['source_manifest_sha256'] or
            identity_data['source_archive_sha256']!='c75ba57b296c1b2038cd5cc3789059eb4513f79831d64cfb6f4b855a22d72722'):
        raise ValueError('Accepted diagnostic source manifest/archive identity differs')
    build=json.loads((diagnostic/'build-report.json').read_text())
    if build['source_commit']!=identity.source or build['executable_sha256']!=identity.sha256:
        raise ValueError('Build report differs from the actual diagnostic identity')
    assert build['romx_banks']==list(range(1,256)) and build['rom_sha256']==ROM_SHA
    cachetext=(diagnostic/'build-logs/CMakeCache.txt').read_text()
    assert 'DWM2T_ALL_ROMX:BOOL=ON' in cachetext
    manifest=json.loads((diagnostic/'source-manifest.json').read_text())
    native_paths=sorted(path for path in manifest if
        path.startswith(('recomp/src/','recomp/include/','src/banks/')) or
        path in ('recomp/CMakeLists.txt','recomp/tools/recompile_bank0.py',
                 'recomp/tools/recompile_romx_bank.py','recomp/tools/generate_romx_dispatch.py',
                 'recomp/tools/generate_rom_image.py','recomp/tools/lr35902.py'))
    normalized_windows_checkout=[]
    for path in native_paths:
        data=(repo/path).read_bytes()
        if hashlib.sha256(data).hexdigest()==manifest[path]:continue
        crlf=data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
        assert hashlib.sha256(crlf).hexdigest()==manifest[path],path
        normalized_windows_checkout.append(path)
    report['aot']={'source_commit':build['source_commit'],'executable_sha256':build['executable_sha256'],
        'accepted_binary_manifest_checked':True,
        'actual_executable_hashed':True,'source_manifest_sha256':manifest_digest,
        'build_identity_sha256':identity.manifest_sha256,
        'build_report':str(diagnostic/'build-report.json'),'all_255_romx_banks_in_build':True,
        'entry_addresses_per_romx_bank':16384,'finite_dynamic_entry_samples_emitted_banks':emitted,
        'current_native_sources_match_accepted_build_manifest':True,
        'native_source_and_rom_files_compared':len(native_paths),
        'manifest_comparison_semantics':'Exact file hash or exact hash after LF->CRLF Windows-checkout conversion; no other content normalization.',
        'windows_checkout_newline_conversion_files':len(normalized_windows_checkout),
        'source_files':['recomp/CMakeLists.txt','recomp/tools/recompile_romx_bank.py','recomp/tools/generate_romx_dispatch.py','recomp/src/runtime.cpp','recomp/src/hram_exec.cpp'],
        'runtime_policy':'Compiled Bank0/ROMX entries and signature-checked original HRAM DMA only; other RAM execution traps.',
        'finding':'No postgame-specific missing ROMX bank or reachable-entry filter in the full build. Dynamic correctness of every postgame path remains a gameplay-validation question.'}
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--diagnostic',type=Path,help='Optional extracted complete-AOT build with original manifests')
    p.add_argument('--output',type=Path,required=True,help='New JSON file for the complete static receipt')
    args=p.parse_args()
    if args.output.exists():
        raise ValueError('Output already exists; refusing to overwrite an audit')
    report=audit(args.repo,args.diagnostic)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','scope','rom_sha256')},indent=2))
    print(json.dumps({'recipes':report['recipes']['count'],'structures':report['recipes']['records'],
        'levels':100,'terrain_classes':10,'templates':report['surface_assets']['distinct_templates'],
        'surface_layer_pairs':report['surface_assets']['screen_visual_and_attribute_pairs_checked'],
        'interior_screens':report['interior_assets']['screens_checked'],'lcg_states':report['rng_math']['period_from_zero']},indent=2))

if __name__=='__main__':main()
