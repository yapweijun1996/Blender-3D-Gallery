import test from 'node:test';
for(const slug of ["zebra-crossing-beacon", "road-speed-hump", "road-kerb-module", "five-foot-way-floor-tile", "street-utility-pole"]) test(slug+' geometry and budgets',async()=>{await import('../models/'+slug+'/validate.mjs');});
