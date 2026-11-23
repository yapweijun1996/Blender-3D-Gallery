"""Check the trial bank independently before selecting it for delivery."""
from verify import *
import verify

verify.FIXED = OUT/'.runtime/motion_thumb_trial.glb'
verify.QA = OUT/'.runtime/walkqa'
verify.QA.mkdir(exist_ok=True,parents=True)
verify.motion_audit()
