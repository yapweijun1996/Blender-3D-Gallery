import test from 'node:test';
for(const slug of ["hawker-stall-number-plate", "hawker-centre-ceiling-fan", "hawker-centre-table-number", "hawker-centre-tray-rack", "kopitiam-coffee-sock"]) test(slug+' geometry and budgets',async()=>{await import('../models/'+slug+'/validate.mjs');});
