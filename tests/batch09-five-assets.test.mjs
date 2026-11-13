import test from 'node:test';
for(const slug of ["roadside-bus-bay", "malaysia-terrace-house-gate", "malaysia-terrace-house-porch", "malaysia-car-porch-roof", "malaysia-house-boundary-wall"])test(slug+' structure and budgets',async()=>{await import('../models/'+slug+'/validate.mjs');});
