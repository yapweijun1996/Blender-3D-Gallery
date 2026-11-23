"""Print the worst sampled contact for each failed clip."""
import json
import sys
from pathlib import Path

for file in sys.argv[1:]:
    print(file)
    gate = json.loads(Path(file).read_text())
    for clip, row in gate['clips'].items():
        if row['min_signed_m']>=.0005 and not row['peak_inside'] and not row['peak_pairs'] and not any(row['layer_peaks'].values()):
            continue
        signed = min(row['frames'],key=lambda x:x['min_signed_m'])
        pairs = max(row['frames'],key=lambda x:x['pairs'])
        by_layer = max(row['frames'],key=lambda x:sum(x['layer_pairs'].values()))
        print(clip, (row['peak_inside'], row['peak_pairs'], round(1000*row['min_signed_m'],3)),
              'vertex',signed['frame'],signed.get('worst_position_m'),
              'pairs',pairs['frame'],pairs.get('overlap_centers_m',[])[:2],
              'layers',by_layer['frame'],row['layer_peaks'])
