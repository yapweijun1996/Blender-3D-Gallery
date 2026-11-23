"""Independently replay the amended walk on all seven delivered modules."""
from verify import *
import verify

verify.FIXED = OUT/'.runtime/motion_thumb_trial.glb'
verify.QA = OUT/'.runtime/walkqa'
verify.module_audit(list(MODULES),('walk',))
