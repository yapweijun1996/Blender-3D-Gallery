import test from 'node:test';
for(const slug of ["malaysia-card-lane-sign", "road-direction-gantry", "motorcycle-parking-bay", "hdb-car-park-ramp", "covered-motorcycle-parking"]) test(slug+' geometry and budgets',async()=>{await import('../models/'+slug+'/validate.mjs');});
