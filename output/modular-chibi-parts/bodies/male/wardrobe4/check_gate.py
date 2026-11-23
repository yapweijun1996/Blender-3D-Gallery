"""Recheck an existing candidate without changing asset bytes."""
import sys

from asset_io import HERE, MOTION, write_json
from body_audit import load_body_motion
from fit_module import read_module
from gate_module import BODY, companions, measure

item, attempt = sys.argv[sys.argv.index('--')+1:]
name = f'{item}-r{attempt}'
scene, arm, master, actions = load_body_motion(MOTION)
body = read_module(BODY,arm)
layers = {ref.name: read_module(ref,arm) for ref in companions(item)}
report, _ = measure(HERE/f'{name}.glb',scene,arm,master,body,actions,layers)
report['round'] = int(attempt)
report['rechecked_existing_export'] = True
write_json(HERE/'qa'/f'{name}.gate.json',report)
