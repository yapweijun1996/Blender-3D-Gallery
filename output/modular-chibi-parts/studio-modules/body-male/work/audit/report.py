"""Render human-readable summaries of the hash-bound reimport checks."""
from pathlib import Path
import json

DIR=Path(__file__).resolve().parent
r=json.loads((DIR/'export_checks.json').read_text());kv=json.loads((DIR/'khronos.json').read_text())
s=r['static'];skin=s['skin'];L,R=r['hands']['L'],r['hands']['R']
digits=('Index','Middle','Ring','Pinky','Thumb')
def f(v):
    return f'{v:.5f}'.rstrip('0').rstrip('.') if isinstance(v,float) else str(v)
def row(v):return '| '+' | '.join(map(f,v))+' |'
def table(out,header,rows):
    out.extend(['',row(header),row(['---']*len(header))])
    out.extend(row(rr) for rr in rows)
def vals(d):return ' / '.join(f(d[k]) for k in digits)
out=['# Export measurements','',f"Blender {r['blender']}. All pose measurements use both delivered GLBs reimported into an empty scene. Distances below are in millimetres unless indicated.",'',
     'Detailed world-space witnesses, rest-defined patch sizes, individual triangle IDs and per-clip normalization evidence are in [export_checks.json](export_checks.json). Khronos messages and versions are in [khronos.json](khronos.json).']
table(out,['File','SHA-256','Khronos errors / warnings / infos'],[[name,kk['sha256'],' / '.join(str(kk['issues'][k]) for k in ('numErrors','numWarnings','numInfos'))] for name,kk in kv.items()])
out+=['','## Bind mesh']
table(out,['Measurement','Value'],[
 ['Meshes / skins / joints / animations',f"{s['meshes']} / {s['skins']} / {s['joints_per_skin'][0]} / {s['animations']}"],
 ['Triangles, whole / left wrist-distal / right wrist-distal',f"{s['triangles']} / {L['hand_triangles_any_vertex']} / {R['hand_triangles_any_vertex']}"],
 ['Editable source vertices / reimported vertex copies',f"{r['native_roundtrip']['native_vertices']} / {r['native_roundtrip']['reimport_vertices']}"],
 ['Height / lowest z, metres',f"{s['height_m']} / {s['feet_z_m']}"],
 ['Packed textures',', '.join(f"{n} {sz[0]} × {sz[1]}" for n,sz in s['decoded_images'].items())],
 ['Materials',s['materials']],['Skin vertices / unweighted / over four',f"{skin['vertices']} / {skin['unweighted']} / {skin['over_four']}"],
 ['Max influences / maximum weight-sum error',f"{skin['max_influences']} / {skin['max_sum_error']:.9g}"],
 ['Multi-digit vertices, any / two above 0.2',f"{skin['multiple_finger_chains']} / {skin['multiple_finger_chains_above_0_2']}"],
 ['Original non-hand vertex copies / maximum displacement',f"{s['original_rest_displacement']['source_vertex_copies_compared']} / {s['original_rest_displacement']['maximum_source_to_export_mm']}"],
 ['Bind non-adjacent triangle pairs, source / repaired',f"{r['source_rest_intersections']['whole_body']} / {r['bind_intersections']['whole_body']}"],
 ['Retessellated toe faces / frontal crease offset', '28 toe triangles / 0.015 mm at one source coordinate'],
 ['Repaired hand open edges beyond wrist, left / right',f"{L['open_edges_distal_to_wrist']} / {R['open_edges_distal_to_wrist']}"],
 ['Repaired hand edges incident to >2 triangles, left / right',f"{L['nonmanifold_edges_over_two_faces']} / {R['nonmanifold_edges_over_two_faces']}"],
 ['Reimport nearest reflected vertex mean / RMS / maximum',' / '.join(f(s['mirror_nearest_vertex_mm'][k]) for k in ['mean','rms','max'])],
 ['Reflected vertex-to-skin mean / RMS / 95th / maximum, source',' / '.join(f(s['mirror_reflected_vertex_to_surface_mm']['original'][k]) for k in ['mean','rms','p95','max'])],
 ['Reflected vertex-to-skin mean / RMS / 95th / maximum, export',' / '.join(f(s['mirror_reflected_vertex_to_surface_mm']['export'][k]) for k in ['mean','rms','p95','max'])],
 ['Clip count / rotation channels / scale channels',f"{r['library']['animations']} / {sum(c['paths'].get('rotation',0) for c in r['library']['clips'].values())} / {sum(c['paths'].get('scale',0) for c in r['library']['clips'].values())}"],
 ['Armature common joint names / largest world bind-matrix component difference',f"{r['library']['joint_frame_comparison']['shared_joint_names']} / {r['library']['joint_frame_comparison']['maximum_world_bind_matrix_difference']:.9g}"]])
out+=['','The wrist boundary is |X| = 0.28245 m. Hand triangle counts include every triangle with a vertex beyond the wrist. The non-hand comparison looks up every original vertex copy against the reimported bind surface vertices.','',
      '## Re-derived local axes','',
      'Curl turns the distal axis toward the palmar pad. Spread turns index/middle toward the thumb and ring/pinky toward the little-finger side. The thumb spread column measures movement toward palmar abduction. Signs are the dominant actual bone-local axes. The JSON retains full unit vectors at all four joints.']
table(out,['Digit','Curl L','Curl R','Spread L','Spread R','Left / right distal shaft vertices checked'],[
    [d,L['axes'][d][0]['curl_toward_pulp'][0],R['axes'][d][0]['curl_toward_pulp'][0],L['axes'][d][0]['spread'][0],R['axes'][d][0]['spread'][0],
     f"{L['free_shaft_weights'][d]['vertices']} / {R['free_shaft_weights'][d]['vertices']}"] for d in digits])
out+=['','## Rest hands']
table(out,['Measure','Left','Right'],[
 ['Palmar normal',str(L['palm_normal']),str(R['palm_normal'])],['Degrees from world down',L['palm_degrees_from_down'],R['palm_degrees_from_down']],
 ['Thumb root-to-skin-tip direction',str(L['digits']['Thumb']['root_to_skin_tip_unit']),str(R['digits']['Thumb']['root_to_skin_tip_unit'])],
 ['Thumb head spacings, metacarpal / two visible segments',str(L['digits']['Thumb']['bone_head_spacings_mm']),str(R['digits']['Thumb']['bone_head_spacings_mm'])],
 *[[f'Thumb width × thickness at {t} shaft fraction',f"{L['thumb_section_widths'][t]['width_mm']} × {L['thumb_section_widths'][t]['thickness_mm']}",f"{R['thumb_section_widths'][t]['width_mm']} × {R['thumb_section_widths'][t]['thickness_mm']}"] for t in L['thumb_section_widths']],
 *[[k+' free-shaft gap',L['interdigital_free_shaft_gaps_mm'][k],R['interdigital_free_shaft_gaps_mm'][k]] for k in L['interdigital_free_shaft_gaps_mm']]])
out+=['','## Posed surface and collision measurements','',
      'Each clip uses one quaternion sample at 0 seconds on the 20 bones of its authored hand. All 18 clips are named below.','',
      'Fingertip centroids use the distal 1.8 mm support band. The palmar surface is the underside of the hand between wrist and MCPs. The pulp patch faces forward and volar on the fingertip, lies within 16 mm of its end and within 2.65 mm of the distal support plane. Witness distance considers vertex-to-face and interior edge-to-edge minima in both directions. A face crossing counts as zero separation and is flagged independently.']
table(out,['Clip','Rotation / scale channels','Non-adjacent pairs, full / L / R','Tip-to-palm, I / M / R / P / T','Thumb above other tips','Pulp gap, OK/pinch','Replay max'],
    [[n,' / '.join(str(r['library']['clips'][n]['paths'].get(k,0)) for k in ('rotation','scale')),
      ' / '.join(str(p['intersections'][k]) for k in ('whole_body','left_hand_or_wrist','right_hand_or_wrist')),
      vals(p['tip_centroid_to_palm_skin_mm']),p['thumb_above_highest_other_mm'],p['surfaces'].get('pulp_to_pulp',{}).get('distance_mm','—'),p.get('reimport_max_vertex_mm','—')]
       for n,p in r['poses'].items()])
table(out,['Fist metric','Left','Right'],[[f'{d} pulp to palmar skin',*[r['poses']['hand_fist_'+t]['surfaces']['long_finger_pulp_to_palm'][d]['distance_mm'] for t in ('L','R')]] for d in digits[:4]]+
   [['Thumb terminal skin to folded digits',*[r['poses']['hand_fist_'+t]['surfaces']['thumb_terminal_to_folded']['distance_mm'] for t in ('L','R')]]])
table(out,['Exterior contact or internal opening','Left','Right'],[
 ['Thumb terminal to exposed palmar-side folded surface',*[r['poses']['hand_fist_'+t]['surfaces']['thumb_terminal_to_palmar_exterior']['distance_mm'] for t in ('L','R')]],
 ['Thumb pulp to exposed palmar-side folded surface',*[r['poses']['hand_fist_'+t]['surfaces']['thumb_pulp_to_palmar_exterior']['distance_mm'] for t in ('L','R')]],
 *[[g+' side silhouette enclosed holes, mm²',*[str(r['poses']['hand_'+g+'_'+t]['thumb_side_silhouette']['hole_areas_mm2']) for t in ('L','R')]] for g in ('fist','thumbs_up')],
 *[[g+' opposing pulp area within 0.5 mm, thumb / index, mm²',
    *[' / '.join(f(r['poses']['hand_'+g+'_'+t]['surfaces']['opposing_pulp_near_area'][k]['within_0_5_mm_area_mm2']) for k in ('thumb_pulp','index_pulp')) for t in ('L','R')]] for g in ('ok','pinch')],
 *[[g+' opposing pulp area within 1 mm, thumb / index, mm²',
    *[' / '.join(f(r['poses']['hand_'+g+'_'+t]['surfaces']['opposing_pulp_near_area'][k]['within_1_mm_area_mm2']) for k in ('thumb_pulp','index_pulp')) for t in ('L','R')]] for g in ('ok','pinch')]])
out+=['','Exterior tests retain folded triangles whose outward normals point toward the underside and whose centres are visible from below on the folded stack with the thumb removed. Opening areas use a direct skin silhouette at 0.25 mm per pixel in the oblique thumb-side view, with 8-connected background and at least four pixels per component. Pulp contact area is estimated by 144 equal-area triangle samples per face and requires opposing normals.']
table(out,['40 mm grip cylinder','Left','Right'],[[key,*[r['poses']['hand_grip_small_'+t]['cylinder_fit'][k] for t in ('L','R')]] for k,key in
   [('point_world_mm','World point, mm'),('axis_world','World axis'),('minimum_axis_distance_mm','Axis-to-skin minimum'),
    ('penetrating_triangles','Penetrating triangles'),('max_angular_contact_gap_deg','Largest angle between the nearest per-part support directions, degrees'),('max_angular_gap_all_skin_vertices_deg','Largest angular gap over all skin projections, degrees')]])
out+=['','Full-body crossings use a BVH on the deformed triangles, retaining a pair if the two triangles share no welded rest-position vertex. The additional coplanar test requires positive overlapping interior area. The mandrel also lies inside the convex hull of the complete projected hand when its largest angular gap is below 180°. Coordinate weld precision is 1 micrometre. The cylinder check projects every hand triangle onto the plane perpendicular to the declared axis, including triangle interiors.','',
 'The two toe patches retain all original corner coordinates. Diagonal changes alter toe triangle interiors by up to 2.954 mm left and 2.192 mm right in bidirectional 24-subdivision sampling. Measurements and sample counts are in [source_patch_distances.json](source_patch_distances.json).', '', '## Check results','']
out += [f"- {'PASS' if passed else 'FAIL'} · {c}" for c,passed in r['checks'].items()]
(DIR/'MEASUREMENTS.md').write_text('\n'.join(out)+'\n')
